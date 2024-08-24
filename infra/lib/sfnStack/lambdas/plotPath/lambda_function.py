import json

from dataclasses import dataclass
from networkx import MultiDiGraph
from typing import Dict, Union, cast

from modules.graph import NodeId
from lambdas.plotPath.utils import (
    get_graph_data,
    get_multidigraph,
    get_path,
    reconstruct_path,
)


@dataclass
class Event:
    iterations: int
    weight: float
    solution_key: str
    source: NodeId
    destination: NodeId
    graph_id: str


def lambda_handler(event: Event, _: Dict[str, str]) -> Dict[str, Union[int, str]]:
    event_graph = Event(
        iterations=event["iterations"],  # type: ignore
        weight=event["weight"],  # type: ignore
        solution_key=event["solution_key"],  # type: ignore
        source=event["source"],  # type: ignore
        destination=event["destination"],  # type: ignore
        graph_id=event["graph_id"],  # type: ignore
    )
    G: MultiDiGraph = get_multidigraph(event_graph.graph_id)
    path, visited, active = get_path(event_graph.solution_key)
    nodes, edges = get_graph_data(event_graph.graph_id)

    s3_url = reconstruct_path(
        G,
        nodes,
        edges,
        event_graph.source,
        event_graph.destination,
        path,
        visited,
        active,
        event_graph.solution_key,
    )

    return {
        "statusCode": 200,
        "body": json.dumps(cast(Dict[str, str], {"url": s3_url})),
    }
