"""두 텍스트 파일을 줄 단위로 비교 (보너스).

LCS(최장 공통 부분 수열)를 동적 계획법으로 구한 뒤,
공통 줄은 '  ', 첫 파일에만 있는 줄은 '- ', 둘째 파일에만 있는 줄은 '+ '로 표시한다.
시간/공간 복잡도: O(N * M)
"""


def diff_lines(a: list[str], b: list[str]) -> list[str]:
    """두 줄 목록의 차이를 '  공통', '- 삭제', '+ 추가' 형식의 줄 목록으로 반환한다."""
    n, m = len(a), len(b)  # 두 목록의 줄 수
    # lcs[i][j] = a[i:]와 b[j:]의 최장 공통 부분 수열 길이
    lcs = [[0] * (m + 1) for _ in range(n + 1)]  # (n+1) x (m+1) 표를 0으로 채운다
    for i in range(n - 1, -1, -1):  # a의 뒤에서부터 앞으로
        for j in range(m - 1, -1, -1):  # b의 뒤에서부터 앞으로
            if a[i] == b[j]:  # 두 줄이 같으면
                lcs[i][j] = lcs[i + 1][j + 1] + 1  # 둘 다 한 칸 뒤의 값 + 1
            else:  # 다르면
                lcs[i][j] = max(lcs[i + 1][j], lcs[i][j + 1])  # a를 건너뛴 값, b를 건너뛴 값 중 큰 것

    result = []  # diff 결과 줄 목록
    i = j = 0  # a, b를 가리키는 위치 (앞에서부터)
    while i < n and j < m:  # 둘 다 남은 줄이 있는 동안
        if a[i] == b[j]:  # 같은 줄이면
            result.append(f"  {a[i]}")  # 공통 줄로 표시
            i += 1  # a 다음 줄로
            j += 1  # b 다음 줄로
        elif lcs[i + 1][j] >= lcs[i][j + 1]:  # a 줄을 버리는 쪽이 손해가 없으면
            result.append(f"- {a[i]}")  # 삭제된 줄로 표시
            i += 1  # a만 다음 줄로
        else:  # b 줄을 버리는 쪽이 낫다면
            result.append(f"+ {b[j]}")  # 추가된 줄로 표시
            j += 1  # b만 다음 줄로
    result.extend(f"- {line}" for line in a[i:])  # a에 남은 줄은 모두 삭제
    result.extend(f"+ {line}" for line in b[j:])  # b에 남은 줄은 모두 추가
    return result  # 완성된 diff 반환


def diff_files(path1: str, path2: str) -> list[str]:
    """두 파일을 읽어 diff_lines 결과를 반환한다."""
    with open(path1, encoding="utf-8") as f1, open(path2, encoding="utf-8") as f2:  # 두 파일을 UTF-8로 연다
        return diff_lines(f1.read().splitlines(), f2.read().splitlines())  # 줄 단위로 쪼개서 비교
