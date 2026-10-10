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

from typing import Callable, TypeVar

T = TypeVar("T")


def _identity(x):
    return x


def merge_sort(items: list[T], key: Callable[[T], object] = _identity) -> list[T]:
    """병합 정렬. 원본은 바꾸지 않고 정렬된 새 리스트를 반환한다.

    리스트를 반으로 나눠 각각 재귀적으로 정렬한 뒤, 두 정렬된 리스트를 앞에서부터
    비교하며 합친다. 값이 같으면 왼쪽 원소를 먼저 넣으므로 안정 정렬이다.
    """
    if len(items) <= 1:
        return list(items)
    mid = len(items) // 2
    left = merge_sort(items[:mid], key)
    right = merge_sort(items[mid:], key)
    return _merge(left, right, key)


def _merge(left: list[T], right: list[T], key: Callable[[T], object]) -> list[T]:
    """정렬된 두 리스트를 하나의 정렬된 리스트로 합친다."""
    merged = []
    i = j = 0
    while i < len(left) and j < len(right):
        # '<=' 이기 때문에 같은 값이면 왼쪽(원래 앞에 있던 원소)이 먼저 들어간다 → 안정성
        if key(left[i]) <= key(right[j]):
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1
    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged


def quick_sort(items: list[T], key: Callable[[T], object] = _identity) -> list[T]:
    """퀵 정렬. 가운데 원소를 피벗으로 작은 값/같은 값/큰 값 세 그룹으로 나눠 재귀 정렬한다.

    피벗이 계속 최솟값/최댓값으로 뽑히면 O(N^2)까지 느려진다.
    (이 구현은 3분할 방식이라 실제로는 순서가 유지되지만, 일반적인 제자리(in-place)
    퀵 정렬은 원소 교환 과정에서 순서가 섞이므로 불안정 정렬로 분류한다.)
    """
    if len(items) <= 1:
        return list(items)
    pivot = key(items[len(items) // 2])
    less, equal, greater = [], [], []
    for item in items:
        k = key(item)
        if k < pivot:
            less.append(item)
        elif k > pivot:
            greater.append(item)
        else:
            equal.append(item)
    return quick_sort(less, key) + equal + quick_sort(greater, key)


def insertion_sort(items: list[T], key: Callable[[T], object] = _identity) -> list[T]:
    """삽입 정렬. 앞쪽의 정렬된 구간에 원소를 하나씩 알맞은 위치로 끼워 넣는다.

    거의 정렬된 입력에서는 O(N)으로 빠르지만, 평균/최악은 O(N^2)이다.
    자신보다 '큰' 원소만 뒤로 밀기 때문에 안정 정렬이다.
    """
    result = list(items)
    for i in range(1, len(result)):
        current = result[i]
        current_key = key(current)
        j = i - 1
        while j >= 0 and key(result[j]) > current_key:
            result[j + 1] = result[j]
            j -= 1
        result[j + 1] = current
    return result
