"""Mini Git 단위 테스트. 실행: python -m unittest discover tests"""

import os  # 파일 경로 합치기
import random  # 테스트용 난수
import re  # 정규식 검사
import tempfile  # 임시 폴더 생성
import unittest  # 파이썬 기본 테스트 도구
from datetime import datetime, timedelta  # 시각, 시간 간격
from pathlib import Path  # 파일 경로/읽기/쓰기 도구

from minigit import graph  # 그래프 알고리즘
from minigit.cli import MiniGitCLI, parse  # CLI와 입력 파서
from minigit.commit import Commit  # 커밋 타입
from minigit.diff import diff_lines  # 줄 비교 함수
from minigit.index import SearchIndex  # 검색 인덱스
from minigit.repository import MiniGitError, Repository  # 저장소와 에러
from minigit.sorting import insertion_sort, merge_sort, quick_sort  # 정렬 함수들

BASE_TIME = datetime(2024, 1, 15, 9, 0, 0)  # 테스트 커밋의 기준 시각


def make_graph(edges: dict[str, list[str]]) -> dict[str, Commit]:
    """{hash: [parents]} 로 테스트용 커밋 그래프를 만든다 (dict 순서 = 생성 순서)."""
    commits = {}  # 결과 그래프
    for i, (h, parents) in enumerate(edges.items()):  # 순번과 함께 하나씩
        # 커밋을 만들고 시각은 1분씩 늘린다
        commits[h] = Commit(h, f"msg {h}", "tester", BASE_TIME + timedelta(minutes=i), parents, seq=i)
    return commits  # 완성된 그래프 반환


class TestSorting(unittest.TestCase):
    def test_all_algorithms_sort_correctly(self):
        rng = random.Random(0)  # seed 고정 난수
        for size in (0, 1, 2, 10, 200):  # 여러 크기로 시험
            data = [rng.randint(0, 50) for _ in range(size)]  # 난수 리스트
            expected = merge_sort(data)  # 병합 정렬 결과를 기준으로
            for i in range(len(expected) - 1):  # 이웃한 두 원소마다
                self.assertLessEqual(expected[i], expected[i + 1])  # 앞이 뒤보다 작거나 같은지 확인
            self.assertEqual(quick_sort(data), expected)  # 퀵 정렬 결과가 같은지
            self.assertEqual(insertion_sort(data), expected)  # 삽입 정렬 결과가 같은지

    def test_custom_key_and_stability(self):
        items = [("bob", 1), ("alice", 2), ("bob", 3), ("alice", 4)]  # 이름이 겹치는 데이터
        by_name = merge_sort(items, key=lambda x: x[0])  # 이름으로만 정렬
        # 같은 이름끼리는 원래 순서(2→4, 1→3)가 유지돼야 한다 (안정 정렬)
        self.assertEqual(by_name, [("alice", 2), ("alice", 4), ("bob", 1), ("bob", 3)])
        self.assertEqual(insertion_sort(items, key=lambda x: x[0]), by_name)  # 삽입 정렬도 같은 결과

    def test_original_list_unchanged(self):
        data = [3, 1, 2]  # 원본
        merge_sort(data)  # 정렬 실행
        self.assertEqual(data, [3, 1, 2])  # 원본은 그대로인지 확인

    def test_no_builtin_sort_used(self):
        source_dir = Path(__file__).resolve().parent.parent / "minigit"  # 소스 폴더 경로
        for path in source_dir.glob("*.py"):  # 모든 .py 파일마다
            code = path.read_text(encoding="utf-8")  # 파일 내용 읽기
            # 내장 정렬 함수 호출이 하나도 없는지 확인
            self.assertIsNone(re.search(r"\bsorted\(|\.sort\(", code), path.name)


