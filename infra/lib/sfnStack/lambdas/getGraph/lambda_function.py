import math
import os
import json
import boto3
import requests

from dataclasses import dataclass
from uuid import uuid4
import osmnx as ox
from networkx import MultiDiGraph
from networkx import Graph as NGraph
from typing import Tuple, Optional, Dict, List, Union, cast

from modules.graph import NodeId, EdgeId, Node, Edge, Graph
from modules.event import Event, EventQueryString, EventCoords, EventAddress, Algorithms


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

HEADERS = {"User-Agent": "GraphMapsApplication/1.0"}


def get_current_location(
    coordinates: Coordinates,
) -> Tuple[Optional[str], Optional[str]]:
    latitude, longitude = (
        round(coordinates.latitude, 6),
        round(coordinates.longitude, 6),
    )
    url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={latitude}&lon={longitude}"
    response = requests.get(url, headers=HEADERS)
    data: Dict[str, Dict[str, str]] = response.json()
    if "address" not in data:
        return (None, None)
    address = data["address"]
    city: Optional[str] = address.get("city", None)
    country: Optional[str] = address.get("country", None)
    return (city, country)


def get_lat_lon(address: str) -> Optional[Coordinates]:
    url = "https://nominatim.openstreetmap.org/search"
    params: Dict[str, str | int] = {"q": address, "format": "json", "limit": 1}
    response = requests.get(url, params=params, headers=HEADERS)
    if response.status_code == 200 and response.json():
        location = response.json()[0]
        return Coordinates(
            latitude=float(location["lat"]), longitude=float(location["lon"])
        )
    return None


def get_max_speed(
    edge: Dict[str, List[str] | str | int], min_max_speed_allowed: int = 30
) -> int:
    max_speed = min_max_speed_allowed
    if "maxspeed" in edge:
        max_speeds = edge["maxspeed"]
        if isinstance(max_speeds, list):
            speeds: List[int] = [
                int(speed) for speed in max_speeds if speed and speed.isnumeric()
            ]
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
    for edge in cast(List[Tuple[NodeId, NodeId, float]], graph.edges):
        u, v, _ = edge
        current_edge: Dict[str, List[str] | str | int] = graph.edges[edge]  # type: ignore
        all_edges[(u, v)] = Edge(
            id=(u, v),
            length=cast(float, current_edge["length"]),
            maxspeed=get_max_speed(current_edge),
        )
        if u not in to_node_by_node:
            to_node_by_node[u] = []
        to_node_by_node[u].append(v)
    all_nodes: Dict[NodeId, Node] = {
        node: Node(
            id=node,
            next_nodes=to_node_by_node.get(node, []),
            lat=graph.nodes[node]["y"],
            lon=graph.nodes[node]["x"],
        )
        for node in cast(List[NodeId], graph.nodes)
    }
    return Graph(nodes=all_nodes, edges=all_edges)


def store_graph(graph: Graph, key: str) -> None:
    nodes: Dict[str, Dict[str, str]] = {
        "Nodes": {
            str(node): f"{node_data.lat},{node_data.lon}"
            for node, node_data in graph.nodes.items()
        }
    }
    edges: Dict[str, Dict[str, str]] = {
        "Edges": {
            ",".join(str(x) for x in edge_id): ",".join(
                [str(edge.length), str(edge.maxspeed)]
            )
            for edge_id, edge in graph.edges.items()
        }
    }
    graphs_bucket.put_object(Key=f"nodes-{key}.json", Body=json.dumps(nodes))
    graphs_bucket.put_object(Key=f"edges-{key}.json", Body=json.dumps(edges))


def download_graph(country: str, city: str) -> Tuple[MultiDiGraph, str]:
    G: MultiDiGraph = cast(
        MultiDiGraph,
        ox.graph_from_place({"city": city, "country": country}, network_type="drive"),
    )
    key: str = uuid4().hex
    # TODO: Send it directly to S3
    ox.save_graphml(G, f"/tmp/{key}.graphml")
    graphs_bucket.upload_file(f"/tmp/{key}.graphml", f"{key}.graphml")
    return G, key


def download_graph_by_distance(
    center: Coordinates, distance: float
) -> Tuple[MultiDiGraph, str]:
    G: MultiDiGraph = ox.graph_from_point(
        (center.latitude, center.longitude), dist=int(distance)
    )
    key: str = uuid4().hex
    ox.save_graphml(G, f"/tmp/{key}.graphml")
    graphs_bucket.upload_file(f"/tmp/{key}.graphml", f"{key}.graphml")
    return G, key


def get_multidigraph(graph_id: str) -> MultiDiGraph:
    graphs_bucket.download_file(
        Key=f"{graph_id}.graphml", Filename=f"/tmp/{graph_id}.graphml"
    )
    return ox.load_graphml(f"/tmp/{graph_id}.graphml")


def get_graph_id(country: str, city: str) -> Optional[str]:
    response = graphs_table.get_item(Key={"Country": country, "City": city})

    item: Dict[str, str] = cast(Dict[str, str], response.get("Item", {}))
    graph_id: Optional[str] = item.get("GraphId", None)
    return graph_id


def get_graph(country: str, city: str) -> Tuple[MultiDiGraph, str]:
    graph_id = get_graph_id(country, city)
    if graph_id is None:
        G, graph_id = download_graph(country, city)
        graph: Graph = generate_graph(G)
        store_graph(graph, graph_id)
        graphs_table.put_item(
            Item={"Country": country, "City": city, "GraphId": graph_id}
        )
    else:
        G = get_multidigraph(graph_id)

    return G, graph_id


