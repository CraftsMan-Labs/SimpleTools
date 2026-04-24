from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from simpletools.fuzzy_patch import fuzzy_find_and_replace
from simpletools.registry import list_tools
from simpletools.runner import ToolRunner


class SmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp()
        self.cwd = Path(self.tmp) / "w"
        self.cwd.mkdir()
        self.data = Path(self.tmp) / "d"
        self.r = ToolRunner(cwd=self.cwd, data_dir=self.data)

    def test_registry_size(self) -> None:
        names = {t["name"] for t in list_tools()}
        self.assertIn("web_search", names)
        self.assertIn("session_index", names)
        self.assertNotIn("image_generate", names)

    def test_memory_todo_cron(self) -> None:
        m = self.r.call("memory", action="add", target="memory", content="project uses uv")
        self.assertTrue(m.get("ok"), m)
        rd = self.r.call("memory", action="read")
        self.assertIn("project uses uv", str(rd.get("memory", [])))
        self.assertTrue(
            self.r.call(
                "todo",
                todos=[{"id": "1", "content": "step a", "status": "pending"}],
                merge=False,
            )["ok"]
        )
        j = self.r.call(
            "cronjob",
            action="create",
            spec="0 * * * *",
            payload={"kind": "python", "code": "print(1)"},
        )
        self.assertTrue(j["ok"], j)

    def test_file_ops_and_fuzzy_patch(self) -> None:
        self.assertTrue(
            self.r.call("write_file", path="a.txt", content="def foo():\n    return 1\n")["ok"]
        )
        rf = self.r.call("read_file", path="a.txt", offset=1, limit=10)
        self.assertTrue(rf["ok"])
        self.assertIn("1|def foo", rf["content"])
        pr = self.r.call(
            "patch",
            mode="replace",
            path="a.txt",
            old_string="return 1",
            new_string="return 2",
            replace_all=False,
        )
        self.assertTrue(pr.get("ok"), pr)
        text = (self.cwd / "a.txt").read_text()
        self.assertIn("return 2", text)

    def test_fuzzy_chain_handles_whitespace(self) -> None:
        src = "def foo():\n    pass\n"
        new, n, err = fuzzy_find_and_replace(src, "def foo():", "def bar():", replace_all=False)
        self.assertIsNone(err)
        self.assertEqual(n, 1)
        self.assertIn("def bar", new)

    def test_delegate_requires_handler(self) -> None:
        out = self.r.call("delegate_task", tasks=["a"])
        self.assertFalse(out["ok"])


if __name__ == "__main__":
    unittest.main()
