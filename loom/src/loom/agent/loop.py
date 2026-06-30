"""Core planning and execution loop."""
import json, logging, re
from ..config import LoomConfig
from ..index.store import IndexStore
from ..models.llama_cpp import LlamaCppModel
from ..tools.git import GitManager
from ..tools.test import TestRunner

logger = logging.getLogger(__name__)

PLAN_SYSTEM_PROMPT = """You are a coding assistant that only outputs valid JSON.
Given a user task and a summary of the repository, produce a step-by-step plan as a JSON list.
Each step must be an object with "action" and "description".
Example:
[
  {"action": "modify file.py", "description": "Add JWT auth to login endpoint"},
  {"action": "install package", "description": "pip install PyJWT"}
]
Do not output anything else."""

EDIT_SYSTEM_PROMPT = """You are a precise code editor. Given a code context and a step description, output a unified diff patch that implements the change.
Use the standard unified diff format starting with --- and +++.
Only include the necessary lines. Do not rewrite unrelated code."""

REFLECT_SYSTEM_PROMPT = """You are a code reviewer. The following test output indicates a failure after a code change. Diagnose the issue and output a unified diff patch to fix it.
Output only the diff."""

class AgentLoop:
    def __init__(self, config: LoomConfig, store: IndexStore, dry_run: bool = False):
        self.config = config
        self.store = store
        self.model = LlamaCppModel(config.models.default)
        self.git = GitManager(store.repo_path)
        self.test_runner = TestRunner(store.repo_path)
        self._last_diff = ""
        self.dry_run = dry_run

    def create_plan(self, task: str) -> str:
        repo_summary = self.store.get_summary()
        prompt = f"Repository summary:\n{repo_summary}\n\nTask: {task}\n\nPlan:"
        response = self.model.generate(PLAN_SYSTEM_PROMPT, prompt, max_tokens=1024, temperature=0.2)
        plan = self._extract_json(response)
        self.store.save_plan(task, plan)
        return json.dumps(plan, indent=2)

    def execute_plan(self, task: str, plan_json: str) -> str:
        plan = json.loads(plan_json) if isinstance(plan_json, str) else plan_json
        all_diffs = []
        for step in plan:
            description = step.get("description", str(step))
            logger.info(f"Executing step: {description}")
            chunks = self.store.search_chunks(description, limit=self.config.agent.context_chunks)
            context = "\n\n".join([f"```{c['language']}\n{c['code']}\n```" for c in chunks])
            edit_prompt = f"Task step: {description}\n\nRelevant code:\n{context}\n\nGenerate a unified diff patch:"
            try:
                diff = self.model.generate(EDIT_SYSTEM_PROMPT, edit_prompt, max_tokens=2048, temperature=0.1)
            except Exception as e:
                logger.error(f"Model generation failed: {e}")
                diff = ""
            if not diff.strip():
                logger.warning("Empty diff generated, skipping step.")
                continue
            if not self.dry_run:
                self.git.apply_patch(diff)
            test_success = True
            if not self.dry_run:
                test_output = self.test_runner.run()
                test_success = self.test_runner.last_return_code == 0
                retries = 0
                while not test_success and retries < self.config.agent.max_retries:
                    reflect_prompt = f"Step failed. Test output:\n{test_output}\nCurrent diff:\n{diff}\nFix the issue:"
                    try:
                        fix_diff = self.model.generate(REFLECT_SYSTEM_PROMPT, reflect_prompt, max_tokens=2048, temperature=0.2)
                    except Exception as e:
                        logger.error(f"Reflect generation failed: {e}")
                        break
                    self.git.apply_patch(fix_diff)
                    test_output = self.test_runner.run()
                    test_success = self.test_runner.last_return_code == 0
                    diff += "\n" + fix_diff
                    retries += 1
                if not test_success:
                    logger.warning("Tests still failing after retries.")
            all_diffs.append(diff)
        final_diff = "\n".join(all_diffs) if all_diffs else ""
        self._last_diff = final_diff
        self.store.save_diff(final_diff)
        return final_diff

    def apply_changes(self):
        if not self.dry_run:
            self.git.commit_changes("Loom: applied changes")

    def undo_last(self):
        self.git.revert_last_commit()

    def hard_reset(self):
        self.git.hard_reset()

    def _extract_json(self, text: str):
        cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', text.strip(), flags=re.MULTILINE)
        match = re.search(r'\[.*\]', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return [{"action": "", "description": line} for line in lines]