def get_node_id(graph: Union[MultiDiGraph, NGraph], location: Coordinates) -> NodeId:
    return cast(NodeId, ox.nearest_nodes(graph, location.longitude, location.latitude))  # type: ignore


def get_ids(
    country: str,
    city: str,
    source_coordinates: Coordinates,
    destination_coordinates: Coordinates,
    use_distance: Optional[float],
) -> Tuple[str, NodeId, NodeId]:
    if use_distance is None:
        graph_id = get_graph_id(country, city)
        if graph_id is None:
            G, graph_id = download_graph(country, city)
            graph: Graph = generate_graph(G)
            store_graph(graph, graph_id)
            graphs_table.put_item(
                Item={"Country": country, "City": city, "GraphId": graph_id}
            )
            source = get_node_id(G, source_coordinates)
            destination = get_node_id(G, destination_coordinates)
            return graph_id, source, destination
        else:
            try:
                source_graph = ox.graph_from_point(
                    (source_coordinates.latitude, source_coordinates.longitude),
                    dist=200,
                    network_type="drive",
                )
                destination_graph = ox.graph_from_point(
                    (
                        destination_coordinates.latitude,
                        destination_coordinates.longitude,
                    ),
                    dist=200,
                    network_type="drive",
                )
            except ValueError as err:
                print(
                    "Not found a valid node around source or destination in 200m around"
                )
                print(err)
                raise
            source = get_node_id(source_graph, source_coordinates)
            destination = get_node_id(destination_graph, destination_coordinates)
            return graph_id, source, destination
    else:
        latitude = (source_coordinates.latitude + destination_coordinates.longitude) / 2
        longitude = (
            source_coordinates.longitude + destination_coordinates.longitude
        ) / 2
        G, graph_id = download_graph_by_distance(
            Coordinates(latitude=latitude, longitude=longitude), 2 * 1000 * use_distance
        )
        graph: Graph = generate_graph(G)  # type: ignore
        store_graph(graph, graph_id)
        source = get_node_id(G, source_coordinates)
        destination = get_node_id(G, destination_coordinates)
        return graph_id, source, destination


def haversine(source: Coordinates, destination: Coordinates) -> float:
    earth_radius: float = 6371.0088
    delta_lat: float = destination.latitude - source.latitude
    delta_lon: float = destination.longitude - source.longitude
    dist: float = pow(math.sin((delta_lat / 2)), 2) + math.cos(
        source.latitude
    ) * math.cos(destination.latitude) * pow(math.sin(delta_lon / 2), 2)
    haversine_kernel: float = 2 * math.asin(math.sqrt(dist))
    return earth_radius * haversine_kernel


def lambda_handler(
    raw_event: Event, _: Dict[str, str]
) -> Optional[Dict[str, NodeId | EdgeId | str]]:
    if "querystring" in raw_event:
        raw_event = cast(EventQueryString, raw_event)
        event: EventCoords | EventAddress = raw_event["querystring"]  # type: ignore
    else:
        event = cast(EventCoords | EventAddress, raw_event)

    algorithm: Algorithms = event.get("algorithm") or "dijkstra"
    if "source" in event and "dest" in event:
        event_with_address = cast(EventAddress, event)
        source_coordinates = get_lat_lon(event_with_address["source"])  # type: ignore
        dest_coordinates = get_lat_lon(event_with_address["dest"])  # type: ignore
        if source_coordinates is None or dest_coordinates is None:
            print("Not able to find the address for you source or dest")
            return None
        else:
            event_with_coords = EventCoords(
                algorithm=algorithm,
                source_lat=str(source_coordinates.latitude),
                source_lon=str(source_coordinates.longitude),
                dest_lat=str(dest_coordinates.latitude),
                dest_lon=str(dest_coordinates.longitude),
            )
    else:
        event_with_coords = cast(EventCoords, event)

    source_coordinates = Coordinates(
        latitude=float(event_with_coords["source_lat"]),  # type: ignore
        longitude=float(event_with_coords["source_lon"]),  # type: ignore
    )
    destination_coordinates = Coordinates(
        latitude=float(event_with_coords["dest_lat"]),  # type: ignore
        longitude=float(event_with_coords["dest_lon"]),  # type: ignore
    )

    source_location = get_current_location(source_coordinates)
    destination_location = get_current_location(destination_coordinates)

    source_city, source_country = source_location
    destination_city, destination_country = destination_location

    if not all([source_city, source_country, destination_city, destination_country]):
        print("No possible to find a valid location")
        if source_city is None and destination_city is None:
            return None
        if source_country is None and destination_country is None:
            return None
        if source_country != destination_country:
            return None

    if source_city is None or source_country is None:
        print("Invalid locations")
        return None

    use_distance: Optional[float]
    if source_city != destination_city or source_country != destination_country:
        print("Source and destination are not in the same city/country")
        use_distance = haversine(
            source_coordinates,
            destination_coordinates,
        )
        print("Not possible to cache, downloading by distance")
    else:
        use_distance = None

    ox.config(use_cache=True, cache_folder="/tmp/osmnx_cache")
    graph_id, source, destination = get_ids(
        source_country,
        source_city,
        source_coordinates,
        destination_coordinates,
        use_distance,
    )

    return {
        "source": source,
        "destination": destination,
        "key": graph_id,
        "algorithm": algorithm,
    }
