"""CLI(REPL): 입력 파싱 → 명령 실행 → 결과 출력."""

import shlex  # 따옴표를 인식해 문자열을 쪼개는 모듈

from .benchmark import run_benchmark  # 정렬 성능 비교 함수
from .commit import Commit  # 커밋 타입
from .diff import diff_files  # 파일 비교 함수
from .repository import MiniGitError, Repository  # 저장소와 에러 타입

PROMPT = "mini-git> "  # 입력 대기 표시
EXIT_COMMANDS = {"exit", "quit"}  # 종료 명령어 모음

# HELP 명령으로 보여줄 도움말 (여러 줄 문자열)
HELP_TEXT = """\
Commands (case-insensitive, quote arguments that contain spaces):
  INIT <user_name>                 Initialize repository (main branch)
  BRANCH [<branch_name>]           Create a branch at HEAD (no arg: list branches)
  SWITCH <branch_name>             Move HEAD to a branch
  COMMIT <message>                 Create a commit on the current branch
  LOG [--sort-by=date|author]      Show commits (default: parents before children)
  PATH <commit1> <commit2>         Shortest path between two commits
  ANCESTORS <commit_hash>          All ancestors of a commit
  SEARCH <keyword>                 Commits whose message contains the keyword
  SEARCH --author=<name>           Commits by an author
  MERGE <branch_name>              (bonus) Create a merge commit
  DIFF <file1> <file2>             (bonus) Line-by-line file comparison
  BENCH [<size> ...]               (bonus) Compare sorting algorithm speed
  HELP                             Show this help
  EXIT | QUIT                      Quit"""


def parse(line: str) -> tuple[str, list[str]]:
    """입력 한 줄을 (소문자 명령어, 인자 목록)으로 나눈다.

    shlex를 이용해 따옴표로 감싼 문자열을 하나의 인자로 묶는다.
    예) 'COMMIT "Add login feature"' -> ('commit', ['Add login feature'])
    따옴표가 닫히지 않으면 ValueError가 발생하므로 Invalid args로 처리한다.
    """
    try:
        tokens = shlex.split(line)  # 공백 기준으로 쪼개되 따옴표 안은 하나로 묶는다
    except ValueError:  # 따옴표가 안 닫혔으면
        raise MiniGitError("Invalid args")  # 잘못된 인자 에러
    if not tokens:  # 빈 줄이면
        return "", []  # 명령어 없음
    return tokens[0].lower(), tokens[1:]  # 첫 단어는 소문자 명령어, 나머지는 인자


def format_commit(commit: Commit, show_branch: bool = True) -> list[str]:
    """LOG 출력용 커밋 두 줄: 'commit <hash> (<author>, <time>) [<branch>]' + 메시지."""
    header = f"commit {commit.hash} ({commit.author}, {commit.time_str()})"  # 첫 줄: hash, 작성자, 시각
    if show_branch:  # 브랜치를 보여줄 때만
        header += f" [{commit.branch}]"  # 브랜치 이름 붙이기
    if len(commit.parents) > 1:  # merge 커밋이면 (부모 2개)
        header += f" Merge: {' '.join(commit.parents)}"  # 부모 hash들을 표시
    return [header, commit.message]  # 첫 줄 + 메시지 줄


def format_commit_list(commits: list[Commit]) -> list[str]:
    """SEARCH 결과 출력: 'Found N commit(s):' + '- <hash>: <message>' 목록."""
    if not commits:  # 결과가 없으면
        return ["No commits found"]  # 없다고 출력
    noun = "commit" if len(commits) == 1 else "commits"  # 1개면 단수, 여러 개면 복수
    return [f"Found {len(commits)} {noun}:"] + [f"- {c.hash}: {c.message}" for c in commits]  # 개수 줄 + 커밋 목록


def _expect(args: list[str], count: int) -> None:
    """인자 개수가 정확히 count개가 아니면 Invalid args."""
    if len(args) != count:  # 인자 개수가 다르면
        raise MiniGitError("Invalid args")  # 에러


