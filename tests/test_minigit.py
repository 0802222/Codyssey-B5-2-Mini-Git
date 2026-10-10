"""Mini Git 단위 테스트. 실행: python -m unittest discover tests"""

import os
import random
import re
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from minigit import graph
from minigit.cli import MiniGitCLI, parse
from minigit.commit import Commit
from minigit.diff import diff_lines
from minigit.index import SearchIndex
from minigit.repository import MiniGitError, Repository
from minigit.sorting import insertion_sort, merge_sort, quick_sort

BASE_TIME = datetime(2024, 1, 15, 9, 0, 0)


def make_graph(edges: dict[str, list[str]]) -> dict[str, Commit]:
    """{hash: [parents]} 로 테스트용 커밋 그래프를 만든다 (dict 순서 = 생성 순서)."""
    commits = {}
    for i, (h, parents) in enumerate(edges.items()):
        commits[h] = Commit(h, f"msg {h}", "tester", BASE_TIME + timedelta(minutes=i), parents, seq=i)
    return commits


class TestSorting(unittest.TestCase):
    def test_all_algorithms_sort_correctly(self):
        rng = random.Random(0)
        for size in (0, 1, 2, 10, 200):
            data = [rng.randint(0, 50) for _ in range(size)]
            expected = merge_sort(data)
            for i in range(len(expected) - 1):
                self.assertLessEqual(expected[i], expected[i + 1])
            self.assertEqual(quick_sort(data), expected)
            self.assertEqual(insertion_sort(data), expected)

    def test_custom_key_and_stability(self):
        items = [("bob", 1), ("alice", 2), ("bob", 3), ("alice", 4)]
        by_name = merge_sort(items, key=lambda x: x[0])
        self.assertEqual(by_name, [("alice", 2), ("alice", 4), ("bob", 1), ("bob", 3)])
        self.assertEqual(insertion_sort(items, key=lambda x: x[0]), by_name)

    def test_original_list_unchanged(self):
        data = [3, 1, 2]
        merge_sort(data)
        self.assertEqual(data, [3, 1, 2])

    def test_no_builtin_sort_used(self):
        source_dir = Path(__file__).resolve().parent.parent / "minigit"
        for path in source_dir.glob("*.py"):
            code = path.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"\bsorted\(|\.sort\(", code), path.name)


class TestGraph(unittest.TestCase):
    def setUp(self):
        # a - b - d (merge)   e (다른 루트, 연결 없음)
        #   \ c /
        self.g = make_graph({
            "aaaaaaa": [],
            "ccccccc": ["aaaaaaa"],
            "bbbbbbb": ["aaaaaaa"],
            "ddddddd": ["ccccccc", "bbbbbbb"],
            "eeeeeee": [],
        })

    def test_topological_sort_parents_first(self):
        order = graph.topological_sort(self.g)
        self.assertEqual(len(order), len(self.g))
        position = {h: i for i, h in enumerate(order)}
        for commit in self.g.values():
            for parent in commit.parents:
                self.assertLess(position[parent], position[commit.hash])

    def test_shortest_path_lexicographic_tiebreak(self):
        # a->b->d 와 a->c->d 둘 다 길이 2 → 사전순으로 작은 b 경유
        self.assertEqual(graph.shortest_path(self.g, "aaaaaaa", "ddddddd"),
                         ["aaaaaaa", "bbbbbbb", "ddddddd"])

    def test_shortest_path_undirected(self):
        # 형제 커밋 사이: c -> a -> b (부모 방향, 자식 방향 모두 이동)
        self.assertEqual(graph.shortest_path(self.g, "ccccccc", "bbbbbbb"),
                         ["ccccccc", "aaaaaaa", "bbbbbbb"])

    def test_shortest_path_same_and_none(self):
        self.assertEqual(graph.shortest_path(self.g, "aaaaaaa", "aaaaaaa"), ["aaaaaaa"])
        self.assertIsNone(graph.shortest_path(self.g, "aaaaaaa", "eeeeeee"))

    def test_ancestors_no_duplicates(self):
        ancestors = graph.find_ancestors(self.g, "ddddddd")
        self.assertEqual(ancestors, ["ccccccc", "bbbbbbb", "aaaaaaa"])
        self.assertEqual(graph.find_ancestors(self.g, "aaaaaaa"), [])

    def test_cycle_detected(self):
        cyclic = make_graph({"x": ["y"], "y": ["x"]})
        with self.assertRaises(ValueError):
            graph.topological_sort(cyclic)


class TestIndex(unittest.TestCase):
    def test_keyword_and_author(self):
        index = SearchIndex()
        index.add_commit("h1", "Add login feature", "Alice")
        index.add_commit("h2", "Fix LOGIN bug", "Bob")
        index.add_commit("h3", "login login", "alice")
        self.assertEqual(index.search_keyword("login"), ["h1", "h2", "h3"])
        self.assertEqual(index.search_keyword("add LOGIN"), ["h1"])
        self.assertEqual(index.search_keyword("nothing"), [])
        self.assertEqual(index.search_author("ALICE"), ["h1", "h3"])


