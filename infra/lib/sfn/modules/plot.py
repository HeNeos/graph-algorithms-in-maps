import matplotlib.pyplot as plt

class UnvisitedEdge:
  color = plt.cm.viridis(0.25)
  alpha = 0.35
  linewidth = 0.2

class VisitedEdge:
  color = plt.cm.viridis(0.45)
  alpha = 0.55
  linewidth = 0.35

class ActiveEdge:
  color = plt.cm.viridis(0.7)
  alpha = 0.8
  linewidth = 0.55

class PathEdge:
  color = plt.cm.viridis(1.0)
  alpha = 1.0
  linewidth = 0.7

NODE_SIZE = 0.085
NODE_ALPHA = 0.06

POINT_SIZE = 25
POINT_ALPHA = 1
