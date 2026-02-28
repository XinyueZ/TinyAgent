import warnings

from tiny_agent.utils.print_utils import format_text

warnings.filterwarnings("ignore")

from google.genai import types
import os

_APP_BUILDER_MODEL = "gemini-3-flash-preview"
_APP_BUILDER_MODEL_CONFIG = {
    "temperature": 1.0,
    "seed": 42,
    "top_p": 1.0,
    "top_k": 60,
    "thinking_config": types.ThinkingConfig(
        thinking_level=types.ThinkingLevel.HIGH,
        include_thoughts=False,
    ),
}

_PROVIDER_CONFIG = {
    "vertexai": os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", "True") == "True",
    "vertexai_location": os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west4"),
    "vertexai_project": os.environ.get(
        "GOOGLE_CLOUD_PROJECT", "hg-hjghjg-ai-ft-exp-pr-hjjkhljhlhjkl"
    ),
    "google_ai_studio_api_key": os.environ.get(
        "GOOGLE_AI_STUDIO_API_KEY", "adfasdfasdfads"
    ),
}

if __name__ == "__main__":
    print("App Builder")
    import argparse
    from tiny_agent.agent.tiny_agent import TinyAgent

    this_file_absolute_path = os.path.abspath(__file__)
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument(
        "--main",
        type=str,
        required=True,
        help="The the file where the main is. One app only one main. Recommended to use absolute path ‼️",
    )
    args = parser.parse_args()
    task = f"""
You are a CLI shell-script builder. Your goal is to create a new `.sh` file under the `CLIs/` directory for the application whose main entry-point is given below.

## Inputs

- **main path**: `{args.main}`
- **this file absolute path**: `{this_file_absolute_path}`

## How to locate the `CLIs` directory

The `CLIs` directory is a **sibling** of the `apps` directory. Derive its absolute path from **this file absolute path** by finding the `apps` component and replacing it with `CLIs`.
For example, if this file absolute path is `/aaa/bbb/apps/app-builder/app-builder.py`, then the `CLIs` absolute path is `/aaa/bbb/CLIs`.

## Steps

1. **Read reference sh files** — Use `list_dir` on the `CLIs` absolute path derived above, then read every `.sh` file found there. Understand their common structure: shebang, ADC check, argument parsing (`while` / `case`), path resolution, volume mounts, `docker compose run` invocation, etc.

2. **Read the main-path file** — Read the file at `{args.main}`. Look for an `argparse` section (`ArgumentParser`, `add_argument` calls).
   - **If `argparse` is found**, extract each argument:
     - argument name (e.g. `--output`, `--tasks`, `--main_path`, …)
     - whether it is `required`
     - its `type` and `help` text
     - whether the argument semantically represents a **directory path**, a **file path**, or a **plain value** (infer from the name, help text, and how it is used in the code).
   - **If no `argparse` / `ArgumentParser` / `add_argument` is found**, the app takes no CLI arguments. The generated `.sh` script should have no argument parsing, no volume mounts for user-provided paths, and simply invoke the Python entry-point directly via `docker compose run`.

3. **Determine the sh file name** — The new sh file must be named after the **parent directory** of the main-path file. For example if main path is `apps/foo-bar/main.py`, the sh file is `<CLIs absolute path>/foo-bar.sh`.

4. **Determine the docker-compose service name** — The service name used in the `docker compose run` command equals the sh file name (without `.sh`), i.e. the parent-directory name of the main-path file.

5. **Generate the sh script** — Produce a bash script that mirrors the structure of the reference sh files **but adapts the argument handling** to match the argparse of the main-path file:
   - For each argparse argument that represents a **directory path**: parse it from CLI, resolve it to an absolute path, `mkdir -p` if it is an output dir, mount it as a Docker volume (`-v host:container`), and rewrite the container arg to the mount point.
   - For each argparse argument that represents a **file path**: parse it from CLI, resolve it to an absolute path, mount the **parent directory** as a Docker volume, and rewrite the container arg accordingly.
   - For each argparse argument that is a **plain value** (not a path): simply forward it as-is to the container command.
   - Mark arguments as required or optional consistent with the argparse definition. If all required arguments are not provided, print a usage message and exit.
   - Keep the ADC credential check, `set -euo pipefail`, `SCRIPT_DIR` / `REPO_ROOT` resolution, and `OTHER_ARGS` pass-through exactly as in the reference scripts.

6. **Write the sh file** — Use `write_file` to save the generated script to `<CLIs absolute path>/<parent-dir-name>.sh`. The file must be a valid bash script ready to execute.

7. **Verify** — Use `file_exists` to confirm the file was written, then use `read_file` to re-read it and verify correctness.

main path: {args.main}

"""
    format_text(task, "⚑ App Builder (single agent)")
    # create the agent and run
    agent = TinyAgent(
        name="app_builder",
        model=_APP_BUILDER_MODEL,
        output_root="./.build",
        genai_stuff={**_APP_BUILDER_MODEL_CONFIG, **_PROVIDER_CONFIG},
    )

    agent(contents=task)
