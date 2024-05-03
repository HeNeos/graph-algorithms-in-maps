use queues::*;

use std::collections::{HashMap, HashSet};

use crate::graph::{Graph, Node, NodeId};

pub async fn bfs(
    graph: &Graph,
    source: NodeId,
    destination: NodeId,
) -> Option<(HashMap<NodeId, NodeId>, f64, i64)> {
    let mut visited_nodes: HashSet<NodeId> = HashSet::new();
    let mut previous_node: HashMap<NodeId, NodeId> = HashMap::new();

    let mut iteration: i64 = 0;
    let mut queue: Queue<NodeId> = queue![];
    let _ = queue.add(source);
    while queue.size() > 0 {
        let node_id: NodeId = queue.peek().unwrap();
        let _ = queue.remove();
        if node_id == destination {
            return Some((previous_node, iteration as f64, iteration));
        }
        let current_node: Node = graph.nodes.get(&node_id).unwrap().clone();
        let next_nodes_id: Vec<NodeId> = current_node.next_nodes;
        for next_node_id in &next_nodes_id {
            iteration += 1;
            if visited_nodes.contains(&node_id) {
                continue;
            }
            previous_node.insert(*next_node_id, node_id);
            let _ = queue.add(*next_node_id);
            visited_nodes.insert(node_id);
        }
    }
    return None;
}