class TestGraph(unittest.TestCase):
    def setUp(self):
        # a - b - d (merge)   e (다른 루트, 연결 없음)
        #   \ c /
        self.g = make_graph({  # 테스트용 그래프
            "aaaaaaa": [],  # 루트
            "ccccccc": ["aaaaaaa"],  # a의 자식
            "bbbbbbb": ["aaaaaaa"],  # a의 자식
            "ddddddd": ["ccccccc", "bbbbbbb"],  # c와 b를 합친 merge 커밋
            "eeeeeee": [],  # 따로 떨어진 루트
        })

    def test_topological_sort_parents_first(self):
        order = graph.topological_sort(self.g)  # 위상 정렬
        self.assertEqual(len(order), len(self.g))  # 모든 커밋이 나왔는지
        position = {h: i for i, h in enumerate(order)}  # 커밋별 위치
        for commit in self.g.values():  # 커밋마다
            for parent in commit.parents:  # 부모마다
                self.assertLess(position[parent], position[commit.hash])  # 부모가 더 앞에 있는지

    def test_shortest_path_lexicographic_tiebreak(self):
        # a->b->d 와 a->c->d 둘 다 길이 2 → 사전순으로 작은 b 경유
        self.assertEqual(graph.shortest_path(self.g, "aaaaaaa", "ddddddd"),
                         ["aaaaaaa", "bbbbbbb", "ddddddd"])  # b를 거치는 경로가 나와야 한다

    def test_shortest_path_undirected(self):
        # 형제 커밋 사이: c -> a -> b (부모 방향, 자식 방향 모두 이동)
        self.assertEqual(graph.shortest_path(self.g, "ccccccc", "bbbbbbb"),
                         ["ccccccc", "aaaaaaa", "bbbbbbb"])  # 부모 a를 거쳐 가야 한다

    def test_shortest_path_same_and_none(self):
        self.assertEqual(graph.shortest_path(self.g, "aaaaaaa", "aaaaaaa"), ["aaaaaaa"])  # 같은 커밋이면 자기 자신만
        self.assertIsNone(graph.shortest_path(self.g, "aaaaaaa", "eeeeeee"))  # 연결 안 됐으면 None

    def test_ancestors_no_duplicates(self):
        ancestors = graph.find_ancestors(self.g, "ddddddd")  # d의 조상
        self.assertEqual(ancestors, ["ccccccc", "bbbbbbb", "aaaaaaa"])  # a는 두 경로로 가도 한 번만
        self.assertEqual(graph.find_ancestors(self.g, "aaaaaaa"), [])  # 루트는 조상이 없다

    def test_cycle_detected(self):
        cyclic = make_graph({"x": ["y"], "y": ["x"]})  # 서로가 부모인 잘못된 그래프
        with self.assertRaises(ValueError):  # 에러가 나야 한다
            graph.topological_sort(cyclic)  # 위상 정렬 시도


class TestIndex(unittest.TestCase):
    def test_keyword_and_author(self):
        index = SearchIndex()  # 빈 인덱스
        index.add_commit("h1", "Add login feature", "Alice")  # 커밋 1 등록
        index.add_commit("h2", "Fix LOGIN bug", "Bob")  # 커밋 2 등록 (대문자 LOGIN)
        index.add_commit("h3", "login login", "alice")  # 커밋 3 등록 (같은 단어 두 번)
        self.assertEqual(index.search_keyword("login"), ["h1", "h2", "h3"])  # 대소문자 무시, 중복 없음
        self.assertEqual(index.search_keyword("add LOGIN"), ["h1"])  # 두 단어 모두 있는 커밋만
        self.assertEqual(index.search_keyword("nothing"), [])  # 없는 단어는 빈 결과
        self.assertEqual(index.search_author("ALICE"), ["h1", "h3"])  # 작성자도 대소문자 무시


