#!/bin/bash

# Path to cities.json
CITIES_JSON_PATH="../cities.json"

# Iterate over cities in the JSON file
jq -c '.[]' "$CITIES_JSON_PATH" | while read -r city; do
  # Extract the city name
  city_name=$(echo "$city" | jq -r '.name')

  # Run the Python script for each city
  python prepare.py "$city_name"
done
