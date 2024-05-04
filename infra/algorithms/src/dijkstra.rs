use std::collections::{BinaryHeap, HashMap, HashSet};
use std::f64::INFINITY;

use crate::graph::{Edge, EdgeId, Graph, Node, NodeId, State};

pub async fn dijkstra(
    graph: &Graph,
    source: NodeId,
    destination: NodeId,
) -> Option<(HashMap<NodeId, NodeId>, Vec<EdgeId>, Vec<EdgeId>, f64, i64)> {
    let mut weight_from_source: HashMap<NodeId, f64> = HashMap::new();
    let mut visited_nodes: HashSet<NodeId> = HashSet::new();
    let mut previous_node: HashMap<NodeId, NodeId> = HashMap::new();
    let mut visited_edges: Vec<EdgeId> = Vec::new();
    let mut active_edges: HashSet<EdgeId> = HashSet::new();

    let mut iteration: i64 = 0;
    let mut priority_queue: BinaryHeap<State> = BinaryHeap::new();
    priority_queue.push(State {
        weight: 0.,
        node_id: source,
    });
    weight_from_source.insert(source, 0.0);
    while let Some(State { weight: _, node_id }) = priority_queue.pop() {
        let weight_to_node = weight_from_source
            .get(&node_id)
            .copied()
            .unwrap_or(INFINITY);
        if node_id == destination {
            return Some((
                previous_node,
                visited_edges,
                Vec::from_iter(active_edges),
                weight_to_node,
                iteration,
            ));
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
            visited_edges.push(current_edge_id);
            active_edges.remove(&current_edge_id);
            let edge_weight: f64 = (current_edge.length / 1000.) / (current_edge.maxspeed as f64);
            let new_weight: f64 = weight_to_node + edge_weight;
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
                let nodes_to_visit: Vec<NodeId> =
                    graph.nodes.get(&next_node_id).unwrap().clone().next_nodes;
                for to_visit_node_id in &nodes_to_visit {
                    active_edges.insert((*next_node_id, *to_visit_node_id));
                }
            }
        }
    }
    return None;
}
