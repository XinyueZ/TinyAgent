# TinyAgent

A personal hobby project for building various agentic applications. Designed with a **keep-it-simple** philosophy — currently supports Google GenAI, Vertex AI, and Ollama only.

Whether it will be expanded in the future? We'll see. No promises.

---

## Environment Setup

Create a `.env` file under the `apps/` directory (or set the environment variables listed in `apps/env_sample` by other means). See `apps/env_sample` for the full list of required variables.

- `TAVILY_API_KEY_0` is **required** at minimum.
- You can register multiple Tavily API keys — just number them starting from `0` (e.g. `TAVILY_API_KEY_0`, `TAVILY_API_KEY_1`, `TAVILY_API_KEY_2`, ...).

---

### Build and local deploy

```bash
docker compose build
docker compose up -d
```

### Enter container

```bash
docker exec -it TinyAgentDev /bin/bash
```

### Logging

```bash
docker logs -f TinyAgentDev
```

---

## Run Apps (inside container)

Enter the container first, then navigate to the corresponding app directory to run.

### Single Tavily Search Agent

```bash
cd apps/single-tavily-search-agent
python ./agent.py --output ./agent-output
```

- `--output` (required): Output directory for results
- `--tasks` (optional): Directory containing task files (`.md`). Defaults to `./tasks/` in the app folder.

#### Example: Using `--tasks` with Custom Task Files

You can organize research tasks in separate `.md` files. Each file contains prompts that guide the agent's research focus.

**Example directory structure:**
```
labubuVShellokitty/
├── labubu.md
├── hellokitty.md
└── compare.md
```

**Example task file (`labubu.md`):**
```markdown
What is Labubu?
- Provide an introduction to Labubu and its creator (Pop Mart)
- Analyze the current market performance and collector demand
- Discuss the future outlook and growth potential of the brand
```

**Example task file (`hellokitty.md`):**
```markdown
What is Hello Kitty?
- Provide a brief introduction to Hello Kitty and its origins
- Summarize the history and evolution of the Hello Kitty brand
- Analyze the current market presence and commercial performance
- Discuss the future outlook and potential growth of the brand
```

**Example task file (`compare.md`):**
```markdown
Compare Labubu and Hello Kitty from multiple perspectives:
- Market positioning and global reach
- Branding strategies and visual identity
- Popularity and cultural impact among young consumers
```

**Run with custom tasks:**
```bash
python ./agent.py --output ./my-output --tasks /path/to/labubuVShellokitty
```

### Deep Research Multi-Agents Tool (Tavily Search)

```bash
cd apps/deep-research-multi-agents-tool-tavily-search
python ./deep-research.py --output ./deep-research-output
```

- `--output` (required): Output directory for results
- `--tasks` (optional): Directory containing task files (`.md`). Defaults to `./tasks/` in the app folder.

---

## Run from Host (outside container)

You can also run the apps directly from your host machine using the CLI scripts in `CLIs/`. These scripts handle Google Cloud ADC authentication, resolve `--output`/`--tasks` paths relative to your current directory, and run the app inside Docker automatically.

### Single Tavily Search Agent

```bash
/path/to/CLIs/single-tavily-search-agent.sh --output ./my-output [--tasks ./my-tasks]
```

### Deep Research Multi-Agents Tool (Tavily Search)

```bash
/path/to/CLIs/deep-research-multi-agents-tool-tavily-search.sh --output ./my-output [--tasks ./my-tasks]
```

---

## Troubleshooting: Google Cloud Credentials

If you encounter `DefaultCredentialsError` or any credential-related error during execution:

- **Inside container**: Run the following command inside the container to authenticate:
  ```bash
  gcloud auth application-default login
  ```
  Follow the prompts to complete the authentication flow.

- **From host (via `CLIs/*.sh`)**: The CLI scripts will automatically detect missing or expired credentials and guide you through `gcloud auth application-default login` before running the app.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=XinyueZ/TinyAgent&type=Date)](https://star-history.com/#XinyueZ/TinyAgent&Date)

---

## License

This project is licensed under the [MIT License](LICENSE).