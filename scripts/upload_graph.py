import boto3
import json
import requests
import os
import time
import sys

from pathlib import Path

from typing import List, Dict, Tuple, Optional

sys.path.append((Path.cwd() / ".." / "infra/lib/sfn").absolute().as_posix())

from modules.graph import Graph # type: ignore
from lambdas.getGraph.lambda_function import download_graph, store_graph, generate_graph # type: ignore

GRAPHS_TABLE_NAME = os.environ["GRAPHS_TABLE_NAME"]
GRAPHS_BUCKET_NAME = os.environ["GRAPHS_BUCKET"]

dynamodb = boto3.resource("dynamodb")
graphs_table = dynamodb.Table(GRAPHS_TABLE_NAME)
s3 = boto3.resource("s3")
graphs_bucket = s3.Bucket(GRAPHS_BUCKET_NAME)


NOMINATIM_URL = f"https://nominatim.openstreetmap.org/reverse?format=json"
HEADERS = {"User-Agent": "GraphMapsApplication/1.0"}

def get_place(lat: str, lon: str) -> Tuple[Optional[str], Optional[str]]:
  url = f"{NOMINATIM_URL}&lat={lat}&lon={lon}"
  response = requests.get(url, headers=HEADERS)
  data: Dict = response.json()
  if "address" not in data:
    print("Not possible to get the address")
    return (None, None)
  address: Dict = data["address"]
  city = address.get("city", None)
  country = address.get("country", None)
  return (city, country)

def main():
  with open("cities.json", "r") as f:
    cities_data: List[Dict[str, str]] = json.load(f)

  for city_data in cities_data:
    if city_data.get("uploaded", False):
      continue
    city, country = get_place(city_data["lat"], city_data["lon"])
    print(f"Uploading {city}, {country}")
    if city is None or country is None:
      continue
    G, graph_id = download_graph(country=country, city=city)
    graph: Graph = generate_graph(G)
    store_graph(graph, graph_id)
    graphs_table.put_item(Item={
      "Country": country,
      "City": city,
      "GraphId": graph_id
    })


if __name__ == "__main__":
  main()