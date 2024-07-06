import json
import requests
import time

from typing import List, Dict, Optional

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"


def get_lat_lon(city: str, country: str) -> Optional[Dict[str, str]]:
    """
    Fetches latitude and longitude for a city using Nominatim API.

    Args:
        city: The name of the city.
        country: The country of the city.

    Returns:
        A dictionary containing latitude (lat) and longitude (lon) if successful,
        None otherwise.
    """
    params = {"city": city, "country": country, "format": "json"}
    headers = {"User-Agent": "GraphMapsApplication/1.0"}

    response = requests.get(NOMINATIM_URL, params=params, headers=headers)

    if response.status_code == 200:
        data: Optional[List[Dict[str, str]]] = response.json()
        if data:
            return {"lat": data[0]["lat"], "lon": data[0]["lon"]}
        else:
            print(f"No results found for {city}, {country}")
    else:
        print(f"Error retrieving data for {city}, {country}: {response.status_code}")
    return None


def main() -> None:
    with open("cities.json", "r") as f:
        cities_data: List[Dict[str, str]] = json.load(f)

    cities_with_lat_lon: List[Dict[str, str]] = []
    for city in cities_data:
        if "lat" not in city or "lon" not in city:
            lat_lon = get_lat_lon(city["city"], city["country"])
            if lat_lon:
                city.update(lat_lon)
            time.sleep(2)
        cities_with_lat_lon.append(city)

    with open("cities.json", "w") as f:
        json.dump(cities_with_lat_lon, f, indent=2)


if __name__ == "__main__":
    main()
