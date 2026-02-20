import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import docker


@dataclass(frozen=True)
class SandboxLimits:
    cpus: float = 2.0
    memory: str = "1g"
    pids_limit: int = 50
    timeout_seconds: int = 120


class SandboxError(RuntimeError):
    pass


class DockerSandboxRunner:
    """Run untrusted code in a short-lived, resource-limited Docker container.

    This runner is intended to be called by a trusted orchestrator (your code agent).
    Do NOT expose raw Docker access to the LLM.
    """

    def __init__(
        self,
        *,
        allowed_host_roots: Sequence[str] = ("/app/sandbox",),
        docker_base_url: str | None = "unix:///var/run/docker.sock",
    ):
        self._allowed_host_roots = tuple(str(Path(p).resolve()) for p in allowed_host_roots)
        self._client = docker.DockerClient(base_url=docker_base_url) if docker_base_url else docker.from_env()

    def _ensure_allowed(self, host_path: str) -> str:
        resolved = str(Path(host_path).resolve())
        if not any(resolved == r or resolved.startswith(r + os.sep) for r in self._allowed_host_roots):
            raise SandboxError(
                f"Host path not allowed for sandbox mount: {resolved}. "
                f"Allowed roots: {self._allowed_host_roots}"
            )
        return resolved

    def run(
        self,
        *,
        image: str,
        command: Sequence[str],
        input_dir: str,
        output_dir: str,
        env: Mapping[str, str] | None = None,
        limits: SandboxLimits = SandboxLimits(),
        network_mode: str = "bridge",
        read_only_rootfs: bool = True,
        user: str = "1000:1000",
        workdir: str = "/work",
        tmpfs: Mapping[str, str] | None = None,
    ) -> tuple[int, str]:
        """Run a container and return (exit_code, logs).

        Mounts:
        - input_dir: mounted read-only at /work/input
        - output_dir: mounted read-write at /work/output

        Defaults are intentionally restrictive. You can widen them explicitly.
        """

        if not command:
            raise SandboxError("command must be non-empty")

        host_input = self._ensure_allowed(input_dir)
        host_output = self._ensure_allowed(output_dir)

        Path(host_output).mkdir(parents=True, exist_ok=True)

        volumes = {
            host_input: {"bind": f"{workdir}/input", "mode": "ro"},
            host_output: {"bind": f"{workdir}/output", "mode": "rw"},
        }

        tmpfs = dict(tmpfs or {})
        tmpfs.setdefault("/tmp", "rw,noexec,nosuid,nodev,size=256m")

        container = None
        start = time.time()
        try:
            container = self._client.containers.run(
                image=image,
                command=list(command),
                detach=True,
                remove=False,
                network_mode=network_mode,
                volumes=volumes,
                working_dir=workdir,
                environment=dict(env or {}),
                read_only=read_only_rootfs,
                tmpfs=tmpfs,
                user=user,
                mem_limit=limits.memory,
                nano_cpus=int(limits.cpus * 1_000_000_000),
                pids_limit=limits.pids_limit,
                security_opt=["no-new-privileges:true"],
            )

            try:
                result = container.wait(timeout=limits.timeout_seconds)
                exit_code = int(result.get("StatusCode", 1))
            except Exception:
                # Timeout or API error while waiting
                container.kill()
                raise SandboxError(
                    f"Sandbox container timed out after {limits.timeout_seconds}s (elapsed={int(time.time()-start)}s)"
                )

            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
            return exit_code, logs
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
