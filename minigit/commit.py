"""커밋 노드 정의."""

from dataclasses import dataclass, field
from datetime import datetime

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


@dataclass
class Commit:
    """커밋 그래프의 노드 하나.

    Attributes:
        hash: 세션 내에서 유일한 커밋 식별자 (7자리 16진수 문자열)
        message: 커밋 메시지
        author: 작성자 이름
        timestamp: 생성 시각
        parents: 부모 커밋 hash 목록 (최초 커밋은 0개, 일반 커밋 1개, merge 커밋 2개)
        branch: 커밋이 만들어질 당시의 브랜치 이름 (LOG 출력용)
        seq: 생성 순번. timestamp가 같을 때 순서를 구분하는 데 쓴다.
    """

    hash: str
    message: str
    author: str
    timestamp: datetime
    parents: list[str] = field(default_factory=list)
    branch: str = ""
    seq: int = 0

    def time_str(self) -> str:
        """timestamp를 'YYYY-MM-DD HH:MM:SS' 형식 문자열로 반환한다."""
        return self.timestamp.strftime(TIME_FORMAT)