class MiniGitCLI:
    """명령어 이름 → 처리 함수 매핑을 가지고 한 줄씩 실행하는 인터프리터."""

    def __init__(self) -> None:
        self.repo = Repository()  # 빈 저장소 생성
        self.handlers = {  # 명령어 -> 처리 함수 표
            "init": self.cmd_init,  # 저장소 초기화
            "branch": self.cmd_branch,  # 브랜치 생성/목록
            "switch": self.cmd_switch,  # 브랜치 이동
            "commit": self.cmd_commit,  # 커밋 생성
            "log": self.cmd_log,  # 커밋 기록 보기
            "path": self.cmd_path,  # 두 커밋 사이 경로
            "ancestors": self.cmd_ancestors,  # 조상 커밋 보기
            "search": self.cmd_search,  # 커밋 검색
            "merge": self.cmd_merge,  # 브랜치 병합
            "diff": self.cmd_diff,  # 파일 비교
            "bench": self.cmd_bench,  # 정렬 성능 비교
            "help": self.cmd_help,  # 도움말
        }

    def execute(self, line: str) -> list[str]:
        """입력 한 줄을 실행하고 출력할 줄 목록을 반환한다. 에러도 메시지로 반환한다."""
        try:
            command, args = parse(line)  # 명령어와 인자로 나눈다
            if not command:  # 빈 줄이면
                return []  # 아무것도 출력 안 함
            handler = self.handlers.get(command)  # 명령어에 맞는 처리 함수 찾기
            if handler is None:  # 모르는 명령어면
                return [f"Unknown command: {command}"]  # 알 수 없는 명령 출력
            return handler(args)  # 처리 함수 실행 결과 반환
        except MiniGitError as e:  # 처리 중 에러가 나면
            return [str(e)]  # 에러 메시지를 출력 줄로 반환

    # ---------- 명령 처리 함수 ----------

    def cmd_init(self, args: list[str]) -> list[str]:
        _expect(args, 1)  # 인자는 사용자 이름 1개
        created = self.repo.init(args[0])  # 저장소 초기화 (새로 만들었는지 결과 받기)
        return [
            # 새로 만들었으면 Initialized, 아니면 Reinitialized
            "Initialized repository." if created else "Reinitialized repository (history kept).",
            f"Current branch: {self.repo.head}",  # 현재 브랜치 출력
            f"Current user: {self.repo.user}",  # 현재 사용자 출력
        ]

    def cmd_branch(self, args: list[str]) -> list[str]:
        if not args:  # 인자가 없으면 브랜치 목록 출력 (현재 브랜치는 *)
            return [
                # 현재 브랜치면 '*', 아니면 공백 + 이름 + 가리키는 커밋
                f"{'*' if name == self.repo.head else ' '} {name} -> {commit or '(no commits)'}"
                for name, commit in self.repo.list_branches().items()  # 모든 브랜치에 대해
            ]
        _expect(args, 1)  # 인자는 브랜치 이름 1개
        self.repo.create_branch(args[0])  # 브랜치 생성
        return [f"Created branch: {args[0]}"]  # 생성 완료 메시지

    def cmd_switch(self, args: list[str]) -> list[str]:
        _expect(args, 1)  # 인자는 브랜치 이름 1개
        self.repo.switch(args[0])  # HEAD 이동
        return [f"Switched to branch: {args[0]}"]  # 이동 완료 메시지

    def cmd_commit(self, args: list[str]) -> list[str]:
        _expect(args, 1)  # 인자는 메시지 1개
        commit = self.repo.commit(args[0])  # 커밋 생성
        return [f"[{commit.branch} {commit.hash}] {commit.message}"]  # [브랜치 hash] 메시지 형식 출력

    def cmd_log(self, args: list[str]) -> list[str]:
        sort_by = None  # 기본은 정렬 옵션 없음
        if args:  # 옵션이 있으면
            _expect(args, 1)  # 옵션은 1개만
            option, _, value = args[0].partition("=")  # '--sort-by=date'를 '=' 기준으로 나눈다
            if option.lower() != "--sort-by" or value.lower() not in ("date", "author"):  # 형식이 틀리면
                raise MiniGitError("Invalid args")  # 에러
            sort_by = value.lower()  # 정렬 기준 저장
        commits = self.repo.log(sort_by)  # 커밋 목록 가져오기
        if not commits:  # 커밋이 없으면
            return ["No commits yet"]  # 없다고 출력
        lines = []  # 출력할 줄 목록
        for commit in commits:  # 커밋마다
            lines.extend(format_commit(commit, show_branch=sort_by is None))  # 두 줄씩 추가 (정렬 시 브랜치 생략)
        return lines  # 출력 줄 반환

    def cmd_path(self, args: list[str]) -> list[str]:
        _expect(args, 2)  # 인자는 커밋 hash 2개
        path = self.repo.path(args[0], args[1])  # 최단 경로 계산
        if path is None:  # 경로가 없으면
            return ["No path"]  # 없다고 출력
        return ["Path: " + " -> ".join(path)]  # hash를 화살표로 이어서 출력

    def cmd_ancestors(self, args: list[str]) -> list[str]:
        _expect(args, 1)  # 인자는 커밋 hash 1개
        ancestors = self.repo.ancestors(args[0])  # 조상 목록 가져오기
        if not ancestors:  # 조상이 없으면 (첫 커밋)
            return [f"No ancestors of {args[0]}"]  # 없다고 출력
        return [f"Ancestors of {args[0]} ({len(ancestors)}):"] + [  # 개수 줄 +
            f"- {c.hash}: {c.message}" for c in ancestors  # 조상 하나씩 한 줄
        ]

    def cmd_search(self, args: list[str]) -> list[str]:
        _expect(args, 1)  # 인자는 1개
        arg = args[0]  # 검색어 또는 옵션
        if arg.lower().startswith("--author="):  # 작성자 검색이면
            name = arg.partition("=")[2]  # '=' 뒤의 이름만 꺼낸다
            if not name:  # 이름이 비어 있으면
                raise MiniGitError("Invalid args")  # 에러
            return format_commit_list(self.repo.search_author(name))  # 작성자 검색 결과 출력
        if arg.startswith("--"):  # 모르는 옵션이면
            raise MiniGitError("Invalid args")  # 에러
        return format_commit_list(self.repo.search_keyword(arg))  # 키워드 검색 결과 출력

    def cmd_merge(self, args: list[str]) -> list[str]:
        _expect(args, 1)  # 인자는 브랜치 이름 1개
        commit = self.repo.merge(args[0])  # 병합 실행
        if commit is None:  # 합칠 게 없었으면
            return ["Already up to date."]  # 이미 최신이라고 출력
        return [f"[{commit.branch} {commit.hash}] {commit.message}"]  # 병합 커밋 정보 출력

    def cmd_diff(self, args: list[str]) -> list[str]:
        _expect(args, 2)  # 인자는 파일 경로 2개
        try:
            lines = diff_files(args[0], args[1])  # 두 파일 비교
        except OSError as e:  # 파일을 못 읽으면
            raise MiniGitError(f"Cannot read file: {e.filename}")  # 어떤 파일인지 알려주는 에러
        return lines or ["(both files are empty)"]  # 결과가 비면 둘 다 빈 파일이라고 출력

    def cmd_bench(self, args: list[str]) -> list[str]:
        try:
            sizes = [int(a) for a in args]  # 인자를 정수로 변환
        except ValueError:  # 숫자가 아니면
            raise MiniGitError("Invalid args")  # 에러
        if any(size <= 0 for size in sizes):  # 0 이하 크기가 있으면
            raise MiniGitError("Invalid args")  # 에러
        return run_benchmark(sizes or None)  # 크기가 없으면 기본값으로 벤치마크 실행

    def cmd_help(self, args: list[str]) -> list[str]:
        return HELP_TEXT.splitlines()  # 도움말을 줄 단위로 반환


def run() -> None:
    """REPL 루프: 프롬프트 출력 → 입력 → 실행 → 결과 출력을 exit/quit까지 반복한다."""
    cli = MiniGitCLI()  # CLI 객체 생성
    print("Mini Git - type HELP for commands, EXIT to quit")  # 시작 안내 출력
    while True:  # 종료할 때까지 반복
        try:
            line = input(PROMPT)  # 사용자 입력 받기
        except (EOFError, KeyboardInterrupt):  # Ctrl+D 또는 Ctrl+C를 누르면
            print()  # 줄바꿈 하고
            break  # 종료
        if line.strip().lower() in EXIT_COMMANDS:  # exit/quit 입력이면
            break  # 종료
        for out in cli.execute(line):  # 실행 결과 줄마다
            print(out)  # 화면에 출력
