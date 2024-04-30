use std::collections::{BinaryHeap, HashMap, HashSet};
use std::f64::INFINITY;

use crate::graph::{NodeId, EdgeId, Node, Edge, Graph, State};

pub async fn dijkstra(
  graph: &Graph,
  source: NodeId,
  destination: NodeId,
) -> Option<(HashMap<NodeId, NodeId>, f64, i64)> {
  let mut weight_from_source: HashMap<NodeId, f64> = HashMap::new();
  let mut visited_nodes: HashSet<NodeId> = HashSet::new();
  let mut previous_node: HashMap<NodeId, NodeId> = HashMap::new();

  let mut iteration: i64 = 0;
  let mut priority_queue: BinaryHeap<State> = BinaryHeap::new();
  priority_queue.push(State {
    weight: 0.,
    node_id: source,
  });
  while let Some(State { weight, node_id }) = priority_queue.pop() {
    if node_id == destination {
      return Some((previous_node, weight, iteration));
    }
    let current_node: Node = graph.nodes.get(&node_id).unwrap().clone();
    if visited_nodes.contains(&node_id) {
      continue;
    }
    visited_nodes.insert(node_id);
    let next_nodes_id: Vec<NodeId> = current_node.next_nodes;
    for next_node_id in &next_nodes_id {
      iteration += 1;
      let current_edge_id: EdgeId = (node_id, *next_node_id);
      let current_edge: Edge = graph.edges.get(&current_edge_id).unwrap().clone();
      let edge_weight: f64 = (current_edge.length / 1000.) / (current_edge.maxspeed as f64);
      let new_weight: f64 = weight + edge_weight;
      if weight_from_source
        .get(next_node_id)
        .copied()
        .unwrap_or(INFINITY)
        > new_weight
      {
        weight_from_source.insert(*next_node_id, new_weight);
        previous_node.insert(*next_node_id, node_id);
        priority_queue.push(State {
          weight: new_weight,
          node_id: *next_node_id,
        });
      }
    }
  }
  return None;
}
