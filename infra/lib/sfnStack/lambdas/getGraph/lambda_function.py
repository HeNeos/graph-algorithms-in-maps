import osmnx as ox
from typing import Optional, Dict, cast

from lambdas.getGraph.utils import get_lat_lon, get_current_location, haversine, get_ids
from lambdas.getGraph.modules.coordinates import Coordinates

from modules.graph import NodeId, EdgeId
from modules.event import Event, EventQueryString, EventCoords, EventAddress, Algorithms


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
