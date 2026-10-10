"""정렬 알고리즘 성능 비교 (보너스)."""

import random
import time

from .sorting import insertion_sort, merge_sort, quick_sort

ALGORITHMS = {
    "merge": merge_sort,
    "quick": quick_sort,
    "insertion": insertion_sort,
}
DEFAULT_SIZES = [100, 500, 1000, 2000]


def run_benchmark(sizes: list[int] | None = None, seed: int = 42) -> list[str]:
    """입력 크기별로 각 정렬 알고리즘의 실행 시간(ms)을 측정해 표 형태의 줄 목록으로 반환한다.

    모든 알고리즘에 같은 난수 데이터를 넣어 공정하게 비교한다.
    """
    sizes = sizes or DEFAULT_SIZES
    rng = random.Random(seed)
    header = f"{'size':>8}" + "".join(f"{name:>12}" for name in ALGORITHMS)
    lines = [header + "   (ms)"]
    for size in sizes:
        data = [rng.randint(0, size * 10) for _ in range(size)]
        row = f"{size:>8}"
        for func in ALGORITHMS.values():
            start = time.perf_counter()
            func(data)
            elapsed = (time.perf_counter() - start) * 1000
            row += f"{elapsed:>12.2f}"
        lines.append(row)
    return lines