class TestRepository(unittest.TestCase):
    def setUp(self):
        self.repo = Repository()  # 새 저장소
        self.repo.init("Alice")  # Alice로 초기화

    def test_requires_init(self):
        with self.assertRaises(MiniGitError):  # 에러가 나야 한다
            Repository().commit("x")  # INIT 없이 커밋 시도

    def test_commit_and_branch(self):
        c1 = self.repo.commit("first")  # 첫 커밋
        self.assertEqual(c1.parents, [])  # 첫 커밋은 부모 없음
        self.repo.create_branch("feature")  # feature 브랜치 생성
        self.repo.switch("feature")  # feature로 이동
        c2 = self.repo.commit("second")  # 두 번째 커밋
        self.assertEqual(c2.parents, [c1.hash])  # 부모는 첫 커밋
        self.assertEqual(self.repo.branches["main"], c1.hash)  # main은 그대로 c1
        self.assertEqual(self.repo.branches["feature"], c2.hash)  # feature만 c2로 이동

    def test_branch_errors(self):
        with self.assertRaises(MiniGitError):  # 에러가 나야 한다
            self.repo.create_branch("x")  # 커밋 없음
        self.repo.commit("first")  # 커밋 하나 만들고
        self.repo.create_branch("x")  # 이제는 브랜치 생성 성공
        with self.assertRaisesRegex(MiniGitError, "Branch already exists"):  # 중복 에러 확인
            self.repo.create_branch("x")  # 같은 이름 다시 생성
        with self.assertRaisesRegex(MiniGitError, "Unknown branch: y"):  # 없는 브랜치 에러 확인
            self.repo.switch("y")  # 없는 브랜치로 이동

    def test_hashes_unique(self):
        hashes = {self.repo.commit("same message").hash for _ in range(2000)}  # 같은 메시지로 2000번 커밋
        self.assertEqual(len(hashes), 2000)  # hash가 하나도 안 겹쳤는지

    def test_sort_by_author(self):
        self.repo.init("Charlie")  # 사용자 Charlie로 변경
        self.repo.commit("c1")  # Charlie 커밋
        self.repo.init("alice")  # 사용자 alice로 변경
        self.repo.commit("a1")  # alice 커밋
        self.repo.init("Bob")  # 사용자 Bob으로 변경
        self.repo.commit("b1")  # Bob 커밋
        authors = [c.author for c in self.repo.log("author")]  # 작성자순 정렬 결과
        self.assertEqual(authors, ["alice", "Bob", "Charlie"])  # 대소문자 무시한 알파벳순
        self.assertEqual([c.message for c in self.repo.log("date")], ["c1", "a1", "b1"])  # 날짜순은 만든 순서

    def test_merge(self):
        base = self.repo.commit("base")  # 공통 시작 커밋
        self.repo.create_branch("feature")  # feature 브랜치 생성
        self.repo.switch("feature")  # feature로 이동
        f = self.repo.commit("feature work")  # feature 쪽 커밋
        self.repo.switch("main")  # main으로 복귀
        m = self.repo.commit("main work")  # main 쪽 커밋
        merged = self.repo.merge("feature")  # feature를 main에 병합
        self.assertEqual(merged.parents, [m.hash, f.hash])  # 부모가 main, feature 순서인지
        self.assertIsNone(self.repo.merge("feature"))  # 다시 병합하면 할 게 없음
        self.assertEqual(len(self.repo.ancestors(merged.hash)), 3)  # 조상은 m, f, base 3개
        # f와 m 사이 경로가 사전순으로 작은 후보와 같은지
        self.assertEqual(self.repo.path(f.hash, m.hash), smaller_path(f.hash, m.hash, base.hash, merged.hash))


def smaller_path(f, m, base, merged):
    """f와 m 사이 최단 경로 후보 두 개 중 사전순으로 작은 것."""
    via_base = [f, base, m]  # base를 거치는 경로
    via_merge = [f, merged, m]  # merge 커밋을 거치는 경로
    return via_base if "->".join(via_base) < "->".join(via_merge) else via_merge  # 문자열로 비교해 작은 쪽


