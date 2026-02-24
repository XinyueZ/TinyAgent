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
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"

update_docker_compose_service() {
    local host_main="$1"
    local service_name="$2"
    local entrypoint_rel="$3"
    local sandbox_sock="${4:-false}"
    local compose_file="${COMPOSE_FILE}"

    if [[ ! -f "${compose_file}" ]]; then
        echo "[WARN] docker-compose.yml not found at ${compose_file}; skip updating."
        return 0
    fi

    if [[ "${entrypoint_rel}" != apps/* ]]; then
        echo "[ERROR] Entrypoint must be repo-relative and start with apps/: ${entrypoint_rel}"
        return 1
    fi

    local tmp_file block_file
    tmp_file="$(mktemp)"
    block_file="$(mktemp)"

    local sock_block=""
    if [[ "${sandbox_sock}" == "true" ]]; then
        sock_block="      # run_python_file() needs the Docker daemon to spin up sandboxed
      # containers for code execution (see tiny_agent/tools/coding/run_code.py).
      - /var/run/docker.sock:/var/run/docker.sock
"
    fi

    cat > "${block_file}" <<EOF
  ${service_name}:
    build:
      context: .
      dockerfile: Dockerfile
    image: tiny-agent-io:latest
    volumes:
      - .:/app
${sock_block}      - \${HOME}/.config/gcloud/application_default_credentials.json:/root/.config/gcloud/application_default_credentials.json:ro
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json
    env_file:
      - ./apps/.env
    working_dir: /app
    entrypoint: ["python", "${entrypoint_rel}"]

EOF

    # Replace if service exists; otherwise insert before app-builder service (preferred), else append at end.
    awk -v service_name="${service_name}" -v block_file="${block_file}" '
        function print_block() {
            while ((getline line < block_file) > 0) {
                print line
            }
            close(block_file)
        }
        BEGIN { in_target=0; replaced=0; inserted=0 }
        {
            if (in_target == 1) {
                # Stop skipping when a new top-level service key begins (two spaces + non-space)
                if ($0 ~ /^  [^ #][^:]*:/) {
                    in_target=0
                } else {
                    next
                }
            }

            if (in_target == 0 && $0 ~ ("^  " service_name ":")) {
                print_block()
                replaced=1
                in_target=1
                next
            }

            if (inserted == 0 && $0 ~ /^  # App Builder$/) {
                print_block()
                inserted=1
            }
            if (inserted == 0 && $0 ~ /^  app-builder:$/) {
                print_block()
                inserted=1
            }

            print $0
        }
        END {
            if (replaced == 0 && inserted == 0) {
                print_block()
            }
        }
    ' "${compose_file}" > "${tmp_file}"

    mv "${tmp_file}" "${compose_file}"
    rm -f "${block_file}"
    echo "[INFO] Updated docker-compose.yml with service: ${service_name} (entrypoint: ${entrypoint_rel})"
}

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
SANDBOX_SOCK="false"
OTHER_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --main)
            HOST_MAIN="$2"; shift 2 ;;
        --sandbox-sock)
            SANDBOX_SOCK="true"; shift ;;
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

SERVICE_NAME="$(basename "${HOST_MAIN_DIR}")"
ENTRYPOINT_REL="$(REPO_ROOT="${REPO_ROOT}" HOST_MAIN="${HOST_MAIN}" python - <<'PY'
import os
repo_root = os.environ["REPO_ROOT"]
host_main = os.environ["HOST_MAIN"]
print(os.path.relpath(host_main, repo_root))
PY
)"

# Mount the parent directory of the main file
CONTAINER_MAIN_DIR="/host_main/${SERVICE_NAME}"
VOLUME_ARGS=(-v "${HOST_MAIN_DIR}:${CONTAINER_MAIN_DIR}:ro")
CONTAINER_ARGS=(--main "${CONTAINER_MAIN_DIR}/${HOST_MAIN_NAME}")

# ── Run ──
CMD=(
    docker compose
    -f "${COMPOSE_FILE}"
    --project-directory "${REPO_ROOT}"
    run --rm
    "${VOLUME_ARGS[@]}"
    app-builder
    "${CONTAINER_ARGS[@]}"
)
if [[ ${#OTHER_ARGS[@]} -gt 0 ]]; then
    CMD+=("${OTHER_ARGS[@]}")
fi
set +e
"${CMD[@]}"
RUN_STATUS=$?
set -e

update_docker_compose_service "${HOST_MAIN}" "${SERVICE_NAME}" "${ENTRYPOINT_REL}" "${SANDBOX_SOCK}"

docker compose \
    -f "${COMPOSE_FILE}" \
    --project-directory "${REPO_ROOT}" \
    up -d

exit ${RUN_STATUS}
