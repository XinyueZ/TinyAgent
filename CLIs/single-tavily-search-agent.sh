#!/bin/bash
# Run single-tavily-search-agent in Docker

# Check if --output is provided
if [[ ! "$*" =~ "--output" ]]; then
    echo "Usage: $0 --output <output_dir> [--tasks <tasks_dir>]"
    exit 1
fi

docker compose run --rm single-tavily-search-agent "$@"