class TestCLI(unittest.TestCase):
    def setUp(self):
        self.cli = MiniGitCLI()  # 새 CLI

    def run_cmd(self, line):
        return self.cli.execute(line)  # 명령 한 줄 실행 결과 반환

    def test_parse(self):
        self.assertEqual(parse('COMMIT "Add login feature"'), ("commit", ["Add login feature"]))  # 따옴표 안은 한 인자
        self.assertEqual(parse('search --author="Bob Lee"'), ("search", ["--author=Bob Lee"]))  # 옵션 안 따옴표도 처리
        with self.assertRaises(MiniGitError):  # 에러가 나야 한다
            parse('commit "unclosed')  # 따옴표가 안 닫힌 입력

    def test_example_scenario(self):
        self.assertEqual(self.run_cmd('init "Alice"'),
                         ["Initialized repository.", "Current branch: main", "Current user: Alice"])  # 초기화 출력 확인
        out = self.run_cmd('commit "Initial commit"')[0]  # 첫 커밋 출력
        self.assertRegex(out, r"^\[main [0-9a-f]{7}\] Initial commit$")  # [main 7자리hash] 형식인지
        self.assertEqual(self.run_cmd("branch feature"), ["Created branch: feature"])  # 브랜치 생성 출력
        self.assertEqual(self.run_cmd("SWITCH feature"), ["Switched to branch: feature"])  # 대문자 명령도 동작
        self.run_cmd('commit "Add login feature"')  # feature에 커밋
        self.run_cmd("switch main")  # main으로 이동
        self.run_cmd('commit "Add payment feature"')  # main에 커밋
        log = self.run_cmd("log")  # 로그 출력
        # 빈 줄을 제외한 홀수 번째 줄(메시지)만 모아 순서 확인
        non_empty_log = [line for line in log if line]  # 커밋 사이 빈 줄 제거
        self.assertEqual(non_empty_log[1::2], ["Initial commit", "Add login feature", "Add payment feature"])
        self.assertEqual(log[2], "")  # 첫 번째 커밋과 두 번째 커밋 사이를 빈 줄로 구분
        self.assertEqual(log[5], "")  # 두 번째 커밋과 세 번째 커밋 사이를 빈 줄로 구분
        search = self.run_cmd('search "login"')  # login 검색
        self.assertEqual(search[0], "Found 1 commit:")  # 1개 찾았다는 줄
        self.assertTrue(search[1].endswith(": Add login feature"))  # 찾은 커밋 메시지 확인

    def test_path_and_ancestors_output(self):
        self.run_cmd("init Alice")  # 초기화
        h1 = self.run_cmd("commit one")[0][6:13]  # 출력 '[main xxxxxxx] one'에서 hash만 잘라낸다
        h2 = self.run_cmd("commit two")[0][6:13]  # 두 번째 커밋 hash
        self.assertEqual(self.run_cmd(f"path {h1} {h2}"), [f"Path: {h1} -> {h2}"])  # 경로 출력 형식
        self.assertEqual(self.run_cmd(f"ancestors {h2}"), [f"Ancestors of {h2} (1):", f"- {h1}: one"])  # 조상 출력 형식

    def test_error_messages(self):
        self.assertEqual(self.run_cmd("log"), ["Not initialized. Use INIT <user_name> first"])  # INIT 전 명령
        self.run_cmd("init Alice")  # 초기화
        self.assertEqual(self.run_cmd("commit"), ["Invalid args"])  # 메시지 없음
        self.assertEqual(self.run_cmd("commit two words"), ["Invalid args"])  # 따옴표 없이 두 단어
        self.assertEqual(self.run_cmd("switch nope"), ["Unknown branch: nope"])  # 없는 브랜치
        self.assertEqual(self.run_cmd("ancestors zzz"), ["Unknown commit: zzz"])  # 없는 커밋
        self.assertEqual(self.run_cmd("log --sort-by=size"), ["Invalid args"])  # 잘못된 정렬 기준
        self.assertEqual(self.run_cmd("hello"), ["Unknown command: hello"])  # 없는 명령어
        self.assertEqual(self.run_cmd("log"), ["No commits yet"])  # 커밋 없는 상태의 로그


class TestDiff(unittest.TestCase):
    def test_diff_lines(self):
        result = diff_lines(["a", "b", "c"], ["a", "c", "d"])  # 두 줄 목록 비교
        self.assertEqual(result, ["  a", "- b", "  c", "+ d"])  # b 삭제, d 추가

    def test_diff_command(self):
        cli = MiniGitCLI()  # 새 CLI
        with tempfile.TemporaryDirectory() as tmp:  # 테스트 끝나면 지워지는 임시 폴더
            p1, p2 = os.path.join(tmp, "1.txt"), os.path.join(tmp, "2.txt")  # 파일 경로 2개
            Path(p1).write_text("x\ny\n", encoding="utf-8")  # 첫 파일 내용
            Path(p2).write_text("x\nz\n", encoding="utf-8")  # 둘째 파일 내용
            self.assertEqual(cli.execute(f"diff {p1} {p2}"), ["  x", "- y", "+ z"])  # diff 출력 확인
            self.assertTrue(cli.execute(f"diff {p1} nope.txt")[0].startswith("Cannot read file"))  # 없는 파일 에러


if __name__ == "__main__":  # 이 파일을 직접 실행하면
    unittest.main()  # 테스트 전체 실행
