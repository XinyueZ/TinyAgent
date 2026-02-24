#!/bin/bash
# Run coding-agent in Docker
#
# Usage (from anywhere on the host):
#   /app/CLIs/coding-agent.sh --output <output_dir> --tasks <tasks_dir> [--deps <deps_file>] [--coding-tools <tools_file>]
#
# Arguments are resolved relative to the caller's working directory,
# mounted into the container, and rewritten so the Python app can access them.
#
# If Docker is not available (e.g. already inside a container), falls back to
# running the Python entry-point directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Fallback: no Docker → run directly (e.g. already inside a container) ──
if ! command -v docker &>/dev/null; then
    echo "[INFO] Docker not found. Running directly via Python."
    exec python "${REPO_ROOT}/apps/coding-agent/coding-agent.py" "$@"
fi

# Ensure Google Cloud Application Default Credentials (ADC) are valid
ADC_FILE="${HOME}/.config/gcloud/application_default_credentials.json"
if [[ ! -f "${ADC_FILE}" ]] || ! gcloud auth application-default print-access-token &>/dev/null; then
    echo "[INFO] ADC credentials missing or expired."
    echo "[INFO] Running: gcloud auth application-default login"
    gcloud auth application-default login
fi

# ── Parse arguments ──
HOST_OUTPUT=""
HOST_TASKS=""
HOST_DEPS=""
HOST_TOOLS=""
OTHER_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output)
            HOST_OUTPUT="$2"; shift 2 ;;
        --tasks)
            HOST_TASKS="$2"; shift 2 ;;
        --deps)
            HOST_DEPS="$2"; shift 2 ;;
        --coding-tools)
            HOST_TOOLS="$2"; shift 2 ;;
        *)
            OTHER_ARGS+=("$1"); shift ;;
    esac
done

if [[ -z "${HOST_OUTPUT}" || -z "${HOST_TASKS}" ]]; then
    echo "Usage: $0 --output <output_dir> --tasks <tasks_dir> [--deps <deps_file>] [--coding-tools <tools_file>]"
    exit 1
fi

# ── Resolve paths and prepare volume mounts ──
VOLUME_ARGS=()
CONTAINER_ARGS=()

# Resolve --output (Directory)
[[ "${HOST_OUTPUT}" != /* ]] && HOST_OUTPUT="${PWD}/${HOST_OUTPUT}"
mkdir -p "${HOST_OUTPUT}"
HOST_OUTPUT="$(cd "${HOST_OUTPUT}" && pwd)"
VOLUME_ARGS+=(-v "${HOST_OUTPUT}:/host_output")
CONTAINER_ARGS+=(--output /host_output)

# Resolve --tasks (Directory)
[[ "${HOST_TASKS}" != /* ]] && HOST_TASKS="${PWD}/${HOST_TASKS}"
if [[ ! -d "${HOST_TASKS}" ]]; then
    echo "[ERROR] Tasks directory does not exist: ${HOST_TASKS}"
    exit 1
fi
HOST_TASKS="$(cd "${HOST_TASKS}" && pwd)"
VOLUME_ARGS+=(-v "${HOST_TASKS}:/host_tasks:ro")
CONTAINER_ARGS+=(--tasks /host_tasks)

# Resolve --deps (File)
if [[ -n "${HOST_DEPS}" ]]; then
    [[ "${HOST_DEPS}" != /* ]] && HOST_DEPS="${PWD}/${HOST_DEPS}"
    if [[ ! -f "${HOST_DEPS}" ]]; then
        echo "[ERROR] Deps file does not exist: ${HOST_DEPS}"
        exit 1
    fi
    HOST_DEPS_DIR="$(cd "$(dirname "${HOST_DEPS}")" && pwd)"
    HOST_DEPS_NAME="$(basename "${HOST_DEPS}")"
    VOLUME_ARGS+=(-v "${HOST_DEPS_DIR}:/host_deps:ro")
    CONTAINER_ARGS+=(--deps "/host_deps/${HOST_DEPS_NAME}")
fi

# Resolve --coding-tools (File)
if [[ -n "${HOST_TOOLS}" ]]; then
    [[ "${HOST_TOOLS}" != /* ]] && HOST_TOOLS="${PWD}/${HOST_TOOLS}"
    if [[ ! -f "${HOST_TOOLS}" ]]; then
        echo "[ERROR] Coding tools file does not exist: ${HOST_TOOLS}"
        exit 1
    fi
    HOST_TOOLS_DIR="$(cd "$(dirname "${HOST_TOOLS}")" && pwd)"
    HOST_TOOLS_NAME="$(basename "${HOST_TOOLS}")"
    VOLUME_ARGS+=(-v "${HOST_TOOLS_DIR}:/host_tools:ro")
    CONTAINER_ARGS+=(--coding-tools "/host_tools/${HOST_TOOLS_NAME}")
fi

# ── Run ──
CMD=(
    docker compose
    -f "${REPO_ROOT}/docker-compose.yml"
    --project-directory "${REPO_ROOT}"
    run --rm
    "${VOLUME_ARGS[@]}"
    coding-agent
    "${CONTAINER_ARGS[@]}"
)
if [[ ${#OTHER_ARGS[@]} -gt 0 ]]; then
    CMD+=("${OTHER_ARGS[@]}")
fi
"${CMD[@]}"
