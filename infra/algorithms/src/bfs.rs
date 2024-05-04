use queues::*;

use std::collections::{HashMap, HashSet};

use crate::graph::{EdgeId, Graph, Node, NodeId};

pub async fn bfs(
    graph: &Graph,
    source: NodeId,
    destination: NodeId,
) -> Option<(HashMap<NodeId, NodeId>, Vec<EdgeId>, Vec<EdgeId>, f64, i64)> {
    let mut visited_nodes: HashSet<NodeId> = HashSet::new();
    let mut previous_node: HashMap<NodeId, NodeId> = HashMap::new();
    let mut visited_edges: Vec<EdgeId> = Vec::new();
    let mut active_edges: HashSet<EdgeId> = HashSet::new();

    let mut iteration: i64 = 0;
    let mut queue: Queue<NodeId> = queue![];
    let _ = queue.add(source);
    while queue.size() > 0 {
        let node_id: NodeId = queue.peek().unwrap();
        let _ = queue.remove();
        if node_id == destination {
            return Some((
                previous_node,
                visited_edges,
                Vec::from_iter(active_edges),
                iteration as f64,
                iteration,
            ));
        }
        let current_node: Node = graph.nodes.get(&node_id).unwrap().clone();
        let next_nodes_id: Vec<NodeId> = current_node.next_nodes;
        for next_node_id in &next_nodes_id {
            iteration += 1;
            if visited_nodes.contains(next_node_id) {
                continue;
            }
            let current_edge_id: EdgeId = (node_id, *next_node_id);
            visited_edges.push(current_edge_id);
            active_edges.remove(&current_edge_id);
            previous_node.insert(*next_node_id, node_id);
            let _ = queue.add(*next_node_id);
            visited_nodes.insert(node_id);
            let nodes_to_visit: Vec<NodeId> =
                graph.nodes.get(&next_node_id).unwrap().clone().next_nodes;
            for to_visit_node_id in &nodes_to_visit {
                active_edges.insert((*next_node_id, *to_visit_node_id));
            }
        }
    }
    return None;
}
