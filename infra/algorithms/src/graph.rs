use std::collections::HashMap;

type NodeId = i64;
type EdgeId = (NodeId, NodeId);

#[derive(Clone)]
pub struct Node {
  pub id: NodeId,
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
