import os

import osmnx as ox
import boto3
import json
import matplotlib.pyplot as plt
import requests

from dataclasses import dataclass
from networkx import MultiDiGraph
from typing import Optional, Dict, List

from modules.graph import NodeId, EdgeId, Node, Edge, Graph
from modules.plot import POINT_ALPHA, POINT_SIZE, NODE_ALPHA, NODE_SIZE, PathEdge, UnvisitedEdge

GRAPHS_TABLE_NAME = os.environ["GRAPHS_TABLE_NAME"]
GRAPHS_BUCKET_NAME = os.environ["GRAPHS_BUCKET"]
PATHS_BUCKET_NAME = os.environ["PATHS_BUCKET"]

dynamodb = boto3.resource("dynamodb")
graphs_table = dynamodb.Table(GRAPHS_TABLE_NAME)
s3 = boto3.resource("s3")
s3_client = boto3.client("s3")
graphs_bucket = s3.Bucket(GRAPHS_BUCKET_NAME)
paths_bucket = s3.Bucket(PATHS_BUCKET_NAME)

@dataclass
class Event:
  iterations: int
  weight: float
  solution_key: str
  source: NodeId
  destination: NodeId
  graph_id: str

def get_multidigraph(graph_id: str) -> MultiDiGraph:
  graphs_bucket.download_file(Key=f"{graph_id}.graphml", Filename=f"/tmp/{graph_id}.graphml")
  return ox.load_graphml(f"/tmp/{graph_id}.graphml")

def get_path(solution_key: str):
  path_object = s3_client.get_object(
    Bucket=PATHS_BUCKET_NAME,
    Key=f"{solution_key}.json"
  )
  path = json.load(path_object["Body"])
  return {int(k): v for k, v in path.items()}

def get_graph_data(graph_id: str):
  [nodes, edges] = [
    s3_client.get_object(
      Bucket=GRAPHS_BUCKET_NAME,
      Key=f"{data}-{graph_id}.json"
    )
    for data in ["nodes", "edges"]
  ]

  nodes = json.load(nodes["Body"])
  edges = json.load(edges["Body"])

  graph_nodes: List[NodeId] = [int(node) for node in nodes["Nodes"]]
  graph_edges: Dict[EdgeId, Edge] = dict()
  for edge_id, edge in edges["Edges"].items():
    u, v = edge_id.split(",")
    graph_edge_id: EdgeId = (int(u), int(v))
    length, maxspeed = edge.split(",")
    graph_edge = Edge(id=graph_edge_id, length=float(length), maxspeed=int(maxspeed))
    graph_edges[graph_edge_id] = graph_edge

  return graph_nodes, graph_edges

def save_graph(graph: MultiDiGraph, edges_in_path: List[EdgeId], solution_key: str, dist, time) -> Optional[str]:
  destination = edges_in_path[0][-1]
  source = edges_in_path[-1][0]
  node_size = []
  node_alpha = []
  node_color = []
  for node in graph.nodes:
    if node in (source, destination):
      node_size.append(POINT_SIZE)
      node_alpha.append(POINT_ALPHA)
      if node == source:
        node_color.append("blue")
      else:
        node_color.append("red")
    else:
      node_size.append(NODE_SIZE)
      node_alpha.append(NODE_ALPHA)
      node_color.append("white")
  edge_color = []
  edge_alpha = []
  edge_linewidth = []
  for edge in graph.edges:
    if (edge[0], edge[1]) in edges_in_path:
      edge_color.append(PathEdge.color)
      edge_alpha.append(PathEdge.alpha)
      edge_linewidth.append(PathEdge.linewidth)
    else:
      edge_color.append(UnvisitedEdge.color)
      edge_alpha.append(UnvisitedEdge.alpha)
      edge_linewidth.append(UnvisitedEdge.linewidth)

  fig, ax = ox.plot_graph(
    graph,
    node_size=node_size,
    node_alpha=node_alpha,
    edge_color=edge_color,
    edge_alpha=edge_alpha,
    edge_linewidth=edge_linewidth,
    node_color=node_color,
    bgcolor="#000000",
    show=False,
    close=False
  )
  title = '\n'.join([f"Distance: {dist} km", f"Time: {time}"])
  ax.set_title(title, color="white", fontsize=10)
  plt.savefig(f"/tmp/{solution_key}.png", dpi=600)
  plt.close()
  paths_bucket.upload_file(f"/tmp/{solution_key}.png", f"{solution_key}.png")

  response = s3_client.generate_presigned_url("get_object", Params={
    "Bucket": PATHS_BUCKET_NAME,
    "Key": f"{solution_key}.png"
  }, ExpiresIn=300)
  return str(response)

def reconstruct_path(G: MultiDiGraph, nodes: List[NodeId], edges: Dict[EdgeId, Edge], source: NodeId, destination: NodeId, path: Dict[NodeId, Optional[NodeId]], solution_key: str) -> str:
  dist: float = 0
  time: float = 0
  edges_in_path: List[EdgeId] = []
  current_node_id: NodeId = destination
  while current_node_id != source:
    previous_node_id: Optional[NodeId] = path.get(current_node_id, None)
    if previous_node_id is None:
      break
    current_edge_id: EdgeId = (previous_node_id, current_node_id)
    edges_in_path.append(current_edge_id)
    current_edge: Edge = edges[current_edge_id]
    current_length = current_edge.length
    current_maxspeed = current_edge.maxspeed
    dist += current_length / 1000
    time += (current_length / 1000) / current_maxspeed
    current_node_id = previous_node_id
  time_in_sec = int(time * 60 * 60)
  formatted_time = f"{time_in_sec // 60} min {time_in_sec%60} sec"
  print(f"Total dist = {dist} km")
  print(f"Total time = {formatted_time}")
  print(f"Speed average = {dist / time}")
  s3_url = save_graph(G, edges_in_path, solution_key, dist, formatted_time)
  return s3_url

def lambda_handler(event: Event, _):
  event_graph = Event(
    iterations=event["iterations"],
    weight=event["weight"],
    solution_key=event["solution_key"],
    source=event["source"],
    destination=event["destination"],
    graph_id=event["graph_id"]
  )
  G: MultiDiGraph = get_multidigraph(event_graph.graph_id)
  path = get_path(event_graph.solution_key)
  nodes, edges = get_graph_data(event_graph.graph_id)

  s3_url = reconstruct_path(G, nodes, edges, event_graph.source, event_graph.destination, path, event_graph.solution_key)

  return {
    "statusCode": 200,
    "body": json.dumps({"url": s3_url})
  }