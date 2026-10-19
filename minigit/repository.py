"""저장소 상태 관리: 커밋 저장소, 브랜치, HEAD, 현재 사용자."""

import hashlib  # SHA-1 해시 함수 제공
from datetime import datetime  # 현재 시각을 얻는 데 사용

from . import graph  # 그래프 탐색 함수 모음
from .commit import Commit  # 커밋 노드 타입
from .index import SearchIndex  # 검색용 역색인
from .sorting import merge_sort  # 직접 만든 병합 정렬

HASH_LENGTH = 7  # 커밋 hash 길이 (7자리)


class MiniGitError(Exception):
    """사용자에게 그대로 보여줄 에러 메시지를 담는 예외."""


class Repository:
    """메모리 위에서 동작하는 Mini Git 저장소.

    - commits: hash -> Commit 해시맵. hash로 커밋을 평균 O(1)에 찾는다.
    - branches: 브랜치 이름 -> 그 브랜치가 가리키는 커밋 hash (커밋이 없으면 None)
    - head: 현재 체크아웃된 브랜치 이름 (HEAD는 브랜치를 가리키고, 브랜치가 커밋을 가리킨다)
    """

    def __init__(self) -> None:
        self.initialized = False  # INIT을 했는지 여부
        self.user = ""  # 현재 사용자 이름
        self.commits: dict[str, Commit] = {}  # hash -> 커밋 저장소
        self.branches: dict[str, str | None] = {}  # 브랜치 이름 -> 커밋 hash
        self.head = ""  # 현재 브랜치 이름
        self.index = SearchIndex()  # 검색용 역색인
        self._counter = 0  # 지금까지 만든 커밋 수 (순번용)

    # ---------- 저장소 / 브랜치 ----------

    def init(self, user: str) -> bool:
        """저장소를 초기화하고 main 브랜치를 만든 뒤 HEAD와 사용자를 설정한다.

        이미 초기화된 저장소라면 커밋 이력은 그대로 두고 현재 사용자만 바꾼다
        (여러 작성자의 커밋을 만들어 SEARCH --author, LOG --sort-by=author를 확인하기 위함).
        새로 초기화했으면 True, 사용자만 바꿨으면 False를 반환한다.
        """
        if self.initialized:  # 이미 초기화했다면
            self.user = user  # 사용자만 바꾸고
            return False  # 재초기화라고 알린다
        self.initialized = True  # 초기화 완료 표시
        self.user = user  # 사용자 설정
        self.branches = {"main": None}  # 커밋 없는 main 브랜치 생성
        self.head = "main"  # HEAD를 main으로
        return True  # 새로 초기화했다고 알린다

    def head_commit(self) -> str | None:
        """HEAD(현재 브랜치)가 가리키는 커밋 hash. 아직 커밋이 없으면 None."""
        return self.branches[self.head]  # 현재 브랜치가 가리키는 커밋

    def create_branch(self, name: str) -> None:
        """현재 HEAD 커밋을 가리키는 새 브랜치를 만든다."""
        self._require_init()  # INIT 안 했으면 에러
        if name in self.branches:  # 같은 이름이 이미 있으면
            raise MiniGitError(f"Branch already exists: {name}")  # 중복 에러
        if self.head_commit() is None:  # 커밋이 하나도 없으면
            raise MiniGitError("No commits yet")  # 가리킬 커밋이 없으니 에러
        self.branches[name] = self.head_commit()  # 새 브랜치가 현재 커밋을 가리키게 한다

    def list_branches(self) -> dict[str, str | None]:
        """브랜치 이름 -> 가리키는 커밋 hash 맵을 반환한다."""
        self._require_init()  # INIT 안 했으면 에러
        return dict(self.branches)  # 복사본 반환 (밖에서 바꿔도 원본 안전)

    def switch(self, name: str) -> None:
        """HEAD를 지정한 브랜치로 옮긴다."""
        self._require_init()  # INIT 안 했으면 에러
        if name not in self.branches:  # 없는 브랜치면
            raise MiniGitError(f"Unknown branch: {name}")  # 에러
        self.head = name  # HEAD를 그 브랜치로 이동

    # ---------- 커밋 ----------

    def commit(self, message: str) -> Commit:
        """현재 HEAD 커밋을 부모로 하는 새 커밋을 만든다."""
        self._require_init()  # INIT 안 했으면 에러
        parent = self.head_commit()  # 현재 커밋 = 새 커밋의 부모
        parents = [parent] if parent is not None else []  # 첫 커밋이면 부모 없음
        return self._create_commit(message, parents)  # 커밋 생성

    def merge(self, branch: str) -> Commit | None:
        """현재 브랜치에 대상 브랜치를 병합한다 (보너스).

        현재 HEAD와 대상 브랜치 HEAD를 부모로 갖는 merge 커밋을 만든다.
        대상 커밋이 이미 현재 커밋의 조상이면 병합할 게 없으므로 None을 반환한다.
        """
        self._require_init()  # INIT 안 했으면 에러
        if branch not in self.branches:  # 없는 브랜치면
            raise MiniGitError(f"Unknown branch: {branch}")  # 에러
        if branch == self.head:  # 자기 자신과 병합하려 하면
            raise MiniGitError("Cannot merge a branch into itself")  # 에러
        current = self.head_commit()  # 현재 브랜치의 커밋
        target = self.branches[branch]  # 대상 브랜치의 커밋
        if current is None or target is None:  # 둘 중 하나라도 커밋이 없으면
            raise MiniGitError("No commits yet")  # 에러
        if graph.is_ancestor(self.commits, target, current):  # 대상이 이미 내 조상이면
            return None  # 합칠 내용이 없다
        message = f"Merge branch '{branch}' into {self.head}"  # 병합 커밋 메시지
        return self._create_commit(message, [current, target])  # 부모가 2개인 커밋 생성

    def _create_commit(self, message: str, parents: list[str]) -> Commit:
        """커밋을 만들어 저장하고, 현재 브랜치를 앞으로 옮기고, 역색인을 갱신한다."""
        timestamp = datetime.now()  # 지금 시각
        commit_hash = self._new_hash(message, timestamp)  # 겹치지 않는 hash 생성
        self._counter += 1  # 커밋 순번 1 증가
        commit = Commit(  # 커밋 객체 생성
            hash=commit_hash,  # 고유 번호
            message=message,  # 메시지
            author=self.user,  # 작성자 = 현재 사용자
            timestamp=timestamp,  # 만든 시각
            parents=parents,  # 부모 목록
            branch=self.head,  # 현재 브랜치 이름
            seq=self._counter,  # 생성 순번
        )
        self.commits[commit_hash] = commit  # 저장소에 저장
        self.branches[self.head] = commit_hash  # 현재 브랜치를 새 커밋으로 옮긴다
        self.index.add_commit(commit_hash, message, self.user)  # 검색 인덱스에 등록
        return commit  # 만든 커밋 반환

    def _new_hash(self, message: str, timestamp: datetime) -> str:
        """세션 내 유일한 7자리 hash를 만든다.

        증가 카운터 + 메시지 + 작성자 + 시각을 SHA-1로 해싱해 앞 7자리를 쓴다.
        앞 7자리만 쓰면 아주 드물게 겹칠 수 있으므로, 이미 존재하는 hash면
        nonce를 올려 다시 해싱한다 → 중복이 절대 생기지 않음을 보장한다.
        """
        nonce = 0  # 겹칠 때마다 올리는 추가 숫자
        while True:  # 겹치지 않는 hash가 나올 때까지
            raw = f"{self._counter}|{nonce}|{message}|{self.user}|{timestamp.isoformat()}"  # 해싱할 원본 문자열
            candidate = hashlib.sha1(raw.encode()).hexdigest()[:HASH_LENGTH]  # SHA-1 결과의 앞 7자리
            if candidate not in self.commits:  # 아직 없는 hash면
                return candidate  # 그대로 사용
            nonce += 1  # 겹쳤으면 nonce를 올려 다시 시도

    # ---------- 조회 ----------

    def get_commit(self, commit_hash: str) -> Commit:
        """hash로 커밋을 찾는다. 없으면 Unknown commit 에러."""
        if commit_hash not in self.commits:  # 없는 hash면
            raise MiniGitError(f"Unknown commit: {commit_hash}")  # 에러
        return self.commits[commit_hash]  # 찾은 커밋 반환

    def log(self, sort_by: str | None = None) -> list[Commit]:
        """커밋 목록을 반환한다.

        - sort_by가 없으면 위상 정렬 순서 (부모가 항상 자식보다 먼저)
        - 'date'  : timestamp 오름차순, 같으면 생성 순번(seq)
        - 'author': 작성자 이름 오름차순, 같으면 위상 정렬 순서 유지 (merge_sort가 안정 정렬)
        """
        self._require_init()  # INIT 안 했으면 에러
        ordered = [self.commits[h] for h in graph.topological_sort(self.commits)]  # 부모 먼저 순서의 커밋 목록
        if sort_by is None:  # 정렬 옵션이 없으면
            return ordered  # 위상 정렬 순서 그대로
        if sort_by == "date":  # 날짜순이면
            return merge_sort(ordered, key=lambda c: (c.timestamp, c.seq))  # 시각, 같으면 순번으로 정렬
        if sort_by == "author":  # 작성자순이면
            return merge_sort(ordered, key=lambda c: c.author.lower())  # 이름(소문자 기준)으로 정렬
        raise MiniGitError("Invalid args")  # 그 밖의 옵션은 에러

    def path(self, start: str, end: str) -> list[str] | None:
        """두 커밋 사이의 최단 경로 (무방향, 사전순 최소). 없으면 None."""
        self._require_init()  # INIT 안 했으면 에러
        self.get_commit(start)  # 시작 커밋이 있는지 확인
        self.get_commit(end)  # 끝 커밋이 있는지 확인
        return graph.shortest_path(self.commits, start, end)  # 최단 경로 계산

    def ancestors(self, commit_hash: str) -> list[Commit]:
        """해당 커밋의 모든 조상 커밋 (가까운 순)."""
        self._require_init()  # INIT 안 했으면 에러
        self.get_commit(commit_hash)  # 커밋이 있는지 확인
        return [self.commits[h] for h in graph.find_ancestors(self.commits, commit_hash)]  # 조상 hash를 커밋 객체로 바꿔 반환

    def search_keyword(self, keyword: str) -> list[Commit]:
        """역색인으로 키워드가 포함된 커밋을 찾는다."""
        self._require_init()  # INIT 안 했으면 에러
        return [self.commits[h] for h in self.index.search_keyword(keyword)]  # 찾은 hash를 커밋 객체로 변환

    def search_author(self, author: str) -> list[Commit]:
        """역색인으로 작성자의 커밋을 찾는다."""
        self._require_init()  # INIT 안 했으면 에러
        return [self.commits[h] for h in self.index.search_author(author)]  # 찾은 hash를 커밋 객체로 변환

    def _require_init(self) -> None:
        if not self.initialized:  # 아직 INIT을 안 했으면
            raise MiniGitError("Not initialized. Use INIT <user_name> first")  # 먼저 INIT 하라는 에러
