import io
import shutil
import tarfile
import tempfile
from pathlib import Path

import docker

from tiny_agent.tools.decorator import tool


@tool()
def run_python_file(file_path: str, output_path: str) -> dict[str, str]:
    """Run a Python file inside a sandboxed Docker container.

    Args:
        file_path:
            Absolute path to the `.py` file to execute on the host.
        output_path:
            Host directory where all execution outputs (charts, CSVs, etc.)
            will be written. The directory is created if it does not exist.

    Container layout:
        /work/code/   ← directory containing file_path (uploaded via tar)
        /work/output/ ← execution cwd; results downloaded back to output_path

    Execution:
        cd /work/output && python -B /work/code/<filename>

    Notes:
        - Code and outputs are transferred via Docker put_archive / get_archive
          (no bind mounts required).
        - Each execution runs in a short-lived container; pip installs do NOT
          persist, but a persistent pip cache volume is available at /work/pip-cache.
        - After execution, files written to /work/output inside the container
          are synced back to output_path on the host.

    Returns:
        dict with keys:
            target_file   – resolved absolute path of file_path
            output_path   – the output_path argument
            execute_result – stdout/stderr on success, or error description
    """

    if not isinstance(file_path, str) or not file_path.strip():
        raise ValueError("file_path must be a non-empty string")
    if not isinstance(output_path, str) or not output_path.strip():
        raise ValueError("output_path must be a non-empty string")

    target = Path(file_path).resolve()
    output_dir_host = Path(output_path).resolve()
    output_dir_host.mkdir(parents=True, exist_ok=True)
    code_dir_host = target.parent

    if not target.exists() or not target.is_file():
        raise FileNotFoundError(f"Python file not found: {target}")

    filename = target.name

    def _result(execute_result: str) -> dict[str, str]:
        return {
            "target_file": str(target),
            "output_path": str(output_dir_host),
            "execute_result": execute_result,
        }

    # ── docker availability ───────────────────────────────────────────
    if not Path("/var/run/docker.sock").exists():
        return _result(
            "DockerUnavailable: /var/run/docker.sock not found. "
            "Mount the host docker socket into the container."
        )

    # ── container paths ───────────────────────────────────────────────
    ctr_code = "/work/code"
    ctr_output = "/work/output"
    ctr_target = f"{ctr_code}/{filename}"

    run_script = "set -e; " f'cd {ctr_output} && python -B "{ctr_target}"'
    command = ["sh", "-lc", run_script]

    # ── run container (put_archive / exec / get_archive) ──────────────
    # NOTE: put_archive writes through the Docker daemon into the container's
    # overlay filesystem.  It CANNOT write into tmpfs mounts (the daemon
    # doesn't see them).  Therefore /work must live on the regular container
    # filesystem, not on a tmpfs.
    try:
        client = docker.DockerClient(base_url="unix:///var/run/docker.sock")
        container = None
        try:
            container = client.containers.run(
                image="python:3.13-slim",
                command=["sh", "-lc", "sleep 3600"],
                detach=True,
                remove=False,
                network_mode="bridge",
                read_only=False,
                working_dir="/work",
                tmpfs={"/tmp": "rw,noexec,nosuid,nodev,size=256m"},
                mem_limit="1g",
                nano_cpus=int(2.0 * 1_000_000_000),
                pids_limit=50,
                security_opt=["no-new-privileges:true"],
                environment={
                    "HOME": "/work",
                    "PIP_CACHE_DIR": "/work/pip-cache",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONUSERBASE": "/work/.local",
                    "PATH": "/usr/local/bin:/usr/bin:/bin:/work/.local/bin",
                },
            )

            # create dirs as root, then hand ownership to unprivileged user
            rc, _ = container.exec_run(
                cmd=[
                    "sh",
                    "-c",
                    f"mkdir -p {ctr_code} {ctr_output} /work/pip-cache "
                    "&& chown -R 1000:1000 /work",
                ],
                user="0",
                demux=False,
            )
            if int(rc) != 0:
                return _result("ExecutionError: mkdir failed inside container")

            # upload code directory
            tar_buf = io.BytesIO()
            with tarfile.open(fileobj=tar_buf, mode="w") as tf:
                tf.add(str(code_dir_host), arcname="code")
            tar_buf.seek(0)
            container.put_archive("/work", tar_buf.read())

            # execute as unprivileged user
            rc, out = container.exec_run(
                cmd=command,
                user="1000:1000",
                demux=False,
            )
            rc = int(rc)
            logs = (out or b"").decode("utf-8", errors="replace")

            if rc != 0:
                return _result(f"ExitCode: {rc}\n{logs}".strip())

            # download output
            try:
                stream, _ = container.get_archive(ctr_output)
                out_tar = io.BytesIO(b"".join(stream))
                out_tar.seek(0)
                with tempfile.TemporaryDirectory() as td:
                    with tarfile.open(fileobj=out_tar, mode="r:*") as tf:
                        tf.extractall(path=td)
                    extracted = Path(td) / "output"
                    if extracted.exists():
                        shutil.copytree(
                            str(extracted),
                            str(output_dir_host),
                            dirs_exist_ok=True,
                        )
            except Exception:
                pass

            return _result(logs)
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
    except Exception as e:
        return _result(f"ExecutionError: {e}")
