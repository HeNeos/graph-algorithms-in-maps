import matplotlib.pyplot as plt


class UnvisitedEdge:
    color = plt.cm.viridis(0.25)
    alpha = 0.4
    linewidth = 0.4


class VisitedEdge:
    color = plt.cm.viridis(0.45)
    alpha = 0.6
    linewidth = 0.5


class ActiveEdge:
    color = plt.cm.viridis(0.7)
    alpha = 0.8
    linewidth = 0.6


class PathEdge:
    color = plt.cm.viridis(1.0)
    alpha = 1.0
    linewidth = 0.7


NODE_SIZE = 0.20
NODE_ALPHA = 0.08

POINT_SIZE = 18
POINT_ALPHA = 1
