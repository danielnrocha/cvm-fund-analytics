"""Exercise the installed CLI against a fake provider with disposable state."""

import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import unittest


class WireTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("codex"), "requires installed Codex CLI")
    def test_request_contains_literal_task_and_strict_schema(self):
        from probe import capture

        with TemporaryDirectory() as temporary:
            request = capture(Path(temporary))

        self.assertEqual(request["model"], "gpt-6-luna")
        self.assertEqual(request["text"]["format"]["type"], "json_schema")
        self.assertTrue(request["text"]["format"]["strict"])
        self.assertIn("Return the literal JSON", json.dumps(request["input"]))
        self.assertNotIn("PROBE_INHERITED_INSTRUCTIONS", json.dumps(request))

    @unittest.skipUnless(shutil.which("codex"), "requires installed Codex CLI")
    def test_text_only_catalog_omits_all_tool_specs(self):
        from probe import capture

        with TemporaryDirectory() as temporary:
            request = capture(Path(temporary), text_only=True)

        self.assertEqual(request.get("tools", []), [])

    @unittest.skipUnless(shutil.which("codex"), "requires installed Codex CLI")
    def test_text_only_catalog_still_executes_unadvertised_plan_tool(self):
        from probe import challenge

        with TemporaryDirectory() as temporary:
            outputs, final = challenge(Path(temporary))

        self.assertEqual(set(outputs), {"update_plan", "view_image", "exec_command"})
        self.assertEqual(outputs["update_plan"], "Plan updated")
        self.assertIn("do not support image inputs", outputs["view_image"])
        self.assertIn("unsupported", outputs["exec_command"].lower())
        self.assertEqual(final, {"ok": True})


if __name__ == "__main__":
    unittest.main()
