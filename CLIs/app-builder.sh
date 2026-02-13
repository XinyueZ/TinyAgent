#!/bin/bash
# Run app-builder in Docker
#
# Usage (from anywhere on the host):
#   /path/to/CLIs/app-builder.sh --main /path/to/main-file.py
#
# --main is resolved relative to the caller's working directory,
# its parent directory is mounted into the container, and rewritten
# so the Python app can access it.
#
# If Docker is not available (e.g. already inside a container), falls back to
# running the Python entry-point directly.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── Fallback: no Docker → run directly (e.g. already inside a container) ──
if ! command -v docker &>/dev/null; then
    echo "[INFO] Docker not found. Running directly via Python."
    exec python "${REPO_ROOT}/apps/app-builder/app-builder.py" "$@"
fi

# Ensure Google Cloud Application Default Credentials (ADC) are valid
ADC_FILE="${HOME}/.config/gcloud/application_default_credentials.json"
if [[ ! -f "${ADC_FILE}" ]] || ! gcloud auth application-default print-access-token &>/dev/null; then
    echo "[INFO] ADC credentials missing or expired."
    echo "[INFO] Running: gcloud auth application-default login"
    gcloud auth application-default login
fi

# ── Parse --main from the arguments ──
HOST_MAIN=""
OTHER_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --main)
            HOST_MAIN="$2"; shift 2 ;;
        *)
            OTHER_ARGS+=("$1"); shift ;;
    esac
done

if [[ -z "${HOST_MAIN}" ]]; then
    echo "Usage: $0 --main <path_to_main_file>"
    exit 1
fi

# ── Resolve to absolute paths (relative to caller's cwd) ──
# If relative, resolve against the caller's working directory
[[ "${HOST_MAIN}" != /* ]] && HOST_MAIN="${PWD}/${HOST_MAIN}"

if [[ ! -f "${HOST_MAIN}" ]]; then
    echo "[ERROR] Main file does not exist: ${HOST_MAIN}"
    exit 1
fi

HOST_MAIN_DIR="$(cd "$(dirname "${HOST_MAIN}")" && pwd)"
HOST_MAIN_NAME="$(basename "${HOST_MAIN}")"

# Mount the parent directory of the main file
VOLUME_ARGS=(-v "${HOST_MAIN_DIR}:/host_main_dir:ro")
CONTAINER_ARGS=(--main "/host_main_dir/${HOST_MAIN_NAME}")

# ── Run ──
CMD=(
    docker compose
    -f "${REPO_ROOT}/docker-compose.yml"
    --project-directory "${REPO_ROOT}"
    run --rm
    "${VOLUME_ARGS[@]}"
    app-builder
    "${CONTAINER_ARGS[@]}"
)
if [[ ${#OTHER_ARGS[@]} -gt 0 ]]; then
    CMD+=("${OTHER_ARGS[@]}")
fi
"${CMD[@]}"
