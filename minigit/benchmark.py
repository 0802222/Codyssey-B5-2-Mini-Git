"""정렬 알고리즘 성능 비교 (보너스)."""

import random  # 테스트용 난수 데이터를 만드는 모듈
import time  # 실행 시간을 재는 모듈

from .sorting import insertion_sort, merge_sort, quick_sort  # 직접 만든 정렬 함수 3개

ALGORITHMS = {  # 이름 -> 정렬 함수 매핑 (표의 열 순서가 된다)
    "merge_sort": merge_sort,  # 병합 정렬
    "quick_sort": quick_sort,  # 퀵 정렬
    "insertion_sort": insertion_sort,  # 삽입 정렬
}
DEFAULT_ITEM_COUNTS = [100, 500, 1000, 2000]  # 원소 개수를 안 주면 쓰는 기본 입력 크기들


def run_benchmark(item_counts: list[int] | None = None, seed: int = 42) -> list[str]:
    """입력 크기별로 각 정렬 알고리즘의 실행 시간(ms)을 측정해 표 형태의 줄 목록으로 반환한다.

    모든 알고리즘에 같은 난수 데이터를 넣어 공정하게 비교한다.
    """
    item_counts = item_counts or DEFAULT_ITEM_COUNTS  # 원소 개수 목록이 비어 있으면 기본값 사용
    rng = random.Random(seed)  # seed 고정 → 실행할 때마다 같은 난수가 나온다
    header = f"{'items':>8}" + "".join(f"{name:>15}" for name in ALGORITHMS)  # 표 머리글 (오른쪽 정렬)
    lines = [header + "   (ms)"]  # 결과 줄 목록, 첫 줄은 머리글 + 단위
    for item_count in item_counts:  # 원소 개수마다 반복
        data = [rng.randint(0, item_count * 10) for _ in range(item_count)]  # item_count개짜리 난수 리스트 생성
        row = f"{item_count:>8}"  # 이 줄의 첫 칸은 원소 개수
        for func in ALGORITHMS.values():  # 정렬 함수마다 반복
            start = time.perf_counter()  # 시작 시각 기록 (정밀 타이머)
            func(data)  # 같은 데이터로 정렬 실행 (원본은 안 바뀜)
            elapsed = (time.perf_counter() - start) * 1000  # 걸린 시간을 초 → 밀리초로 변환
            row += f"{elapsed:>12.2f}"  # 소수 둘째 자리까지 칸에 맞춰 붙인다
        lines.append(row)  # 완성된 줄을 결과에 추가
    return lines  # 표 전체 줄 목록 반환
