use std::cmp::Ordering;
use std::collections::HashMap;

pub type NodeId = i64;
pub type EdgeId = (NodeId, NodeId);

#[derive(Clone)]
pub struct Node {
    pub id: NodeId,
    pub lat: f64,
    pub lon: f64,
    pub next_nodes: Vec<NodeId>,
}

#[derive(Clone)]
pub struct Edge {
    pub id: EdgeId,
    pub length: f64,
    pub maxspeed: i64,
}

pub struct Graph {
    pub nodes: HashMap<NodeId, Node>,
    pub edges: HashMap<EdgeId, Edge>,
}

#[derive(Copy, Clone)]
pub struct State {
    pub weight: f64,
    pub node_id: NodeId,
}

impl Eq for State {}

impl PartialEq for State {
    fn eq(&self, other: &Self) -> bool {
        self.weight == other.weight && self.node_id == other.node_id
    }
}

impl Ord for State {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .weight
            .partial_cmp(&self.weight)
            .unwrap_or(Ordering::Equal)
            .then_with(|| other.node_id.cmp(&self.node_id))
    }
}

impl PartialOrd for State {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}
