"""生成の確認。同梱の定義をすべて一時フォルダに書き出し、同期とリンクの検査が通ることを確かめる。

    python -m unittest discover tools
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import generate  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOMAINS = sorted(p.parent for p in (ROOT / "domains").glob("*/domain.toml"))


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, encoding="utf-8")


class GenerateTest(unittest.TestCase):
    def test_bundled_domains(self):
        self.assertGreaterEqual(len(DOMAINS), 3)
        for domain in DOMAINS:
            with self.subTest(domain=domain.name), tempfile.TemporaryDirectory() as tmp:
                r = run(ROOT / "tools" / "generate.py", domain, "--out", tmp)
                self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
                out = pathlib.Path(tmp)
                d = generate.load(domain)
                name, prefix = d["domain"]["name"], d["domain"]["prefix"]
                # 置き換え忘れがない
                for path in out.rglob("*"):
                    if path.is_file() and path.suffix in (".md", ".py"):
                        self.assertNotIn("{{", path.read_text(encoding="utf-8"), path)
                # 両方のツール用の入口と、全員分のエージェントがある
                self.assertTrue((out / ".github/skills" / name / "SKILL.md").exists())
                self.assertTrue((out / ".claude/skills" / name / "SKILL.md").exists())
                agents = {"orchestrator", "reconciler", "improver"}
                agents |= {k for k in ("librarian", "auditor") if d["support"][k]}
                for role in d["roles"]:
                    agents |= {role["name"]} | ({role["reviewer"]} if role["reviewer"] else set())
                self.assertEqual({p.name[:-9] for p in (out / ".github/agents").glob("*.agent.md")}, agents)
                self.assertEqual({p.stem for p in (out / ".claude/agents").glob("*.md")}, agents)
                # 担当のスキルは Claude Code 用の入口を作らない (パスで読む)
                self.assertFalse((out / ".claude/skills" / f"{prefix}-base").exists())
                # 書き出した先で、同期が最新で、参照先に抜けがない
                self.assertEqual(run(out / "tools/sync_agents.py", "--check").returncode, 0)
                links = run(out / "tools/check_links.py")
                self.assertEqual(links.returncode, 0, links.stdout)
                # 常に読まれるファイルは短い
                self.assertLessEqual(len((out / "AGENTS.md").read_text(encoding="utf-8").splitlines()), 14)

    def test_keeps_existing_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            domain = ROOT / "domains" / "solve"
            run(ROOT / "tools" / "generate.py", domain, "--out", tmp)
            target = pathlib.Path(tmp) / ".github/skills/solve-framing/SKILL.md"
            target.write_text("手で直した", encoding="utf-8")
            r = run(ROOT / "tools" / "generate.py", domain, "--out", tmp)
            self.assertIn("残した", r.stdout)
            self.assertEqual(target.read_text(encoding="utf-8"), "手で直した")
            run(ROOT / "tools" / "generate.py", domain, "--out", tmp, "--force")
            self.assertNotEqual(target.read_text(encoding="utf-8"), "手で直した")

    def test_solve_skills_are_filled(self):
        files = generate.build(generate.load(ROOT / "domains/solve"), ROOT / "domains/solve")
        for rel, text in files.items():
            if rel.endswith("SKILL.md"):
                self.assertNotIn("TODO(分野の知識)", text, rel)

    def test_iec62443_matches_reference_agents(self):
        """MakeAgent_001 と同じ 15 のエージェント名になる。"""
        files = generate.build(generate.load(ROOT / "domains/iec62443"), ROOT / "domains/iec62443")
        names = {r[len(".github/agents/"):-len(".agent.md")] for r in files if r.startswith(".github/agents/")}
        self.assertEqual(names, {
            "orchestrator", "req-analyzer", "doc-writer", "test-designer", "coder", "tester",
            "req-reviewer", "doc-reviewer", "test-design-reviewer", "code-reviewer", "test-reviewer",
            "reconciler", "auditor", "librarian", "improver"})

    def test_definition_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = (ROOT / "domains/_template/domain.toml").read_text(encoding="utf-8")
            bad = bad.replace('flow = ["maker"]', 'flow = ["nobody"]').replace('tracker = "github"', 'tracker = "jira"')
            (pathlib.Path(tmp) / "domain.toml").write_text(bad, encoding="utf-8")
            with self.assertRaises(generate.DefinitionError) as e:
                generate.load(tmp)
            self.assertIn("nobody", str(e.exception))
            self.assertIn("jira", str(e.exception))

    def test_this_repository(self):
        self.assertEqual(run(ROOT / "tools/sync_agents.py", "--check").returncode, 0)
        links = run(ROOT / "tools/check_links.py", "--exclude", "template", "--exclude", "domains", "--exclude", "out")
        self.assertEqual(links.returncode, 0, links.stdout)


if __name__ == "__main__":
    unittest.main()
