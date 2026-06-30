# Loom – Offline-First AI Coding Agent

**Loom** is a fully local, open-source AI agent that plans, edits, and tests code without any internet connection. Built for developers in low-bandwidth, high-cost, or air-gapped environments.

> *“Not another chatbot wrapper – a true plan-edit-test loop that runs on a beat-up laptop with no internet.”*

---

## Why Loom?

- **Offline by design**: No API keys, no cloud. Works with quantized open models that run on CPU.
- **Low data cost**: A single ~1.2 GB model download gives you unlimited usage. Share via USB stick.
- **Safe & explainable**: Always shows a diff before applying changes. Human-in-the-loop by default.
- **Open & permissive**: Apache 2.0 code, Apache 2.0 default model (Qwen2.5-Coder-1.5B-Instruct).

---

## Installation

### Quick install (with all features)
```bash
pip install loom-agent[full]
```

Minimal install (only CLI, without AI models)
```bash
pip install loom-agent
```

Then, when ready, install the model backends:
```bash
pip install loom-agent[llama,embeddings]
```

Note for llama-cpp-python
The llama extra requires a C++ compiler and cmake. If you encounter build issues, use pre-built wheels:

```bash
pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
```

For air-gapped installations, download the wheels and transfer them. See Offline Setup.

---

## Quick Start

```bash
# 1. Initialize in your project folder (downloads model + indexes code)
loom init

# 2. Plan a task
loom plan "Add pagination to the /users endpoint"

# 3. Execute the plan (review diff before applying)
loom run "Add pagination to the /users endpoint"

# 4. Undo if needed
loom undo
```

---

## How It Works

1. Index: Tree-sitter extracts function/class definitions; embeddings stored in LanceDB.
2. Plan: A reasoning model (Qwen2.5-Coder-1.5B) generates a step-by-step plan.
3. Execute: For each step, Loom retrieves relevant code, generates a diff patch, runs tests, and reflects on failures.
4. Confirm: You see the full diff and approve before any changes are committed.

---

## Model & License

· Default model: Qwen2.5-Coder-1.5B-Instruct – Apache 2.0
· Backend: llama.cpp (any GGUF model supported)
· Embeddings: sentence-transformers/all-MiniLM-L6-v2 (MIT)

You can swap models by editing loom.toml.

---

## Requirements

· Python 3.10+
· 8 GB RAM (runs entirely on CPU)
· Internet only for initial model download (optional USB transfer)

---

## Offline Setup

1. On an internet-connected machine, run loom init to download models.
2. Copy the entire project folder (with .loom/ and models/) to an offline machine.
3. Run loom init --model ./models/my-model.gguf --embedding ./models/all-MiniLM-L6-v2 to skip downloads.

---

## Community & Roadmap

· v1: CLI, single-model planning + editing, offline core.
· v2: Local web UI, plugin marketplace, multi-model pipeline.
· Future: SaaS layer (separate repo) for team collaboration.

Contributions welcome! Check CONTRIBUTING.md.

---

Built for the Next Billion Developers

Loom isn't just a tool – it's a statement that great AI coding assistants should be accessible to everyone, regardless of internet cost or connectivity.

"Code where you are, with what you have."
