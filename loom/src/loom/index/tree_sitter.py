"""Tree-sitter based code chunker."""
import tree_sitter_languages
from tree_sitter import Language, Parser
from pathlib import Path
from typing import List, Dict

LANGUAGE_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "tsx",
    ".jsx": "javascript", ".go": "go", ".rs": "rust", ".c": "c",
    ".cpp": "cpp", ".java": "java", ".rb": "ruby",
}

class Indexer:
    def __init__(self, ignore_patterns: List[str]):
        self.ignore_patterns = ignore_patterns
        self.parsers = {}

    def _get_parser(self, lang_name: str) -> Parser:
        if lang_name not in self.parsers:
            try:
                language = Language(tree_sitter_languages.language(lang_name))
                parser = Parser(language)
                self.parsers[lang_name] = parser
            except Exception:
                return None
        return self.parsers.get(lang_name)

    def index_repo(self, root: Path) -> List[Dict]:
        chunks = []
        for file_path in root.rglob("*"):
            if any(file_path.match(pattern) for pattern in self.ignore_patterns):
                continue
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            lang = LANGUAGE_MAP.get(ext)
            if not lang:
                continue
            parser = self._get_parser(lang)
            if not parser:
                continue
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code = f.read()
            except Exception:
                continue
            tree = parser.parse(bytes(code, "utf-8"))
            defs = self._extract_definitions(tree.root_node, code)
            for defn in defs:
                chunks.append({
                    "file": str(file_path.relative_to(root)),
                    "language": lang,
                    "code": defn["code"],
                    "start_line": defn["start_line"],
                    "end_line": defn["end_line"],
                    "name": defn.get("name", ""),
                })
        return chunks

    def _extract_definitions(self, node, code: str) -> List[Dict]:
        chunks = []
        for child in node.children:
            if child.type in ["function_definition", "class_definition", "method_definition"]:
                name_node = child.child_by_field_name("name")
                name = code[name_node.start_byte:name_node.end_byte] if name_node else ""
                start_line = child.start_point[0] + 1
                end_line = child.end_point[0] + 1
                code_snippet = "\n".join(code.splitlines()[start_line-1:end_line])
                chunks.append({"name": name, "code": code_snippet, "start_line": start_line, "end_line": end_line})
            else:
                chunks.extend(self._extract_definitions(child, code))
        return chunks
