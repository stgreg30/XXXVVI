"""Loads loom.toml configuration."""
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

DEFAULT_CONFIG_NAME = "loom.toml"

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

class ModelsConfig(BaseModel):
    default: str = "models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"
    embedding: str = "sentence-transformers/all-MiniLM-L6-v2"

class AgentConfig(BaseModel):
    max_retries: int = 2
    context_chunks: int = 5
    chunk_size_lines: int = 40

class RepoConfig(BaseModel):
    ignore_patterns: list[str] = [".git", "__pycache__", "node_modules", "*.pyc", "venv"]

class LoomConfig(BaseModel):
    models: ModelsConfig = ModelsConfig()
    agent: AgentConfig = AgentConfig()
    repo: RepoConfig = RepoConfig()

def find_config_dir(start: Path) -> Optional[Path]:
    current = start.resolve()
    while current != current.parent:
        candidate = current / DEFAULT_CONFIG_NAME
        if candidate.exists():
            return current
        current = current.parent
    return None

def load_config(config_dir: Optional[Path] = None) -> LoomConfig:
    if config_dir is None:
        config_dir = find_config_dir(Path.cwd())
    if config_dir is None:
        raise FileNotFoundError(f"No {DEFAULT_CONFIG_NAME} found. Run `loom init` first.")
    config_path = config_dir / DEFAULT_CONFIG_NAME
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    return LoomConfig(**data)
