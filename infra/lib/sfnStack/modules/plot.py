from matplotlib.colors import Colormap
import matplotlib as mpl

colormap: Colormap = mpl.colormaps["viridis"]


class UnvisitedEdge:
    color = colormap(0.25)
    alpha: float = 0.4
    linewidth: float = 0.4


class VisitedEdge:
    color = colormap(0.45)
    alpha: float = 0.6
    linewidth: float = 0.5


class ActiveEdge:
    color = colormap(0.7)
    alpha: float = 0.8
    linewidth: float = 0.6


class PathEdge:
    color = colormap(1.0)
    alpha: float = 1.0
    linewidth: float = 0.7


NODE_SIZE: float = 0.20
NODE_ALPHA: float = 0.08

POINT_SIZE: float = 18
POINT_ALPHA: float = 1
