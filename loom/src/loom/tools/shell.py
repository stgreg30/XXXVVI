"""Safe subprocess call utility."""
import subprocess
from pathlib import Path

def run_command(cmd: list, cwd: Path) -> tuple[int, str]:
    try:
        result = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=60)
        return result.returncode, result.stdout + result.stderr
    except Exception as e:
        return 1, str(e)
