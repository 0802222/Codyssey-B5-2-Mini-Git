"""두 텍스트 파일을 줄 단위로 비교 (보너스).

LCS(최장 공통 부분 수열)를 동적 계획법으로 구한 뒤,
공통 줄은 '  ', 첫 파일에만 있는 줄은 '- ', 둘째 파일에만 있는 줄은 '+ '로 표시한다.
시간/공간 복잡도: O(N * M)
"""


def diff_lines(a: list[str], b: list[str]) -> list[str]:
    """두 줄 목록의 차이를 '  공통', '- 삭제', '+ 추가' 형식의 줄 목록으로 반환한다."""
    n, m = len(a), len(b)
    # lcs[i][j] = a[i:]와 b[j:]의 최장 공통 부분 수열 길이
    lcs = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            if a[i] == b[j]:
                lcs[i][j] = lcs[i + 1][j + 1] + 1
            else:
                lcs[i][j] = max(lcs[i + 1][j], lcs[i][j + 1])

    result = []
    i = j = 0
    while i < n and j < m:
        if a[i] == b[j]:
            result.append(f"  {a[i]}")
            i += 1
            j += 1
        elif lcs[i + 1][j] >= lcs[i][j + 1]:
            result.append(f"- {a[i]}")
            i += 1
        else:
            result.append(f"+ {b[j]}")
            j += 1
    result.extend(f"- {line}" for line in a[i:])
    result.extend(f"+ {line}" for line in b[j:])
    return result


def diff_files(path1: str, path2: str) -> list[str]:
    """두 파일을 읽어 diff_lines 결과를 반환한다."""
    with open(path1, encoding="utf-8") as f1, open(path2, encoding="utf-8") as f2:
        return diff_lines(f1.read().splitlines(), f2.read().splitlines())
