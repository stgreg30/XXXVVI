"""Auto-detect and run project tests."""
import subprocess, logging
from pathlib import Path

logger = logging.getLogger(__name__)

class TestRunner:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.last_return_code = 0

    def run(self) -> str:
        candidates = [
            (["pytest", "-x", "--tb=short"], ["pytest.ini", "pyproject.toml", "setup.cfg"]),
            (["npm", "test", "--", "--verbose"], ["package.json"]),
            (["make", "test"], ["Makefile"]),
            (["cargo", "test"], ["Cargo.toml"]),
        ]
        for cmd, indicators in candidates:
            if any((self.repo_path / f).exists() for f in indicators):
                try:
                    result = subprocess.run(cmd, cwd=str(self.repo_path), capture_output=True, text=True, timeout=120)
                    self.last_return_code = result.returncode
                    return result.stdout + "\n" + result.stderr
                except FileNotFoundError:
                    continue
                except subprocess.TimeoutExpired:
                    self.last_return_code = 1
                    return "Test timed out."
        self.last_return_code = 0
        return "No test command detected."
