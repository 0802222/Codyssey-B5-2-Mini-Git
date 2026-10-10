"""CLI(REPL): 입력 파싱 → 명령 실행 → 결과 출력."""

import shlex

from .benchmark import run_benchmark
from .commit import Commit
from .diff import diff_files
from .repository import MiniGitError, Repository

PROMPT = "mini-git> "
EXIT_COMMANDS = {"exit", "quit"}

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
        tokens = shlex.split(line)
    except ValueError:
        raise MiniGitError("Invalid args")
    if not tokens:
        return "", []
    return tokens[0].lower(), tokens[1:]


def format_commit(commit: Commit, show_branch: bool = True) -> list[str]:
    """LOG 출력용 커밋 두 줄: 'commit <hash> (<author>, <time>) [<branch>]' + 메시지."""
    header = f"commit {commit.hash} ({commit.author}, {commit.time_str()})"
    if show_branch:
        header += f" [{commit.branch}]"
    if len(commit.parents) > 1:
        header += f" Merge: {' '.join(commit.parents)}"
    return [header, commit.message]


def format_commit_list(commits: list[Commit]) -> list[str]:
    """SEARCH 결과 출력: 'Found N commit(s):' + '- <hash>: <message>' 목록."""
    if not commits:
        return ["No commits found"]
    noun = "commit" if len(commits) == 1 else "commits"
    return [f"Found {len(commits)} {noun}:"] + [f"- {c.hash}: {c.message}" for c in commits]


def _expect(args: list[str], count: int) -> None:
    """인자 개수가 정확히 count개가 아니면 Invalid args."""
    if len(args) != count:
        raise MiniGitError("Invalid args")


class MiniGitCLI:
    """명령어 이름 → 처리 함수 매핑을 가지고 한 줄씩 실행하는 인터프리터."""

    def __init__(self) -> None:
        self.repo = Repository()
        self.handlers = {
            "init": self.cmd_init,
            "branch": self.cmd_branch,
            "switch": self.cmd_switch,
            "commit": self.cmd_commit,
            "log": self.cmd_log,
            "path": self.cmd_path,
            "ancestors": self.cmd_ancestors,
            "search": self.cmd_search,
            "merge": self.cmd_merge,
            "diff": self.cmd_diff,
            "bench": self.cmd_bench,
            "help": self.cmd_help,
        }

    def execute(self, line: str) -> list[str]:
        """입력 한 줄을 실행하고 출력할 줄 목록을 반환한다. 에러도 메시지로 반환한다."""
        try:
            command, args = parse(line)
            if not command:
                return []
            handler = self.handlers.get(command)
            if handler is None:
                return [f"Unknown command: {command}"]
            return handler(args)
        except MiniGitError as e:
            return [str(e)]

    # ---------- 명령 처리 함수 ----------

    def cmd_init(self, args: list[str]) -> list[str]:
        _expect(args, 1)
        created = self.repo.init(args[0])
        return [
            "Initialized repository." if created else "Reinitialized repository (history kept).",
            f"Current branch: {self.repo.head}",
            f"Current user: {self.repo.user}",
        ]

    def cmd_branch(self, args: list[str]) -> list[str]:
        if not args:  # 인자가 없으면 브랜치 목록 출력 (현재 브랜치는 *)
            return [
                f"{'*' if name == self.repo.head else ' '} {name} -> {commit or '(no commits)'}"
                for name, commit in self.repo.list_branches().items()
            ]
        _expect(args, 1)
        self.repo.create_branch(args[0])
        return [f"Created branch: {args[0]}"]

    def cmd_switch(self, args: list[str]) -> list[str]:
        _expect(args, 1)
        self.repo.switch(args[0])
        return [f"Switched to branch: {args[0]}"]

    def cmd_commit(self, args: list[str]) -> list[str]:
        _expect(args, 1)
        commit = self.repo.commit(args[0])
        return [f"[{commit.branch} {commit.hash}] {commit.message}"]

    def cmd_log(self, args: list[str]) -> list[str]:
        sort_by = None
        if args:
            _expect(args, 1)
            option, _, value = args[0].partition("=")
            if option.lower() != "--sort-by" or value.lower() not in ("date", "author"):
                raise MiniGitError("Invalid args")
            sort_by = value.lower()
        commits = self.repo.log(sort_by)
        if not commits:
            return ["No commits yet"]
        lines = []
        for commit in commits:
            lines.extend(format_commit(commit, show_branch=sort_by is None))
        return lines

    def cmd_path(self, args: list[str]) -> list[str]:
        _expect(args, 2)
        path = self.repo.path(args[0], args[1])
        if path is None:
            return ["No path"]
        return ["Path: " + " -> ".join(path)]

    def cmd_ancestors(self, args: list[str]) -> list[str]:
        _expect(args, 1)
        ancestors = self.repo.ancestors(args[0])
        if not ancestors:
            return [f"No ancestors of {args[0]}"]
        return [f"Ancestors of {args[0]} ({len(ancestors)}):"] + [
            f"- {c.hash}: {c.message}" for c in ancestors
        ]

    def cmd_search(self, args: list[str]) -> list[str]:
        _expect(args, 1)
        arg = args[0]
        if arg.lower().startswith("--author="):
            name = arg.partition("=")[2]
            if not name:
                raise MiniGitError("Invalid args")
            return format_commit_list(self.repo.search_author(name))
        if arg.startswith("--"):
            raise MiniGitError("Invalid args")
        return format_commit_list(self.repo.search_keyword(arg))

    def cmd_merge(self, args: list[str]) -> list[str]:
        _expect(args, 1)
        commit = self.repo.merge(args[0])
        if commit is None:
            return ["Already up to date."]
        return [f"[{commit.branch} {commit.hash}] {commit.message}"]

    def cmd_diff(self, args: list[str]) -> list[str]:
        _expect(args, 2)
        try:
            lines = diff_files(args[0], args[1])
        except OSError as e:
            raise MiniGitError(f"Cannot read file: {e.filename}")
        return lines or ["(both files are empty)"]

    def cmd_bench(self, args: list[str]) -> list[str]:
        try:
            sizes = [int(a) for a in args]
        except ValueError:
            raise MiniGitError("Invalid args")
        if any(size <= 0 for size in sizes):
            raise MiniGitError("Invalid args")
        return run_benchmark(sizes or None)

    def cmd_help(self, args: list[str]) -> list[str]:
        return HELP_TEXT.splitlines()


def run() -> None:
    """REPL 루프: 프롬프트 출력 → 입력 → 실행 → 결과 출력을 exit/quit까지 반복한다."""
    cli = MiniGitCLI()
    print("Mini Git - type HELP for commands, EXIT to quit")
    while True:
        try:
            line = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if line.strip().lower() in EXIT_COMMANDS:
            break
        for out in cli.execute(line):
            print(out)
