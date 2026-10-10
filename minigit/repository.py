"""저장소 상태 관리: 커밋 저장소, 브랜치, HEAD, 현재 사용자."""

import hashlib
from datetime import datetime

from . import graph
from .commit import Commit
from .index import SearchIndex
from .sorting import merge_sort

HASH_LENGTH = 7


class MiniGitError(Exception):
    """사용자에게 그대로 보여줄 에러 메시지를 담는 예외."""


class Repository:
    """메모리 위에서 동작하는 Mini Git 저장소.

    - commits: hash -> Commit 해시맵. hash로 커밋을 평균 O(1)에 찾는다.
    - branches: 브랜치 이름 -> 그 브랜치가 가리키는 커밋 hash (커밋이 없으면 None)
    - head: 현재 체크아웃된 브랜치 이름 (HEAD는 브랜치를 가리키고, 브랜치가 커밋을 가리킨다)
    """

    def __init__(self) -> None:
        self.initialized = False
        self.user = ""
        self.commits: dict[str, Commit] = {}
        self.branches: dict[str, str | None] = {}
        self.head = ""
        self.index = SearchIndex()
        self._counter = 0

    # ---------- 저장소 / 브랜치 ----------

    def init(self, user: str) -> bool:
        """저장소를 초기화하고 main 브랜치를 만든 뒤 HEAD와 사용자를 설정한다.

        이미 초기화된 저장소라면 커밋 이력은 그대로 두고 현재 사용자만 바꾼다
        (여러 작성자의 커밋을 만들어 SEARCH --author, LOG --sort-by=author를 확인하기 위함).
        새로 초기화했으면 True, 사용자만 바꿨으면 False를 반환한다.
        """
        if self.initialized:
            self.user = user
            return False
        self.initialized = True
        self.user = user
        self.branches = {"main": None}
        self.head = "main"
        return True

    def head_commit(self) -> str | None:
        """HEAD(현재 브랜치)가 가리키는 커밋 hash. 아직 커밋이 없으면 None."""
        return self.branches[self.head]

    def create_branch(self, name: str) -> None:
        """현재 HEAD 커밋을 가리키는 새 브랜치를 만든다."""
        self._require_init()
        if name in self.branches:
            raise MiniGitError(f"Branch already exists: {name}")
        if self.head_commit() is None:
            raise MiniGitError("No commits yet")
        self.branches[name] = self.head_commit()

    def list_branches(self) -> dict[str, str | None]:
        """브랜치 이름 -> 가리키는 커밋 hash 맵을 반환한다."""
        self._require_init()
        return dict(self.branches)

    def switch(self, name: str) -> None:
        """HEAD를 지정한 브랜치로 옮긴다."""
        self._require_init()
        if name not in self.branches:
            raise MiniGitError(f"Unknown branch: {name}")
        self.head = name

    # ---------- 커밋 ----------

    def commit(self, message: str) -> Commit:
        """현재 HEAD 커밋을 부모로 하는 새 커밋을 만든다."""
        self._require_init()
        parent = self.head_commit()
        parents = [parent] if parent is not None else []
        return self._create_commit(message, parents)

    def merge(self, branch: str) -> Commit | None:
        """현재 브랜치에 대상 브랜치를 병합한다 (보너스).

        현재 HEAD와 대상 브랜치 HEAD를 부모로 갖는 merge 커밋을 만든다.
        대상 커밋이 이미 현재 커밋의 조상이면 병합할 게 없으므로 None을 반환한다.
        """
        self._require_init()
        if branch not in self.branches:
            raise MiniGitError(f"Unknown branch: {branch}")
        if branch == self.head:
            raise MiniGitError("Cannot merge a branch into itself")
        current = self.head_commit()
        target = self.branches[branch]
        if current is None or target is None:
            raise MiniGitError("No commits yet")
        if graph.is_ancestor(self.commits, target, current):
            return None
        message = f"Merge branch '{branch}' into {self.head}"
        return self._create_commit(message, [current, target])

    def _create_commit(self, message: str, parents: list[str]) -> Commit:
        """커밋을 만들어 저장하고, 현재 브랜치를 앞으로 옮기고, 역색인을 갱신한다."""
        timestamp = datetime.now()
        commit_hash = self._new_hash(message, timestamp)
        self._counter += 1
        commit = Commit(
            hash=commit_hash,
            message=message,
            author=self.user,
            timestamp=timestamp,
            parents=parents,
            branch=self.head,
            seq=self._counter,
        )
        self.commits[commit_hash] = commit
        self.branches[self.head] = commit_hash
        self.index.add_commit(commit_hash, message, self.user)
        return commit

    def _new_hash(self, message: str, timestamp: datetime) -> str:
        """세션 내 유일한 7자리 hash를 만든다.

        증가 카운터 + 메시지 + 작성자 + 시각을 SHA-1로 해싱해 앞 7자리를 쓴다.
        앞 7자리만 쓰면 아주 드물게 겹칠 수 있으므로, 이미 존재하는 hash면
        nonce를 올려 다시 해싱한다 → 중복이 절대 생기지 않음을 보장한다.
        """
        nonce = 0
        while True:
            raw = f"{self._counter}|{nonce}|{message}|{self.user}|{timestamp.isoformat()}"
            candidate = hashlib.sha1(raw.encode()).hexdigest()[:HASH_LENGTH]
            if candidate not in self.commits:
                return candidate
            nonce += 1

    # ---------- 조회 ----------

    def get_commit(self, commit_hash: str) -> Commit:
        """hash로 커밋을 찾는다. 없으면 Unknown commit 에러."""
        if commit_hash not in self.commits:
            raise MiniGitError(f"Unknown commit: {commit_hash}")
        return self.commits[commit_hash]

    def log(self, sort_by: str | None = None) -> list[Commit]:
        """커밋 목록을 반환한다.

        - sort_by가 없으면 위상 정렬 순서 (부모가 항상 자식보다 먼저)
        - 'date'  : timestamp 오름차순, 같으면 생성 순번(seq)
        - 'author': 작성자 이름 오름차순, 같으면 위상 정렬 순서 유지 (merge_sort가 안정 정렬)
        """
        self._require_init()
        ordered = [self.commits[h] for h in graph.topological_sort(self.commits)]
        if sort_by is None:
            return ordered
        if sort_by == "date":
            return merge_sort(ordered, key=lambda c: (c.timestamp, c.seq))
        if sort_by == "author":
            return merge_sort(ordered, key=lambda c: c.author.lower())
        raise MiniGitError("Invalid args")

    def path(self, start: str, end: str) -> list[str] | None:
        """두 커밋 사이의 최단 경로 (무방향, 사전순 최소). 없으면 None."""
        self._require_init()
        self.get_commit(start)
        self.get_commit(end)
        return graph.shortest_path(self.commits, start, end)

    def ancestors(self, commit_hash: str) -> list[Commit]:
        """해당 커밋의 모든 조상 커밋 (가까운 순)."""
        self._require_init()
        self.get_commit(commit_hash)
        return [self.commits[h] for h in graph.find_ancestors(self.commits, commit_hash)]

    def search_keyword(self, keyword: str) -> list[Commit]:
        """역색인으로 키워드가 포함된 커밋을 찾는다."""
        self._require_init()
        return [self.commits[h] for h in self.index.search_keyword(keyword)]

    def search_author(self, author: str) -> list[Commit]:
        """역색인으로 작성자의 커밋을 찾는다."""
        self._require_init()
        return [self.commits[h] for h in self.index.search_author(author)]

    def _require_init(self) -> None:
        if not self.initialized:
            raise MiniGitError("Not initialized. Use INIT <user_name> first")
