"""역색인(Inverted Index).

일반 검색은 모든 커밋을 돌면서 메시지를 확인해야 하므로 O(N * L)이 걸린다.
역색인은 커밋을 만들 때 미리 '단어 -> 커밋 목록'을 기록해 두기 때문에,
검색할 때는 딕셔너리 조회 한 번(평균 O(1))으로 후보 목록을 바로 얻는다.
"""


def tokenize(text: str) -> list[str]:
    """문자열을 공백 기준으로 나누고 소문자로 정규화한 토큰 목록을 반환한다."""
    return [token.lower() for token in text.split()]  # 공백으로 자르고 전부 소문자로


class InvertedIndex:
    """key -> commit_hash 목록 형태의 역색인.

    같은 커밋이 한 key에 두 번 들어가지 않도록 set으로 중복을 확인하고,
    결과는 커밋이 추가된 순서(=생성 순서)를 유지하도록 list에 저장한다.
    """

    def __init__(self) -> None:
        self._postings: dict[str, list[str]] = {}  # key -> 커밋 hash 목록 (순서 유지)
        self._seen: dict[str, set[str]] = {}  # key -> 이미 넣은 hash 집합 (중복 확인용)

    def add(self, key: str, commit_hash: str) -> None:
        """key에 commit_hash를 등록한다. key는 소문자로 정규화한다."""
        key = key.lower()  # 대소문자 구분 없이 저장
        if key not in self._postings:  # 처음 보는 key면
            self._postings[key] = []  # 빈 목록 생성
            self._seen[key] = set()  # 빈 집합 생성
        if commit_hash not in self._seen[key]:  # 아직 등록 안 된 커밋이면
            self._postings[key].append(commit_hash)  # 목록에 추가
            self._seen[key].add(commit_hash)  # 등록했다고 표시

    def get(self, key: str) -> list[str]:
        """key에 등록된 commit_hash 목록을 반환한다. 없으면 빈 목록."""
        return list(self._postings.get(key.lower(), []))  # 복사본을 반환해 원본이 바뀌지 않게 한다

    def keys(self) -> list[str]:
        """등록된 key 목록을 반환한다."""
        return list(self._postings)  # 딕셔너리의 key만 리스트로


class SearchIndex:
    """커밋 검색용 역색인 묶음: keyword 인덱스 + author 인덱스."""

    def __init__(self) -> None:
        self.keyword_index = InvertedIndex()  # 단어 -> 커밋 목록
        self.author_index = InvertedIndex()  # 작성자 -> 커밋 목록

    def add_commit(self, commit_hash: str, message: str, author: str) -> None:
        """새 커밋을 두 인덱스에 모두 등록한다."""
        for token in tokenize(message):  # 메시지의 단어마다
            self.keyword_index.add(token, commit_hash)  # 단어 인덱스에 커밋 등록
        self.author_index.add(author, commit_hash)  # 작성자 인덱스에 커밋 등록

    def search_keyword(self, keyword: str) -> list[str]:
        """키워드를 포함하는 커밋 hash 목록을 반환한다.

        키워드가 여러 단어("add login")이면 모든 단어를 포함하는 커밋만 남긴다(AND 검색).
        첫 단어의 후보 목록에서 출발해 나머지 단어의 후보 집합과 교집합을 구한다.
        """
        tokens = tokenize(keyword)  # 검색어를 단어로 쪼갠다
        if not tokens:  # 단어가 하나도 없으면
            return []  # 결과 없음
        result = self.keyword_index.get(tokens[0])  # 첫 단어가 들어간 커밋들로 시작
        for token in tokens[1:]:  # 나머지 단어마다
            others = set(self.keyword_index.get(token))  # 그 단어가 들어간 커밋 집합
            result = [h for h in result if h in others]  # 양쪽에 다 있는 커밋만 남긴다 (순서 유지)
        return result  # 모든 단어를 포함한 커밋 목록 반환

    def search_author(self, author: str) -> list[str]:
        """해당 작성자의 커밋 hash 목록을 반환한다. 대소문자는 구분하지 않는다."""
        return self.author_index.get(author)  # 작성자 인덱스에서 바로 꺼낸다
