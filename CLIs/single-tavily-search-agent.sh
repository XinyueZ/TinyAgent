#!/bin/bash
# Run single-tavily-search-agent in Docker
#
# Usage (from anywhere on the host):
#   /path/to/CLIs/single-tavily-search-agent.sh --output ./my-output [--tasks ./my-tasks]
#
# --output and --tasks are resolved relative to the caller's working directory,
# mounted into the container, and rewritten so the Python app writes to the right place.
#
# If Docker is not available (e.g. already inside a container), falls back to
# running the Python entry-point directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Fallback: no Docker → run directly (e.g. already inside a container) ──
if ! command -v docker &>/dev/null; then
    echo "[INFO] Docker not found. Running directly via Python."
    exec python "${REPO_ROOT}/apps/single-tavily-search-agent/agent.py" "$@"
fi

# Ensure Google Cloud Application Default Credentials (ADC) are valid
if [[ ! " $@ " =~ " --no-vertexai " ]]; then
    ADC_FILE="${HOME}/.config/gcloud/application_default_credentials.json"
    if [[ ! -f "${ADC_FILE}" ]] || ! gcloud auth application-default print-access-token &>/dev/null; then
        echo "[INFO] ADC credentials missing or expired."
        echo "[INFO] Running: gcloud auth application-default login"
        gcloud auth application-default login
    fi
fi

# ── Parse --output and --tasks from the arguments ──
HOST_OUTPUT=""
HOST_TASKS=""
OTHER_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            HOST_OUTPUT="$2"; shift 2 ;;
        --tasks)
            HOST_TASKS="$2"; shift 2 ;;
        *)
            OTHER_ARGS+=("$1"); shift ;;
    esac
done

if [[ -z "${HOST_OUTPUT}" || -z "${HOST_TASKS}" ]]; then
    echo "Usage: $0 --output <output_dir> --tasks <tasks_dir>"
    exit 1
fi

# ── Resolve to absolute paths (relative to caller's cwd) ──
# If relative, resolve against the caller's working directory
[[ "${HOST_OUTPUT}" != /* ]] && HOST_OUTPUT="${PWD}/${HOST_OUTPUT}"
mkdir -p "${HOST_OUTPUT}"
HOST_OUTPUT="$(cd "${HOST_OUTPUT}" && pwd)"

VOLUME_ARGS=(-v "${HOST_OUTPUT}:/host_output")
CONTAINER_ARGS=(--output /host_output)

if [[ -n "${HOST_TASKS}" ]]; then
    [[ "${HOST_TASKS}" != /* ]] && HOST_TASKS="${PWD}/${HOST_TASKS}"
    if [[ ! -d "${HOST_TASKS}" ]]; then
        echo "[ERROR] Tasks directory does not exist: ${HOST_TASKS}"
        exit 1
    fi
    HOST_TASKS="$(cd "${HOST_TASKS}" && pwd)"
    VOLUME_ARGS+=(-v "${HOST_TASKS}:/host_tasks:ro")
    CONTAINER_ARGS+=(--tasks /host_tasks)
fi

# ── Run ──
CMD=(
    docker compose
    -f "${REPO_ROOT}/docker-compose.yml"
    --project-directory "${REPO_ROOT}"
    run --rm
    "${VOLUME_ARGS[@]}"
    single-tavily-search-agent
    "${CONTAINER_ARGS[@]}"
)
if [[ ${#OTHER_ARGS[@]} -gt 0 ]]; then
    CMD+=("${OTHER_ARGS[@]}")
fi
"${CMD[@]}"
