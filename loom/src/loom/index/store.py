"""LanceDB + SQLite storage for repo index and task history."""
import json, sqlite3, logging
from pathlib import Path
from typing import List, Dict, Optional
import lancedb, pyarrow as pa

from ..config import LoomConfig

logger = logging.getLogger(__name__)

CHUNK_SCHEMA = pa.schema([
    pa.field("vector", pa.list_(pa.float32(), 384)),
    pa.field("file", pa.string()),
    pa.field("language", pa.string()),
    pa.field("code", pa.string()),
    pa.field("name", pa.string()),
    pa.field("start_line", pa.int32()),
    pa.field("end_line", pa.int32()),
])

class IndexStore:
    def __init__(self, repo_path: Path, config: LoomConfig):
        self.repo_path = repo_path
        self.config = config
        self.db_dir = repo_path / ".loom"
        self.db_dir.mkdir(exist_ok=True)
        self.sqlite_path = self.db_dir / "loom.db"
        self.conn = sqlite3.connect(str(self.sqlite_path))
        self._init_sqlite()
        self.ldb = lancedb.connect(str(self.db_dir / "lancedb"))
        self._init_lancedb()
        try:
            from sentence_transformers import SentenceTransformer
            self.embed_model = SentenceTransformer(config.models.embedding)
        except ImportError:
            raise ImportError("Install embeddings: pip install loom-agent[embeddings]")

    def _init_sqlite(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, task TEXT, plan TEXT, diff TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
        self.conn.commit()

    def _init_lancedb(self):
        if "chunks" not in self.ldb.table_names():
            self.ldb.create_table("chunks", schema=CHUNK_SCHEMA)

    def add_chunks(self, chunks: List[Dict]):
        if not chunks: return
        texts = [c["code"] for c in chunks]
        try:
            embeddings = self.embed_model.encode(texts, show_progress_bar=False)
        except Exception as e:
            logger.error(f"Embedding failed: {e}")
            return
        for i, chunk in enumerate(chunks):
            chunk["vector"] = embeddings[i].tolist()
        self.ldb.open_table("chunks").add(chunks)

    def search_chunks(self, query: str, limit: int = 5) -> List[Dict]:
        try:
            q_embed = self.embed_model.encode([query])[0].tolist()
        except Exception as e:
            logger.error(f"Query embedding failed: {e}")
            return []
        return self.ldb.open_table("chunks").search(q_embed).limit(limit).to_list()

    def get_summary(self) -> str:
        try:
            tbl = self.ldb.open_table("chunks")
            df = tbl.to_pandas()
        except Exception:
            return "No indexed data."
        if df.empty:
            return "Empty repository."
        files = sorted(set(df["file"].tolist()))
        return "Repository files:\n" + "\n".join(files)

    def save_plan(self, task: str, plan: list):
        self.conn.execute("INSERT INTO tasks (task, plan) VALUES (?, ?)", (task, json.dumps(plan)))
        self.conn.commit()

    def save_diff(self, diff: str):
        self.conn.execute("UPDATE tasks SET diff = ? WHERE id = (SELECT MAX(id) FROM tasks)", (diff,))
        self.conn.commit()

    def get_last_diff(self) -> Optional[str]:
        row = self.conn.execute("SELECT diff FROM tasks ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else None
