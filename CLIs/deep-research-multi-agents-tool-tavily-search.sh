#!/bin/bash
# Run deep-research-multi-agents-tool-tavily-search in Docker

# Check if --output is provided
if [[ ! "$*" =~ "--output" ]]; then
    echo "Usage: $0 --output <output_dir> [--tasks <tasks_dir>]"
    exit 1
fi

docker compose run --rm deep-research-multi-agents-tool-tavily-search "$@"
