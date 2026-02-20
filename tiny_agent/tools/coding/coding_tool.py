
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

import docker

from tiny_agent.tools.decorator import tool, get_tool_context
from tiny_agent.utils.docker_sandbox import DockerSandboxRunner, SandboxError, SandboxLimits


@tool()
def run_python_code(code_str: str) -> Any:
    """
    Run Python code in a sandboxed environment.
    
    Args:
        code_str: The Python code to execute
        
    Returns:
        The result of the code execution
    """
    if not isinstance(code_str, str) or not code_str.strip():
        raise ValueError("code_str must be a non-empty string")

    ctx = get_tool_context() or {}
    agent_info = ctx.get("agent_info") or {}
    agent_id = agent_info.get("agent_id", "unknown")
    agent_name = agent_info.get("agent_name", "unknown")

    run_root = f"{agent_name}-{agent_id}"
    run_id = f"{int(time.time() * 1000000)}-{str(uuid4())}"
    base_dir = Path("/app/sandbox") / "run_python_code" / run_root / run_id
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    main_file = input_dir / "main.py"
    main_file.write_text(code_str, encoding="utf-8")

    docker_sock = Path("/var/run/docker.sock")
    if not docker_sock.exists():
        return (
            "DockerUnavailable: /var/run/docker.sock not found. "
            "Run this tool inside the TinyAgentDev container (with docker.sock mounted), "
            "or mount the host docker socket into the container."
        )

    try:
        runner = DockerSandboxRunner(allowed_host_roots=("/app/sandbox",))
        exit_code, logs = runner.run(
            image="python:3.13-slim",
            command=["python", "/work/input/main.py"],
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            limits=SandboxLimits(cpus=2.0, memory="1g", pids_limit=50, timeout_seconds=120),
            network_mode="bridge",
            read_only_rootfs=True,
            user="1000:1000",
        )
    except SandboxError as e:
        return f"SandboxError: {str(e)}"
    except Exception as e:
        msg = str(e)
        if "mounts denied" in msg:
            try:
                client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
                container = None
                try:
                    container = client.containers.run(
                        image="python:3.13-slim",
                        command=["python", "-c", code_str],
                        detach=True,
                        remove=False,
                        network_mode="bridge",
                        read_only=True,
                        tmpfs={"/tmp": "rw,noexec,nosuid,nodev,size=256m"},
                        user="1000:1000",
                        mem_limit="1g",
                        nano_cpus=int(2.0 * 1_000_000_000),
                        pids_limit=50,
                        security_opt=["no-new-privileges:true"],
                    )
                    result = container.wait(timeout=120)
                    exit_code = int(result.get("StatusCode", 1))
                    logs = container.logs(stdout=True, stderr=True).decode(
                        "utf-8", errors="replace"
                    )
                finally:
                    if container is not None:
                        try:
                            container.remove(force=True)
                        except Exception:
                            pass
            except Exception as inner:
                return f"ExecutionError: {str(inner)}"

            if exit_code != 0:
                return f"ExitCode: {exit_code}\n{logs}".strip()
            return logs.strip()
        return f"ExecutionError: {str(e)}"

    if exit_code != 0:
        return f"ExitCode: {exit_code}\n{logs}".strip()
    return logs.strip()

