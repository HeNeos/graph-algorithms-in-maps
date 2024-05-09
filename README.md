# Graph algorithms in maps

## Architecture diagram

![architecture diagram](https://raw.githubusercontent.com/HeNeos/graph-algorithms-in-maps/main/GraphAlgorithmsInMaps.drawio.png)

## Usage

Deploy the stacks in the following order:

1. DatabaseStack
2. S3Stack
3. SfnStack
4. ApiStack

`ApiStack` outputs an endpoint to make queries.

## Description

### Scripts

Most of the time, if you're doing a new query, the lambda `getGraph` will first download the graph and send it to `S3` for future queries. However, this step commonly take a long time (around 2-4 min, depending map size).

If you already has a list of pre-defined places where you will do the queries, you can fill the `cities.json` with the `country` and `city` of the place you'll query.

```json
[
  {
    "country": "Germany",
    "city": "Berlin",
  },
  ...
]
```

Notice that, you only have to put the city and country, then use the script `fill_cities.py` to modify this json with a `lat` and `lon` for a point in the city/country. Then, you can use the script `upload_graph.py` to download the graph and then upload it to S3 and Dynamo.

### Algorithms

Algorithms are lambda functions implemented in `Rust`.

#### BFS

Classic graph-search algorithm, this algorithm only finds a path between the `source` and `destination`, it doesn't try to optimize the path in any way.

#### Dijkstra

Classic graph path finding algorithm, instead of using a `priority queue`, it uses a `heap`, which in this scenario behaves similar. Dijkstra algorithm try to find the fastest path between `source` and `destination`. Notice that, it finds the `fastest`, not `shortest`, this is possible since the library `osmnx` provide information about the maximum speed allowed in an `edge`. Of course, this algorithm can also find the `shortest`, just set the maximum speed allowed to a constant value for all the edges.

#### A*

Heuristic graph path finding algorithm, this algorithm improves dijkstra using a heuristic function that met some *conditions*. Classic heuristic the eulerian distance, which can be calculated from the `latitude` and `longitude` and using the `haversine distance`. A slightly modification is needed in order to use for `fastest`, in this case you can set a `maximum speed` along all the edges in the map, and then divide the distance with the maximum speed, so the heuristic is:

>>> Shortest time between two nodes is the eulerian distance divided by the maximum speed

$$
\text{time}(u, v) = \frac{\text{dist}(u, v)}{\overline{\text{max speed}}} \leq \frac{\vert (u, v) \vert}{\overline{\text{max speed}}} \leq \frac{\vert (u, v) \vert}{\text{max speed}}
$$

Maximum speed is not a constant value, and should be calculated for each graph, lower maximum speed leads to a better heuristic, this value is currently setted to 150.0 km/h.

#### A* enhanced

I don't have a proof of the correctness of this algorithm modification, so it's probably that it can't even find a path, however in most cases it outperforms classic A*.

### Buckets

#### graphsBucket

Store the graph information for a `city` and `country`.

1. `{graphId}.graphml`: Graph information from `networkx` library.
2. `*-{graphId}.json`: Simple graph representation using only nodes and edges.

#### graphsPlotsBucket

Store the results for a request.

1. `*.json`: Edges to plot in the graph
2. `*.png`: Plot of the request

A request always generates a plot and three edges data: `path`, `active`, `visited`.

1. Path edges are `edges` that belongs to the `fastest` path.
2. Active edges are `edges` that are going to be processed for the algorithm.
3. Visited edges are `edges` already processed by the algorithm.
