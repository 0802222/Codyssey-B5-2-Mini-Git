"""역색인(Inverted Index).

일반 검색은 모든 커밋을 돌면서 메시지를 확인해야 하므로 O(N * L)이 걸린다.
역색인은 커밋을 만들 때 미리 '단어 -> 커밋 목록'을 기록해 두기 때문에,
검색할 때는 딕셔너리 조회 한 번(평균 O(1))으로 후보 목록을 바로 얻는다.
"""


def tokenize(text: str) -> list[str]:
    """문자열을 공백 기준으로 나누고 소문자로 정규화한 토큰 목록을 반환한다."""
    return [token.lower() for token in text.split()]


class InvertedIndex:
    """key -> commit_hash 목록 형태의 역색인.

    같은 커밋이 한 key에 두 번 들어가지 않도록 set으로 중복을 확인하고,
    결과는 커밋이 추가된 순서(=생성 순서)를 유지하도록 list에 저장한다.
    """

    def __init__(self) -> None:
        self._postings: dict[str, list[str]] = {}
        self._seen: dict[str, set[str]] = {}

    def add(self, key: str, commit_hash: str) -> None:
        """key에 commit_hash를 등록한다. key는 소문자로 정규화한다."""
        key = key.lower()
        if key not in self._postings:
            self._postings[key] = []
            self._seen[key] = set()
        if commit_hash not in self._seen[key]:
            self._postings[key].append(commit_hash)
            self._seen[key].add(commit_hash)

    def get(self, key: str) -> list[str]:
        """key에 등록된 commit_hash 목록을 반환한다. 없으면 빈 목록."""
        return list(self._postings.get(key.lower(), []))

    def keys(self) -> list[str]:
        """등록된 key 목록을 반환한다."""
        return list(self._postings)


class SearchIndex:
    """커밋 검색용 역색인 묶음: keyword 인덱스 + author 인덱스."""

    def __init__(self) -> None:
        self.keyword_index = InvertedIndex()
        self.author_index = InvertedIndex()

    def add_commit(self, commit_hash: str, message: str, author: str) -> None:
        """새 커밋을 두 인덱스에 모두 등록한다."""
        for token in tokenize(message):
            self.keyword_index.add(token, commit_hash)
        self.author_index.add(author, commit_hash)

    def search_keyword(self, keyword: str) -> list[str]:
        """키워드를 포함하는 커밋 hash 목록을 반환한다.

        키워드가 여러 단어("add login")이면 모든 단어를 포함하는 커밋만 남긴다(AND 검색).
        첫 단어의 후보 목록에서 출발해 나머지 단어의 후보 집합과 교집합을 구한다.
        """
        tokens = tokenize(keyword)
        if not tokens:
            return []
        result = self.keyword_index.get(tokens[0])
        for token in tokens[1:]:
            others = set(self.keyword_index.get(token))
            result = [h for h in result if h in others]
        return result

    def search_author(self, author: str) -> list[str]:
        """해당 작성자의 커밋 hash 목록을 반환한다. 대소문자는 구분하지 않는다."""
        return self.author_index.get(author)
