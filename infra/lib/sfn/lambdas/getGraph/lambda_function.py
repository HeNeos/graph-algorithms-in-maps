import os
import json
import boto3
import requests

from dataclasses import dataclass
from uuid import uuid4
import osmnx as ox
from networkx import MultiDiGraph
from typing import Tuple, Optional, Dict, List

from modules.graph import NodeId, EdgeId, Node, Edge, Graph

@dataclass
class Coordinates:
  latitude: float
  longitude: float

GRAPHS_TABLE_NAME = os.environ["GRAPHS_TABLE_NAME"]
GRAPHS_BUCKET_NAME = os.environ["GRAPHS_BUCKET"]

dynamodb = boto3.resource("dynamodb")
graphs_table = dynamodb.Table(GRAPHS_TABLE_NAME)
s3 = boto3.resource("s3")
graphs_bucket = s3.Bucket(GRAPHS_BUCKET_NAME)

def get_current_location(coordinates: Coordinates) -> Tuple[Optional[str], Optional[str]]:
  latitude, longitude = (round(coordinates.latitude, 6), round(coordinates.longitude, 6))
  url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
  response = requests.get(url)
  data = response.json()
  if "address" not in data:
    return (None, None)
  address = data["address"]
  city: Optional[str] = address.get("city", None)
  country: Optional[str] = address.get("country", None)
  return (city, country)

def get_max_speed(edge, min_max_speed_allowed=30):
  max_speed = min_max_speed_allowed
  if "maxspeed" in edge:
    max_speeds = edge["maxspeed"]
    if isinstance(max_speeds, list):
      speeds: List[int] = [int(speed) for speed in max_speeds if speed and speed.isnumeric()]
      if len(speeds) > 0:
        max_speed = min(speeds)
    elif isinstance(max_speeds, str) and max_speeds.isnumeric():
      max_speed = int(max_speeds)
    elif isinstance(max_speeds, int):
      max_speed = max_speeds
  return max_speed

def generate_graph(graph: MultiDiGraph) -> Graph:
  all_edges: Dict[EdgeId, Edge] = dict()
  to_node_by_node: Dict[NodeId, List[NodeId]] = dict()
  for edge in graph.edges:
    u, v, _ = edge
    current_edge = graph.edges[edge]
    all_edges[(u, v)] = Edge(id=(u, v), length=current_edge["length"], maxspeed=get_max_speed(current_edge))
    if u not in to_node_by_node:
      to_node_by_node[u] = []
    to_node_by_node[u].append(v)
  all_nodes: Dict[NodeId, Node] = {node: Node(id=node, next_nodes=to_node_by_node.get(node, [])) for node in graph.nodes}
  return Graph(nodes=all_nodes, edges=all_edges)

def store_graph(graph: Graph, key: str):
  nodes = {"Nodes": [str(node) for node in set(graph.nodes.keys())]}
  edges = {
    "Edges": {
      ','.join(str(x) for x in edge_id): ','.join([str(edge.length), str(edge.maxspeed)])
      for edge_id, edge in graph.edges.items()
    }
  }
  graphs_bucket.put_object(Key=f"nodes-{key}.json", Body=json.dumps(nodes))
  graphs_bucket.put_object(Key=f"edges-{key}.json", Body=json.dumps(edges))

def download_graph(country: str, city: str) -> Tuple[MultiDiGraph, str]:
  ox.config(use_cache=True, cache_folder="/tmp/osmnx_cache")
  # ox.settings.cache_folder
  G: MultiDiGraph = ox.graph_from_place(f"{city}, {country}", network_type="drive")
  key: str = uuid4().hex
  #TODO: Send it directly to S3
  ox.save_graphml(G, f"/tmp/{key}.graphml")
  graphs_bucket.upload_file(f"/tmp/{key}.graphml", f"{key}.graphml")
  return G, key

def get_multidigraph(graph_id: str) -> MultiDiGraph:
  graphs_bucket.download_file(Key=f"{graph_id}.graphml", Filename=f"/tmp/{graph_id}.graphml")
  return ox.load_graphml(f"/tmp/{graph_id}.graphml")

def get_graph_id(country: str, city: str) -> Optional[str]:
  response = graphs_table.get_item(
    Key={
      "Country": country,
      "City": city
    }
  )

  item: Dict[str, Dict[str, str]] = response.get("Item", {})
  graph_id: Optional[str] = item.get("GraphId", None) # type: ignore
  return graph_id

def get_graph(country: str, city: str) -> Tuple[MultiDiGraph, str]:
  graph_id = get_graph_id(country, city)
  if graph_id is None:
    G, graph_id = download_graph(country, city)
    graph: Graph = generate_graph(G)
    store_graph(graph, graph_id)
    graphs_table.put_item(Item={
      "Country": country,
      "City": city,
      "GraphId": graph_id
    })
  else:
    G: MultiDiGraph = get_multidigraph(graph_id)

  return G, graph_id

def get_node_id(graph: MultiDiGraph, location: Coordinates) -> NodeId:
  return ox.nearest_nodes(graph, location.longitude, location.latitude) # type: ignore

def lambda_handler(event, _):
  source_coordinates = event["source"]
  destination_coordinates = event["destination"]
  source_coordinates = Coordinates(latitude=source_coordinates["latitude"], longitude=source_coordinates["longitude"])
  destination_coordinates = Coordinates(latitude=destination_coordinates["latitude"], longitude=destination_coordinates["longitude"])

  source_location = get_current_location(source_coordinates)
  destination_location = get_current_location(destination_coordinates)

  source_city, source_country = source_location
  destination_city, destination_country = destination_location

  if not all([source_city, source_country, destination_city, destination_country]):
    print("No possible to find a valid location")
    return

  if source_city != destination_city or source_country != destination_country:
    print("Source and destination are not in the same city/country")
    return

  G, graph_id = get_graph(source_country, source_city) # type: ignore
  source = get_node_id(G, source_coordinates)
  destination = get_node_id(G, destination_coordinates)

  return {
    "source": source,
    "destination": destination,
    "key": graph_id
  }


