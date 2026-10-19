"""커밋 노드 정의."""

from dataclasses import dataclass, field  # 데이터 담는 클래스를 짧게 만들어 주는 도구
from datetime import datetime  # 날짜/시각 타입

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"  # 시각 출력 형식 (예: 2024-01-15 09:00:00)


@dataclass  # __init__ 등을 자동으로 만들어 준다
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

    hash: str  # 커밋 고유 번호 (7자리)
    message: str  # 커밋 메시지
    author: str  # 작성자
    timestamp: datetime  # 만든 시각
    parents: list[str] = field(default_factory=list)  # 부모 hash 목록 (커밋마다 새 빈 리스트)
    branch: str = ""  # 만들어질 때의 브랜치 이름
    seq: int = 0  # 생성 순번

    def time_str(self) -> str:
        """timestamp를 'YYYY-MM-DD HH:MM:SS' 형식 문자열로 반환한다."""
        return self.timestamp.strftime(TIME_FORMAT)  # 시각을 정해진 형식의 글자로 바꾼다
