use std::cmp::Ordering;
use std::collections::{BinaryHeap, HashMap, HashSet};
use std::env;
use std::f64::INFINITY;
use std::process::exit;
use uuid::Uuid;

use aws_config::meta::region::RegionProviderChain;
use aws_sdk_s3::operation::{
    get_object::{GetObjectError, GetObjectOutput},
    put_object::{PutObjectError, PutObjectOutput},
};
use aws_sdk_s3::{error::SdkError, Client};
use lambda_runtime::{run, service_fn, tracing, Error, LambdaEvent};

use serde::{Deserialize, Serialize};

type NodeId = i64;
type EdgeId = (NodeId, NodeId);
type NodesJson = HashMap<String, Vec<String>>;
type EdgesJson = HashMap<String, HashMap<String, String>>;

#[derive(Deserialize)]
struct Request {
    key: String,
    source: NodeId,
    destination: NodeId,
}

#[derive(Serialize)]
struct Response {
    iterations: i64,
    weight: f64,
    solution_key: String,
    source: NodeId,
    destination: NodeId,
    graph_id: String
}

#[derive(Clone)]
struct Node {
    id: NodeId,
    next_nodes: Vec<NodeId>,
}

#[derive(Clone)]
struct Edge {
    id: EdgeId,
    length: f64,
    maxspeed: i64,
}

struct Graph {
    nodes: HashMap<NodeId, Node>,
    edges: HashMap<EdgeId, Edge>,
}

#[derive(Copy, Clone)]
struct State {
    weight: f64,
    node_id: NodeId,
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

async fn get_graph(
    client: &Client,
    bucket: &String,
    key: &String,
) -> Result<(NodesJson, EdgesJson), anyhow::Error> {
    let nodes_object = client
        .get_object()
        .bucket(bucket)
        .key(format!("nodes-{}.json", key))
        .response_content_type("application/json")
        .send()
        .await?;

    let edges_object = client
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

async fn upload_path(
    client: &Client,
    bucket: &String,
    key: &str,
    graph_path: &HashMap<NodeId, NodeId>,
) -> Result<PutObjectOutput, SdkError<PutObjectError>> {
    let path_json = serde_json::to_string(&graph_path).expect("Failed to serialize the path");
    client
        .put_object()
        .bucket(bucket)
        .key(key)
        .body(path_json.into_bytes().into())
        .send()
        .await
}

async fn parse_graph(nodes: &NodesJson, edges: &EdgesJson) -> Result<Graph, anyhow::Error> {
    let mut graph_nodes: HashMap<NodeId, Node> = HashMap::new();
    let mut graph_edges: HashMap<EdgeId, Edge> = HashMap::new();

    let mut to_nodes_by_node: HashMap<NodeId, Vec<NodeId>> = HashMap::new();

    let all_nodes: &Vec<String> = nodes.get("Nodes").unwrap();
    let all_edges: &HashMap<String, String> = edges.get("Edges").unwrap();

    let all_nodes: Vec<NodeId> = all_nodes
        .iter()
        .map(|s| s.parse::<NodeId>().unwrap())
        .collect();

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

    for node_id in &all_nodes {
        let empty_vec: Vec<NodeId> = Vec::new();
        let next_nodes: &Vec<NodeId> = match to_nodes_by_node.get(node_id) {
            Some(v) => v,
            None => &empty_vec,
        };
        let node = Node {
            id: *node_id,
            next_nodes: next_nodes.clone(),
        };
        graph_nodes.insert(*node_id as NodeId, node);
    }

    let graph = Graph {
        nodes: graph_nodes,
        edges: graph_edges,
    };

    return Ok(graph);
}

async fn dijkstra(
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

/// This is the main body for the function.
/// Write your code inside it.
/// There are some code example in the following URLs:
/// - https://github.com/awslabs/aws-lambda-rust-runtime/tree/main/examples
/// - https://github.com/aws-samples/serverless-rust-demo/
async fn function_handler(event: LambdaEvent<Request>) -> Result<Response, Error> {
    let region_provider = RegionProviderChain::default_provider().or_else("us-east-1");
    let config = aws_config::from_env().region(region_provider).load().await;
    let client: Client = Client::new(&config);

    let bucket = match env::var("GRAPHS_BUCKET") {
        Ok(b) => b,
        Err(_) => {
            eprintln!("Failed to read 'GRAPHS_BUCKET' env var");
            exit(1);
        }
    };

    let solution_bucket = match env::var("PATHS_BUCKET") {
        Ok(b) => b,
        Err(_) => {
            eprintln!("Failed to read 'PATHS_BUCKET' env var");
            exit(1);
        }
    };

    let key = &event.payload.key;
    let source: NodeId = event.payload.source;
    let destination: NodeId = event.payload.destination;

    let (nodes, edges) = match get_graph(&client, &bucket, key).await {
        Ok(graph_json) => graph_json,
        Err(err) => {
            eprintln!("Error {}", err);
            exit(1);
        }
    };

    let graph: Graph = match parse_graph(&nodes, &edges).await {
        Ok(g) => g,
        Err(err) => {
            eprintln!("Error {}", err);
            exit(1);
        }
    };

    let graph_result = dijkstra(&graph, source, destination).await;
    let (path, weight, iterations) = match graph_result {
        Some(x) => x,
        None => {
            eprintln!("Failed to find a path");
            exit(1);
        }
    };

    let current_time = chrono::Utc::now().format("%Y-%m-%dT%H:%M:%S").to_string();
    let unique_id = Uuid::new_v4().hyphenated().to_string();
    let file_key = format!("{}_{}.json", current_time, unique_id);

    let resp = upload_path(&client, &solution_bucket, &file_key, &path).await;

    assert!(resp.is_ok(), "{resp:?}");

    let resp = Response {
        iterations,
        weight,
        solution_key: file_key,
        source: source,
        destination: destination,
        graph_id: key
    };

    Ok(resp)
}

#[tokio::main]
async fn main() -> Result<(), Error> {
    tracing::init_default_subscriber();

    run(service_fn(function_handler)).await
}
