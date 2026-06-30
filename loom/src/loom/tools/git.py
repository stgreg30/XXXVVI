"""Git operations for diffing, patching, and committing."""
import tempfile, logging
from pathlib import Path
import git

logger = logging.getLogger(__name__)

class GitManager:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        try:
            self.repo = git.Repo(str(repo_path))
        except git.InvalidGitRepositoryError:
            self.repo = git.Repo.init(str(repo_path))

    def apply_patch(self, patch_content: str):
        if not patch_content.strip():
            return
        tf = tempfile.NamedTemporaryFile(delete=False, suffix=".patch")
        tf.write(patch_content.encode())
        tf.close()
        try:
            self.repo.git.apply(tf.name)
        except git.GitCommandError as e:
            logger.warning(f"Patch apply warning: {e}")

    def unified_diff(self) -> str:
        try:
            return self.repo.git.diff(unified=3)
        except git.GitCommandError:
            return ""

    def commit_changes(self, message: str):
        try:
            self.repo.git.add(A=True)
            self.repo.index.commit(message)
        except git.GitCommandError as e:
            logger.error(f"Commit failed: {e}")

    def revert_last_commit(self):
        try:
            self.repo.git.revert("HEAD", no_edit=True)
        except git.GitCommandError as e:
            logger.error(f"Revert failed: {e}")

    def hard_reset(self):
        try:
            self.repo.head.reset(index=True, working_tree=True)
        except git.GitCommandError as e:
            logger.error(f"Hard reset failed: {e}")
