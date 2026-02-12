# TinyAgent

A personal hobby project for building various agentic applications. Designed with a **keep-it-simple** philosophy — currently only supports:

- [Google GenAI SDK](https://github.com/googleapis/python-genai) (including Vertex AI)
- [Ollama](https://github.com/ollama/ollama)

Whether it will be expanded in the future? We'll see. No promises.

---

## Table of Contents

- [Environment Setup](#environment-setup)
- [Apps](#apps)
- [Troubleshooting: Google GenAI Credentials](#troubleshooting-google-genai-credentials)
- [Star History](#star-history)
- [License](#license)

---

## Environment Setup

Copy `apps/env_sample` to `apps/.env` and fill in your values:

```bash
cp apps/env_sample apps/.env
```

This configures **Vertex AI / Google GenAI** (`GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_VERTEXAI`, `GOOGLE_AI_STUDIO_API_KEY`) and **Tavily** API keys.

- `TAVILY_API_KEY_0` is **required** at minimum.
- You can register multiple Tavily API keys — number them starting from `0` (e.g. `TAVILY_API_KEY_0`, `TAVILY_API_KEY_1`, `TAVILY_API_KEY_2`, ...).

---

### 🚀 Build and local deploy

```bash
docker compose build
docker compose up -d
```

### Enter container

```bash
docker exec -it TinyAgentDev /bin/bash
```

### 📋 Logging

```bash
docker logs -f TinyAgentDev
```

---

## Apps

| App | Description | 🐳 Inside Container | 💻 Local Computer (CLI) |
|-----|-------------|-----------------|-----------------|
| `apps/single-tavily-search-agent` | Single agent with Tavily web search | `cd apps/single-tavily-search-agent`<br>`python ./agent.py --output ./agent-output` | `CLIs/single-tavily-search-agent.sh`<br>`--output ./my-output --tasks ./my-tasks` |
| `apps/deep-research-multi-agents-tool-tavily-search` | Deep research via tool calls that spawn multiple TinyAgents concurrently with Tavily search | `cd apps/deep-research-multi-agents-tool-tavily-search`<br>`python ./deep-research.py --output ./deep-research-output --tasks ./my-tasks` | `CLIs/deep-research-multi-agents-tool-tavily-search.sh`<br>`--output ./my-output --tasks ./my-tasks` |

- `--output` (required): Output directory for results.
- `--tasks`: Directory containing task files (`.md`). **Required** when running from host via CLI. Optional inside container (defaults to `./tasks/` in the app folder).
- **Inside container**: Enter with `docker exec -it TinyAgentDev /bin/bash` first.
- **From host**: CLI scripts handle Google Cloud ADC authentication and resolve `--output`/`--tasks` paths relative to your current directory automatically.

### Example: Using `--tasks` with Custom Task Files

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
# Inside container
python ./agent.py --output ./my-output --tasks /path/to/labubuVShellokitty

# From host
CLIs/single-tavily-search-agent.sh --output ./my-output --tasks ./labubuVShellokitty
```

---

## Troubleshooting: Google GenAI Credentials

This section applies when using **Google GenAI / Vertex AI** (not Ollama).

If you encounter `DefaultCredentialsError` or any credential-related error during execution:

- **Inside container**: Run the following command inside the container to authenticate:
  ```bash
  gcloud auth application-default login
  ```
  Follow the prompts to complete the authentication flow.

- **From host (via `CLIs/*.sh`)**: The CLI scripts will automatically detect missing or expired credentials and trigger `gcloud auth application-default login`. This will open a **web browser login dialog** — complete the authentication in the browser, then the script will continue automatically.

---

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=XinyueZ/TinyAgent&type=Date)](https://star-history.com/#XinyueZ/TinyAgent&Date)

---

## License

This project is licensed under the [MIT License](LICENSE).