from typing import Union, TypedDict, Optional, Literal

Algorithms = Literal["dijkstra", "a_star", "a_star_enhanced"]


class EventCoords(TypedDict, total=False):
    algorithm: Optional[Algorithms]
    source_lat: str
    source_lon: str
    dest_lat: str
    dest_lon: str


class EventAddress(TypedDict, total=False):
    algorithm: Optional[Algorithms]
    source: str
    dest: str


class EventQueryString(TypedDict, total=False):
    querystring: EventAddress | EventCoords


Event = Union[EventCoords, EventAddress, EventQueryString]
