from dataclasses import dataclass
from typing import Tuple, Dict, List

NodeId = int
EdgeId = Tuple[NodeId, NodeId]


@dataclass
class Node:
    id: NodeId
    next_nodes: List[NodeId]
    lat: float
    lon: float


@dataclass
class Edge:
    id: EdgeId
    length: float
    maxspeed: int


@dataclass
class Graph:
    nodes: Dict[NodeId, Node]
    edges: Dict[EdgeId, Edge]
