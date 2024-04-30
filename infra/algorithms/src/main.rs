extern crate queues;

mod graph;
mod utils;
mod dijkstra;
mod bfs;

use graph::{NodeId, Graph};
use utils::{get_graph, upload_path, parse_graph};
use dijkstra::dijkstra;
use bfs::bfs;

use std::env;
use std::process::exit;
use uuid::Uuid;

use aws_config::meta::region::RegionProviderChain;
use aws_sdk_s3::Client;
use lambda_runtime::{run, service_fn, tracing, Error, LambdaEvent};

use serde::{Deserialize, Serialize};

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

async fn function_handler(event: LambdaEvent<Request>) -> Result<Response, Error> {
  let region_provider = RegionProviderChain::default_provider().or_else("us-east-1");
  let config = aws_config::from_env().region(region_provider).load().await;
  let client: Client = Client::new(&config);

  let bucket: String = match env::var("GRAPHS_BUCKET") {
    Ok(b) => b,
    Err(_) => {
      eprintln!("Failed to read 'GRAPHS_BUCKET' env var");
      exit(1);
    }
  };

  let solution_bucket: String = match env::var("PATHS_BUCKET") {
    Ok(b) => b,
    Err(_) => {
      eprintln!("Failed to read 'PATHS_BUCKET' env var");
      exit(1);
    }
  };

  let key: &String = &event.payload.key;
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

  let current_time: String = chrono::Utc::now().format("%Y-%m-%dT%H:%M:%S").to_string();
  let unique_id: String = Uuid::new_v4().hyphenated().to_string();
  let file_key: String = format!("{}_{}.json", current_time, unique_id);

  let resp = upload_path(&client, &solution_bucket, &file_key, &path).await;

  assert!(resp.is_ok(), "{resp:?}");

  let resp: Response = Response {
    iterations,
    weight,
    solution_key: file_key,
    source: source,
    destination: destination,
    graph_id: event.payload.key
  };

  Ok(resp)
}

#[tokio::main]
async fn main() -> Result<(), Error> {
  tracing::init_default_subscriber();

  run(service_fn(function_handler)).await
}
