use queues::*;

use std::collections::{HashMap, HashSet};

use crate::graph::{NodeId, Node, Graph};

pub async fn bfs(
  graph: &Graph,
  source: NodeId,
  destination: NodeId,
) -> Option<HashMap<NodeId, NodeId>> {
  let mut visited_nodes: HashSet<NodeId> = HashSet::new();
  let mut previous_node: HashMap<NodeId, NodeId> = HashMap::new();

  let mut queue: Queue<NodeId> = queue![];
  let _ = queue.add(source);
  while queue.size() > 0 {
    let node_id: NodeId = queue.peek().unwrap();
    let _ = queue.remove();
    if node_id == destination { return Some(previous_node); }
    let current_node: Node = graph.nodes.get(&node_id).unwrap().clone();
    let next_nodes_id: Vec<NodeId> = current_node.next_nodes;
    for next_node_id in &next_nodes_id {
      if visited_nodes.contains(&node_id) { continue; }
      previous_node.insert(*next_node_id, node_id);
      let _ = queue.add(*next_node_id);
      visited_nodes.insert(node_id);
    }
  }
  return None;
}
