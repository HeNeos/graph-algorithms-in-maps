use crate::graph::{Edge, EdgeId, Graph, Node, NodeId};
use aws_sdk_s3::operation::get_object::GetObjectOutput;
use aws_sdk_s3::Client;

use std::collections::HashMap;

type NodesJson = HashMap<String, HashMap<String, String>>;
type EdgesJson = HashMap<String, HashMap<String, String>>;

pub async fn get_graph(
    client: &Client,
    bucket: &String,
    key: &String,
) -> Result<(NodesJson, EdgesJson), anyhow::Error> {
    let nodes_object: GetObjectOutput = client
        .get_object()
        .bucket(bucket)
        .key(format!("nodes-{}.json", key))
        .response_content_type("application/json")
        .send()
        .await?;

    let edges_object: GetObjectOutput = client
        .get_object()
        .bucket(bucket)
        .key(format!("edges-{}.json", key))
        .response_content_type("application/json")
        .send()
        .await?;

    let nodes_bytes = nodes_object.body.collect().await?.into_bytes();
    let edges_bytes = edges_object.body.collect().await?.into_bytes();
    let nodes_response = std::str::from_utf8(&nodes_bytes)?;
    let edges_response = std::str::from_utf8(&edges_bytes)?;
    let parsed_nodes: NodesJson = serde_json::from_str(nodes_response).unwrap();
    let parsed_edges: EdgesJson = serde_json::from_str(edges_response).unwrap();

    Ok((parsed_nodes, parsed_edges))
}

pub async fn upload_path(
    client: &Client,
    bucket: &String,
    key: &str,
    graph_path: &HashMap<NodeId, NodeId>,
    visited_edges: &Vec<EdgeId>,
    active_edges: &Vec<EdgeId>,
) -> bool {
    let path_json: String =
        serde_json::to_string(&graph_path).expect("Failed to serialize the path");
    let visited_json: String =
        serde_json::to_string(&visited_edges).expect("Failed to serialize the visited edges");
    let active_json: String =
        serde_json::to_string(&active_edges).expect("Failed to serialize the active edges");

    let mut response: bool = true;
    for (json_file, name) in [
        (path_json, "path"),
        (visited_json, "visited"),
        (active_json, "active"),
    ] {
        let resp = client
            .put_object()
            .bucket(bucket)
            .key(format!("{}-{}.json", &name, key))
            .body(json_file.into_bytes().into())
            .send()
            .await;
        assert!(resp.is_ok(), "{resp:?}");
        response = response && resp.is_ok();
    }

    return response;
}

pub async fn parse_graph(nodes: &NodesJson, edges: &EdgesJson) -> Result<Graph, anyhow::Error> {
    let mut graph_nodes: HashMap<NodeId, Node> = HashMap::new();
    let mut graph_edges: HashMap<EdgeId, Edge> = HashMap::new();

    let mut to_nodes_by_node: HashMap<NodeId, Vec<NodeId>> = HashMap::new();

    let all_nodes: &HashMap<String, String> = nodes.get("Nodes").unwrap();
    let all_edges: &HashMap<String, String> = edges.get("Edges").unwrap();

    for (id, edge_data) in all_edges {
        let (u, v) = {
            let mut ids = id.split(',');
            (
                ids.next().unwrap().parse::<NodeId>().unwrap(),
                ids.next().unwrap().parse::<NodeId>().unwrap(),
            )
        };
        let (length, maxspeed) = {
            let mut data = edge_data.split(',');
            (
                data.next().unwrap().parse::<f64>().unwrap(),
                data.next().unwrap().parse::<i64>().unwrap(),
            )
        };
        let current_edge_id: EdgeId = (u, v);
        let current_edge = Edge {
            id: current_edge_id,
            length: length,
            maxspeed: maxspeed,
        };
        graph_edges.insert(current_edge_id, current_edge);
        to_nodes_by_node.entry(u).or_insert(vec![]).push(v);
    }

    for (node_id, node_data) in all_nodes {
        let u = node_id.parse::<NodeId>().unwrap();
        let (lat, lon) = {
            let mut data = node_data.split(',');
            (
                data.next().unwrap().parse::<f64>().unwrap(),
                data.next().unwrap().parse::<f64>().unwrap(),
            )
        };
        let empty_vec: Vec<NodeId> = Vec::new();
        let next_nodes: &Vec<NodeId> = match to_nodes_by_node.get(&u) {
            Some(v) => v,
            None => &empty_vec,
        };
        let node = Node {
            id: u,
            next_nodes: next_nodes.clone(),
            lat: lat,
            lon: lon,
        };
        graph_nodes.insert(u as NodeId, node);
    }

    let graph = Graph {
        nodes: graph_nodes,
        edges: graph_edges,
    };

    return Ok(graph);
}

pub async fn find_distance_by_nodes(u_lat: f64, u_lon: f64, v_lat: f64, v_lon: f64) -> f64 {
    let earth_radius = 6371.0088;
    let lat1 = u_lat.to_radians();
    let lng1 = u_lon.to_radians();
    let lat2 = v_lat.to_radians();
    let lng2 = v_lon.to_radians();
    let lat = lat2 - lat1;
    let lng = lng2 - lng1;
    let d = (lat * 0.5).sin().powf(2.0) + lat1.cos() * lat2.cos() * (lng * 0.5).sin().powf(2.0);
    let haversine_kernel = 2.0 * d.sqrt().asin();
    return earth_radius * haversine_kernel;
}
