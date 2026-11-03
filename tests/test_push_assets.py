"""The uploaded scorer must register without a participant's local environment."""

import os
import subprocess
import sys
import tempfile
import unittest


class ScorerDeploymentTest(unittest.TestCase):
    def test_hosted_import_without_project_or_dotenv(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("BRAINTRUST_")}
        script = """
import sys
sys.modules['dotenv'] = None
from braintrust.framework import _set_lazy_load
from braintrust.framework2 import global_
with _set_lazy_load(True):
    from super_stonks.evals import push_assets

assert len(global_.functions) == 1
scorer = global_.functions[0]
assert scorer.slug == 'tool_call_succeeded'
assert scorer.handler(output={'ticker': 'BRK-B', 'verdict': 'HOLD'})['score'] == 1
assert scorer.handler(output={'error': 'No data found'})['score'] == 0
assert scorer.handler(output=None)['score'] is None
"""
        with tempfile.TemporaryDirectory() as cwd:
            result = subprocess.run(
                [sys.executable, "-c", script], cwd=cwd, env=env,
                capture_output=True, text=True,
            )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
