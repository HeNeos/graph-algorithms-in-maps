use crate::utils::find_distance_by_nodes;
use std::collections::{BinaryHeap, HashMap, HashSet};
use std::f64::INFINITY;

use crate::graph::{Edge, EdgeId, Graph, Node, NodeId, State};

pub async fn a_star_enhanced(
    graph: &Graph,
    source: NodeId,
    destination: NodeId,
) -> Option<(HashMap<NodeId, NodeId>, Vec<EdgeId>, Vec<EdgeId>, f64, i64)> {
    let max_speed_allowed: f64 = 150.0;
    let mut weight_from_source: HashMap<NodeId, f64> = HashMap::new();
    let mut visited_nodes: HashSet<NodeId> = HashSet::new();
    let mut previous_node: HashMap<NodeId, NodeId> = HashMap::new();
    let mut visited_edges: Vec<EdgeId> = Vec::new();
    let mut active_edges: HashSet<EdgeId> = HashSet::new();

    let source_node = graph.nodes.get(&source).unwrap().clone();
    let destination_node = graph.nodes.get(&destination).unwrap().clone();

    let mut iteration: i64 = 0;
    let mut priority_queue: BinaryHeap<State> = BinaryHeap::new();
    let mut best_node_distance: f64 = INFINITY;
    let source_to_destination_min_distance = find_distance_by_nodes(
        source_node.lat,
        source_node.lon,
        destination_node.lat,
        destination_node.lon,
    )
    .await;
    priority_queue.push(State {
        weight: 0.,
        node_id: source,
    });
    weight_from_source.insert(source, 0.0);
    let destination_node = graph.nodes.get(&destination).unwrap().clone();
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
        let mut level_max_distance: f64 = INFINITY;
        let next_nodes_id: Vec<NodeId> = current_node.next_nodes;
        for next_node_id in &next_nodes_id {
            iteration += 1;
            let next_node: Node = graph.nodes.get(&next_node_id).unwrap().clone();
            let current_edge_id: EdgeId = (node_id, *next_node_id);
            let current_edge: Edge = graph.edges.get(&current_edge_id).unwrap().clone();
            visited_edges.push(current_edge_id);
            active_edges.remove(&current_edge_id);
            let edge_weight: f64 = (current_edge.length / 1000.) / (current_edge.maxspeed as f64);
            let destination_distance: f64 = find_distance_by_nodes(
                next_node.lat,
                next_node.lon,
                destination_node.lat,
                destination_node.lon,
            )
            .await;
            let heuristic_weight: f64 = destination_distance / max_speed_allowed;
            let new_weight: f64 = weight_to_node + edge_weight;
            if weight_from_source
                .get(next_node_id)
                .copied()
                .unwrap_or(INFINITY)
                > new_weight
            {
                weight_from_source.insert(*next_node_id, new_weight);
                previous_node.insert(*next_node_id, node_id);
                if level_max_distance != INFINITY {
                    level_max_distance = f64::max(level_max_distance, destination_distance);
                } else {
                    level_max_distance = destination_distance;
                }
                if best_node_distance != INFINITY {
                    if destination_distance > 2.0 * best_node_distance {
                        continue;
                    } else {
                        best_node_distance =
                            f64::min(source_to_destination_min_distance, destination_distance);
                    }
                }
                priority_queue.push(State {
                    weight: new_weight + heuristic_weight,
                    node_id: *next_node_id,
                });
                let nodes_to_visit: Vec<NodeId> =
                    graph.nodes.get(&next_node_id).unwrap().clone().next_nodes;
                for to_visit_node_id in &nodes_to_visit {
                    active_edges.insert((*next_node_id, *to_visit_node_id));
                }
            }
        }
        if level_max_distance != INFINITY {
            best_node_distance = f64::min(best_node_distance, level_max_distance);
        }
    }
    return None;
}
