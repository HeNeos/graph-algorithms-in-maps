import os

from mypy_boto3_dynamodb import DynamoDBServiceResource
from mypy_boto3_s3 import S3ServiceResource
import osmnx as ox
import boto3
import json
import io
import matplotlib.pyplot as plt

from networkx import MultiDiGraph
from typing import Optional, Dict, List, Set, Tuple, cast

from modules.graph import NodeId, EdgeId, Edge
from modules.plot import (
    POINT_ALPHA,
    POINT_SIZE,
    NODE_ALPHA,
    NODE_SIZE,
    PathEdge,
    UnvisitedEdge,
    ActiveEdge,
    VisitedEdge,
)

GRAPHS_TABLE_NAME = os.environ["GRAPHS_TABLE_NAME"]
GRAPHS_BUCKET_NAME = os.environ["GRAPHS_BUCKET"]
PATHS_BUCKET_NAME = os.environ["PATHS_BUCKET"]

dynamodb: DynamoDBServiceResource = boto3.resource("dynamodb")
graphs_table = dynamodb.Table(GRAPHS_TABLE_NAME)
s3: S3ServiceResource = boto3.resource("s3")
s3_client = boto3.client("s3")
graphs_bucket = s3.Bucket(GRAPHS_BUCKET_NAME)
paths_bucket = s3.Bucket(PATHS_BUCKET_NAME)


Color = Tuple[float, float, float, float] | str


def get_multidigraph(graph_id: str) -> MultiDiGraph:
    graphs_bucket.download_file(
        Key=f"{graph_id}.graphml", Filename=f"/tmp/{graph_id}.graphml"
    )

    return ox.load_graphml(f"/tmp/{graph_id}.graphml")


def get_path(
    solution_key: str,
) -> Tuple[Dict[NodeId, Optional[NodeId]], Set[EdgeId], Set[EdgeId]]:
    objects = {
        name: s3_client.get_object(
            Bucket=PATHS_BUCKET_NAME, Key=f"{name}-{solution_key}.json"
        )
        for name in ["path", "visited", "active"]
    }
    raw_path: Dict[str, NodeId] = json.load(objects["path"]["Body"])
    raw_visited: List[List[NodeId]] = json.load(objects["visited"]["Body"])
    raw_active: List[List[NodeId]] = json.load(objects["active"]["Body"])

    path: Dict[NodeId, Optional[NodeId]] = {int(k): v for k, v in raw_path.items()}
    visited: Set[EdgeId] = {(k[0], k[1]) for k in raw_visited}
    active: Set[EdgeId] = {(k[0], k[1]) for k in raw_active}
    return path, visited, active


def get_graph_data(graph_id: str) -> Tuple[List[NodeId], Dict[EdgeId, Edge]]:
    [raw_nodes, raw_edges] = [
        s3_client.get_object(Bucket=GRAPHS_BUCKET_NAME, Key=f"{data}-{graph_id}.json")
        for data in ["nodes", "edges"]
    ]

    nodes: Dict[str, str] = json.load(raw_nodes["Body"])
    edges: Dict[str, Dict[str, str]] = json.load(raw_edges["Body"])

    graph_nodes: List[NodeId] = [int(node) for node in nodes["Nodes"]]
    graph_edges: Dict[EdgeId, Edge] = dict()
    for edge_id, edge in edges["Edges"].items():
        u, v = edge_id.split(",")
        graph_edge_id: EdgeId = (int(u), int(v))
        length, maxspeed = edge.split(",")
        graph_edge = Edge(
            id=graph_edge_id, length=float(length), maxspeed=int(maxspeed)
        )
        graph_edges[graph_edge_id] = graph_edge

    return graph_nodes, graph_edges


def save_graph(
    graph: MultiDiGraph,
    edges_in_path: Set[EdgeId],
    visited: Set[EdgeId],
    active: Set[EdgeId],
    source: NodeId,
    destination: NodeId,
    solution_key: str,
    dist: float,
    time: str,
) -> str:
    node_size: List[float] = []
    node_alpha: List[float] = []
    node_color: List[Color] = []
    for node in cast(List[NodeId], graph.nodes):
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
    edge_alpha: List[float] = []
    edge_color: List[str | Tuple[float, float, float, float]] = []
    edge_linewidth: List[float] = []
    for edge in graph.edges:
        edge_id = (edge[0], edge[1])
        if edge_id in edges_in_path:
            edge_color.append(PathEdge.color)
            edge_alpha.append(PathEdge.alpha)
            edge_linewidth.append(PathEdge.linewidth)
        elif edge_id in visited:
            edge_color.append(VisitedEdge.color)
            edge_alpha.append(VisitedEdge.alpha)
            edge_linewidth.append(VisitedEdge.linewidth)
        elif edge_id in active:
            edge_color.append(ActiveEdge.color)
            edge_alpha.append(ActiveEdge.alpha)
            edge_linewidth.append(ActiveEdge.linewidth)
        else:
            edge_color.append(UnvisitedEdge.color)
            edge_alpha.append(UnvisitedEdge.alpha)
            edge_linewidth.append(UnvisitedEdge.linewidth)

    fig, ax = ox.plot_graph(
        graph,
        node_size=node_size,  # type: ignore
        node_alpha=node_alpha,  # type: ignore
        edge_color=edge_color,  # type: ignore
        edge_alpha=edge_alpha,
        edge_linewidth=edge_linewidth,  # type: ignore
        node_color=node_color,  # type: ignore
        bgcolor="#000000",
        show=False,
        close=False,
    )
    title: str = "\n".join([f"Distance: {dist} km", f"Time: {time}"])
    ax.set_title(title, color="#3b528b", fontsize=10)

    buffer = io.BytesIO()

    plt.savefig(buffer, dpi=300, format="png")
    plt.close()

    buffer.seek(0)
    paths_bucket.put_object(
        Body=buffer, Key=f"{solution_key}.png", ContentType="image/png"
    )
    buffer.close()

    response = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": PATHS_BUCKET_NAME, "Key": f"{solution_key}.png"},
        ExpiresIn=300,
    )
    return str(response)


def reconstruct_path(
    G: MultiDiGraph,
    nodes: List[NodeId],
    edges: Dict[EdgeId, Edge],
    source: NodeId,
    destination: NodeId,
    path: Dict[NodeId, Optional[NodeId]],
    visited: Set[EdgeId],
    active: Set[EdgeId],
    solution_key: str,
) -> str:
    dist: float = 0
    time: float = 0
    edges_in_path: Set[EdgeId] = set()
    current_node_id: NodeId = destination
    while current_node_id != source:
        previous_node_id: Optional[NodeId] = path.get(current_node_id, None)
        if previous_node_id is None:
            break
        current_edge_id: EdgeId = (previous_node_id, current_node_id)
        edges_in_path.add(current_edge_id)
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
    s3_url = save_graph(
        G,
        edges_in_path,
        visited,
        active,
        source,
        destination,
        solution_key,
        dist,
        formatted_time,
    )
    return s3_url