class TestRepository(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()
        self.repo.init("Alice")

    def test_requires_init(self):
        with self.assertRaises(MiniGitError):
            Repository().commit("x")

    def test_commit_and_branch(self):
        c1 = self.repo.commit("first")
        self.assertEqual(c1.parents, [])
        self.repo.create_branch("feature")
        self.repo.switch("feature")
        c2 = self.repo.commit("second")
        self.assertEqual(c2.parents, [c1.hash])
        self.assertEqual(self.repo.branches["main"], c1.hash)
        self.assertEqual(self.repo.branches["feature"], c2.hash)

    def test_branch_errors(self):
        with self.assertRaises(MiniGitError):
            self.repo.create_branch("x")  # 커밋 없음
        self.repo.commit("first")
        self.repo.create_branch("x")
        with self.assertRaisesRegex(MiniGitError, "Branch already exists"):
            self.repo.create_branch("x")
        with self.assertRaisesRegex(MiniGitError, "Unknown branch: y"):
            self.repo.switch("y")

    def test_hashes_unique(self):
        hashes = {self.repo.commit("same message").hash for _ in range(2000)}
        self.assertEqual(len(hashes), 2000)

    def test_sort_by_author(self):
        self.repo.init("Charlie")
        self.repo.commit("c1")
        self.repo.init("alice")
        self.repo.commit("a1")
        self.repo.init("Bob")
        self.repo.commit("b1")
        authors = [c.author for c in self.repo.log("author")]
        self.assertEqual(authors, ["alice", "Bob", "Charlie"])
        self.assertEqual([c.message for c in self.repo.log("date")], ["c1", "a1", "b1"])

    def test_merge(self):
        base = self.repo.commit("base")
        self.repo.create_branch("feature")
        self.repo.switch("feature")
        f = self.repo.commit("feature work")
        self.repo.switch("main")
        m = self.repo.commit("main work")
        merged = self.repo.merge("feature")
        self.assertEqual(merged.parents, [m.hash, f.hash])
        self.assertIsNone(self.repo.merge("feature"))
        self.assertEqual(len(self.repo.ancestors(merged.hash)), 3)
        self.assertEqual(self.repo.path(f.hash, m.hash), smaller_path(f.hash, m.hash, base.hash, merged.hash))


def smaller_path(f, m, base, merged):
    """f와 m 사이 최단 경로 후보 두 개 중 사전순으로 작은 것."""
    via_base = [f, base, m]
    via_merge = [f, merged, m]
    return via_base if "->".join(via_base) < "->".join(via_merge) else via_merge


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.cli = MiniGitCLI()

    def run_cmd(self, line):
        return self.cli.execute(line)

    def test_parse(self):
        self.assertEqual(parse('COMMIT "Add login feature"'), ("commit", ["Add login feature"]))
        self.assertEqual(parse('search --author="Bob Lee"'), ("search", ["--author=Bob Lee"]))
        with self.assertRaises(MiniGitError):
            parse('commit "unclosed')

    def test_example_scenario(self):
        self.assertEqual(self.run_cmd('init "Alice"'),
                         ["Initialized repository.", "Current branch: main", "Current user: Alice"])
        out = self.run_cmd('commit "Initial commit"')[0]
        self.assertRegex(out, r"^\[main [0-9a-f]{7}\] Initial commit$")
        self.assertEqual(self.run_cmd("branch feature"), ["Created branch: feature"])
        self.assertEqual(self.run_cmd("SWITCH feature"), ["Switched to branch: feature"])
        self.run_cmd('commit "Add login feature"')
        self.run_cmd("switch main")
        self.run_cmd('commit "Add payment feature"')
        log = self.run_cmd("log")
        self.assertEqual(log[1::2], ["Initial commit", "Add login feature", "Add payment feature"])
        search = self.run_cmd('search "login"')
        self.assertEqual(search[0], "Found 1 commit:")
        self.assertTrue(search[1].endswith(": Add login feature"))

    def test_path_and_ancestors_output(self):
        self.run_cmd("init Alice")
        h1 = self.run_cmd("commit one")[0][6:13]
        h2 = self.run_cmd("commit two")[0][6:13]
        self.assertEqual(self.run_cmd(f"path {h1} {h2}"), [f"Path: {h1} -> {h2}"])
        self.assertEqual(self.run_cmd(f"ancestors {h2}"), [f"Ancestors of {h2} (1):", f"- {h1}: one"])

    def test_error_messages(self):
        self.assertEqual(self.run_cmd("log"), ["Not initialized. Use INIT <user_name> first"])
        self.run_cmd("init Alice")
        self.assertEqual(self.run_cmd("commit"), ["Invalid args"])
        self.assertEqual(self.run_cmd("commit two words"), ["Invalid args"])
        self.assertEqual(self.run_cmd("switch nope"), ["Unknown branch: nope"])
        self.assertEqual(self.run_cmd("ancestors zzz"), ["Unknown commit: zzz"])
        self.assertEqual(self.run_cmd("log --sort-by=size"), ["Invalid args"])
        self.assertEqual(self.run_cmd("hello"), ["Unknown command: hello"])
        self.assertEqual(self.run_cmd("log"), ["No commits yet"])


class TestDiff(unittest.TestCase):
    def test_diff_lines(self):
        result = diff_lines(["a", "b", "c"], ["a", "c", "d"])
        self.assertEqual(result, ["  a", "- b", "  c", "+ d"])

    def test_diff_command(self):
        cli = MiniGitCLI()
        with tempfile.TemporaryDirectory() as tmp:
            p1, p2 = os.path.join(tmp, "1.txt"), os.path.join(tmp, "2.txt")
            Path(p1).write_text("x\ny\n", encoding="utf-8")
            Path(p2).write_text("x\nz\n", encoding="utf-8")
            self.assertEqual(cli.execute(f"diff {p1} {p2}"), ["  x", "- y", "+ z"])
            self.assertTrue(cli.execute(f"diff {p1} nope.txt")[0].startswith("Cannot read file"))


if __name__ == "__main__":
    unittest.main()
