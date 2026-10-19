"""정렬 알고리즘 직접 구현 (파이썬 내장 sorted 함수와 list의 sort 메서드는 사용하지 않는다).

모든 함수는 key 함수를 받아 비교 기준을 바꿀 수 있다.
예) merge_sort(commits, key=lambda c: c.author)

| 알고리즘        | 평균        | 최악        | 안정 정렬 |
|----------------|------------|------------|----------|
| merge_sort     | O(N log N) | O(N log N) | O        |
| quick_sort     | O(N log N) | O(N^2)     | X        |
| insertion_sort | O(N^2)     | O(N^2)     | O        |

LOG --sort-by 에는 merge_sort를 사용한다. 최악에도 O(N log N)이고,
안정 정렬이라 기준값이 같은 커밋은 원래 순서(위상 정렬 순서)가 그대로 유지된다.
"""

from typing import Callable, TypeVar  # 타입 힌트용 도구

T = TypeVar("T")  # 아무 타입이나 올 수 있다는 뜻의 타입 변수


def _identity(x):
    return x  # 받은 값을 그대로 돌려준다 (key를 안 주면 값 자체로 비교)


def merge_sort(items: list[T], key: Callable[[T], object] = _identity) -> list[T]:
    """병합 정렬. 원본은 바꾸지 않고 정렬된 새 리스트를 반환한다.

    리스트를 반으로 나눠 각각 재귀적으로 정렬한 뒤, 두 정렬된 리스트를 앞에서부터
    비교하며 합친다. 값이 같으면 왼쪽 원소를 먼저 넣으므로 안정 정렬이다.
    """
    if len(items) <= 1:  # 원소가 0~1개면 이미 정렬된 상태
        return list(items)  # 복사본 반환
    mid = len(items) // 2  # 가운데 위치
    left = merge_sort(items[:mid], key)  # 왼쪽 절반을 정렬
    right = merge_sort(items[mid:], key)  # 오른쪽 절반을 정렬
    return _merge(left, right, key)  # 정렬된 두 절반을 합친다


def _merge(left: list[T], right: list[T], key: Callable[[T], object]) -> list[T]:
    """정렬된 두 리스트를 하나의 정렬된 리스트로 합친다."""
    merged = []  # 합친 결과
    i = j = 0  # left, right에서 다음에 볼 위치
    while i < len(left) and j < len(right):  # 양쪽 다 남아 있는 동안
        # '<=' 이기 때문에 같은 값이면 왼쪽(원래 앞에 있던 원소)이 먼저 들어간다 → 안정성
        if key(left[i]) <= key(right[j]):  # 왼쪽 값이 작거나 같으면
            merged.append(left[i])  # 왼쪽 원소를 넣고
            i += 1  # 왼쪽 다음 칸으로
        else:  # 오른쪽 값이 더 작으면
            merged.append(right[j])  # 오른쪽 원소를 넣고
            j += 1  # 오른쪽 다음 칸으로
    merged.extend(left[i:])  # 왼쪽에 남은 원소를 그대로 붙인다
    merged.extend(right[j:])  # 오른쪽에 남은 원소를 그대로 붙인다
    return merged  # 합친 결과 반환


def quick_sort(items: list[T], key: Callable[[T], object] = _identity) -> list[T]:
    """퀵 정렬. 가운데 원소를 피벗으로 작은 값/같은 값/큰 값 세 그룹으로 나눠 재귀 정렬한다.

    피벗이 계속 최솟값/최댓값으로 뽑히면 O(N^2)까지 느려진다.
    (이 구현은 3분할 방식이라 실제로는 순서가 유지되지만, 일반적인 제자리(in-place)
    퀵 정렬은 원소 교환 과정에서 순서가 섞이므로 불안정 정렬로 분류한다.)
    """
    if len(items) <= 1:  # 원소가 0~1개면 이미 정렬된 상태
        return list(items)  # 복사본 반환
    pivot = key(items[len(items) // 2])  # 가운데 원소의 기준값을 피벗으로
    less, equal, greater = [], [], []  # 피벗보다 작은/같은/큰 그룹
    for item in items:  # 원소마다
        k = key(item)  # 비교 기준값
        if k < pivot:  # 피벗보다 작으면
            less.append(item)  # 작은 그룹
        elif k > pivot:  # 피벗보다 크면
            greater.append(item)  # 큰 그룹
        else:  # 같으면
            equal.append(item)  # 같은 그룹
    return quick_sort(less, key) + equal + quick_sort(greater, key)  # 작은 그룹 정렬 + 같은 그룹 + 큰 그룹 정렬


def insertion_sort(items: list[T], key: Callable[[T], object] = _identity) -> list[T]:
    """삽입 정렬. 앞쪽의 정렬된 구간에 원소를 하나씩 알맞은 위치로 끼워 넣는다.

    거의 정렬된 입력에서는 O(N)으로 빠르지만, 평균/최악은 O(N^2)이다.
    자신보다 '큰' 원소만 뒤로 밀기 때문에 안정 정렬이다.
    """
    result = list(items)  # 원본을 지키려고 복사본에서 작업
    for i in range(1, len(result)):  # 두 번째 원소부터 하나씩
        current = result[i]  # 이번에 끼워 넣을 원소
        current_key = key(current)  # 그 원소의 기준값
        j = i - 1  # 바로 앞 칸부터 비교
        while j >= 0 and key(result[j]) > current_key:  # 앞 원소가 더 크면
            result[j + 1] = result[j]  # 그 원소를 한 칸 뒤로 민다
            j -= 1  # 한 칸 더 앞으로
        result[j + 1] = current  # 빈 자리에 원소를 넣는다
    return result  # 정렬된 리스트 반환
