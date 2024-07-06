from typing import Optional, Tuple, List, Dict, Union
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from networkx import MultiDiGraph


def graph_from_place(
    query: str | List[str] | Dict[str, str],
    network_type: str = "all_private",
    simplify: bool = True,
    retain_all: bool = False,
    truncate_by_edge: bool = False,
    which_result: Optional[int] = None,
    buffer_dist: Optional[float] = None,
    clean_periphery: Optional[bool] = None,
    custom_filter: Optional[str] = None,
) -> Optional[MultiDiGraph]: ...


def save_graphml(
    G: MultiDiGraph,
    filepath: Optional[str] = None,
    gephi: bool = False,
    encoding: str = "utf-8",
) -> None: ...


def graph_from_point(center: Tuple[float, float], dist: int, network_type: str = "all_private") -> MultiDiGraph: ...


def load_graphml(
    filepath: Optional[str] = None, graphml_str: Optional[str] = None
) -> MultiDiGraph: ...


def nearest_nodes(
    G: MultiDiGraph,
    X: Union[List[float], float],
    Y: Union[List[float], float],
    return_dist: bool = False,
) -> int: ...


def config(use_cache: bool = True, cache_folder: str = "./cache") -> None: ...


def plot_graph(
    G: MultiDiGraph,
    node_size: Union[List[float], float] = 15.0,
    node_alpha: Optional[Union[List[float], float]] = None,
    edge_color: Union[List[str], str] = "#999999",
    edge_alpha: Optional[Union[List[float], float]] = None,
    edge_linewidth: Union[List[float], float] = 1.0,
    node_color: Union[List[str], str] = "w",
    bgcolor: "str" = "#111111",
    show: bool = True,
    close: bool = False,
) -> Tuple[Figure, Axes]: ...
