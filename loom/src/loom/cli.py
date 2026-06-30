"""Loom CLI – offline-first coding agent."""
from pathlib import Path
import sys

import click
import tomli_w

from .config import LoomConfig, load_config
from .models.download import download_model, download_embedding_model
from .index.store import IndexStore
from .index.tree_sitter import Indexer
from .agent.loop import AgentLoop

DEFAULT_MODEL_URL = (
    "https://huggingface.co/bartowski/Qwen2.5-Coder-1.5B-Instruct-GGUF/resolve/main/"
    "Qwen2.5-Coder-1.5B-Instruct-Q4_K_M.gguf"
)
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

@click.group()
def cli():
    """Loom – offline AI coding agent for low-bandwidth devs."""
    pass

@cli.command()
@click.option("--model", default=None, help="Path or URL to a GGUF model file")
@click.option("--embedding", default=None, help="Hugging Face embedding model name or path")
@click.option("--force", is_flag=True, help="Re-download models even if they exist")
def init(model, embedding, force):
    """Initialize Loom in the current directory."""
    cwd = Path.cwd()
    config_path = cwd / "loom.toml"

    if config_path.exists() and not force:
        click.echo("loom.toml already exists. Use --force to re-initialize.")
        return

    models_dir = cwd / "models"
    models_dir.mkdir(exist_ok=True)

    model_path = model or str(models_dir / "qwen2.5-coder-1.5b-instruct-q4_k_m.gguf")
    if not Path(model_path).exists() or force:
        click.echo("Downloading default reasoning model... (~1.2 GB)")
        download_model(DEFAULT_MODEL_URL, model_path)
        click.echo(f"Model saved to {model_path}")
    else:
        click.echo(f"Using existing model at {model_path}")

    embedding_path = embedding or EMBEDDING_MODEL_NAME
    click.echo("Downloading embedding model (if not cached)... (~90 MB)")
    try:
        download_embedding_model(embedding_path, str(models_dir))
    except ImportError:
        click.echo("Error: sentence-transformers not installed. Run: pip install loom-agent[embeddings]")
        sys.exit(1)
    click.echo(f"Embedding model ready: {embedding_path}")

    config_dict = {
        "models": {"default": model_path, "embedding": embedding_path},
        "agent": {"max_retries": 2, "context_chunks": 5, "chunk_size_lines": 40},
        "repo": {"ignore_patterns": [".git", "__pycache__", "node_modules", "*.pyc", "venv"]}
    }
    with open(config_path, "wb") as f:
        tomli_w.dump(config_dict, f)
    click.echo("Configuration written to loom.toml")

    config = load_config(config_dir=cwd)
    click.echo("Indexing repository...")
    store = IndexStore(cwd, config)
    indexer = Indexer(config.repo.ignore_patterns)
    chunks = indexer.index_repo(cwd)
    store.add_chunks(chunks)
    click.echo(f"Indexed {len(chunks)} code chunks.")
    click.echo("Loom initialized successfully. You are now offline-ready!")

@cli.command()
@click.argument("task", type=str)
def plan(task):
    config = load_config()
    store = IndexStore(Path.cwd(), config)
    agent = AgentLoop(config, store)
    click.echo(agent.create_plan(task))

@cli.command()
@click.argument("task", type=str)
@click.option("--auto-apply", is_flag=True, help="Apply changes without confirmation (dangerous)")
@click.option("--dry-run", is_flag=True, help="Show diff without applying changes")
def run(task, auto_apply, dry_run):
    config = load_config()
    store = IndexStore(Path.cwd(), config)
    agent = AgentLoop(config, store, dry_run=dry_run)
    click.echo(f"Planning: {task}")
    plan = agent.create_plan(task)
    click.echo(plan)
    click.echo("\nExecuting plan...")
    diff = agent.execute_plan(task, plan)
    click.echo("\n" + "="*40)
    click.echo("Proposed changes (unified diff):")
    click.echo(diff)
    if dry_run:
        click.echo("Dry run complete. No changes applied.")
        return
    if not auto_apply:
        if not click.confirm("Apply these changes?", default=False):
            click.echo("Changes discarded.")
            return
    agent.apply_changes()
    click.echo("Changes applied. Review with `loom review` or undo with `loom undo`.")

@cli.command()
def review():
    config = load_config()
    store = IndexStore(Path.cwd(), config)
    last_diff = store.get_last_diff()
    click.echo(last_diff if last_diff else "No previous diff found.")

@cli.command()
@click.option("--hard", is_flag=True, help="Discard all uncommitted changes (git reset --hard)")
def undo(hard):
    config = load_config()
    store = IndexStore(Path.cwd(), config)
    agent = AgentLoop(config, store)
    if hard:
        agent.hard_reset()
        click.echo("Hard reset performed.")
    else:
        agent.undo_last()
        click.echo("Last change undone.")
