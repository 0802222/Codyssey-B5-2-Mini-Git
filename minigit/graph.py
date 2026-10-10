"""커밋 그래프 탐색 알고리즘.

그래프는 dict[str, Commit] (hash -> Commit) 형태로 받는다.
각 커밋은 parents 목록으로 부모를 가리키므로 간선 방향은 '자식 -> 부모'이다.
부모는 항상 자식보다 먼저 만들어지기 때문에 사이클이 생길 수 없다 → DAG.
"""

from collections import deque

from .commit import Commit

Graph = dict[str, Commit]


def build_children(graph: Graph) -> dict[str, list[str]]:
    """parents 정보를 뒤집어 '부모 -> 자식 목록' 맵을 만든다. 자식은 생성 순서대로 들어간다."""
    children: dict[str, list[str]] = {h: [] for h in graph}
    for commit in graph.values():
        for parent in commit.parents:
            children[parent].append(commit.hash)
    return children


def topological_sort(graph: Graph) -> list[str]:
    """부모 커밋이 항상 자식 커밋보다 먼저 나오도록 커밋 hash를 나열한다 (Kahn 알고리즘).

    1. 각 커밋의 진입 차수 = 아직 출력되지 않은 부모 수 (처음엔 len(parents))
    2. 진입 차수가 0인 커밋(부모가 없는 루트)을 큐에 넣는다.
    3. 큐에서 하나 꺼내 출력하고, 그 자식들의 진입 차수를 1씩 줄인다.
       0이 된 자식은 '모든 부모가 출력됨'이므로 큐에 넣는다.
    4. 큐가 빌 때까지 반복. 출력 개수가 전체보다 적으면 사이클이 있다는 뜻이다.

    시간복잡도: O(V + E) (V = 커밋 수, E = 부모 연결 수)
    """
    children = build_children(graph)
    indegree = {h: len(c.parents) for h, c in graph.items()}
    queue = deque(h for h in graph if indegree[h] == 0)
    order = []
    while queue:
        current = queue.popleft()
        order.append(current)
        for child in children[current]:
            indegree[child] -= 1
            if indegree[child] == 0:
                queue.append(child)
    if len(order) != len(graph):
        raise ValueError("Commit graph has a cycle")
    return order


def _undirected_neighbors(graph: Graph) -> dict[str, list[str]]:
    """부모/자식 연결을 무방향 간선으로 본 인접 리스트를 만든다."""
    neighbors: dict[str, list[str]] = {h: [] for h in graph}
    for commit in graph.values():
        for parent in commit.parents:
            neighbors[commit.hash].append(parent)
            neighbors[parent].append(commit.hash)
    return neighbors


def _bfs_distances(neighbors: dict[str, list[str]], start: str) -> dict[str, int]:
    """start에서 각 노드까지의 최단 거리(간선 수)를 BFS로 구한다."""
    dist = {start: 0}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for nxt in neighbors[current]:
            if nxt not in dist:
                dist[nxt] = dist[current] + 1
                queue.append(nxt)
    return dist


def shortest_path(graph: Graph, start: str, end: str) -> list[str] | None:
    """두 커밋 사이의 최단 경로를 반환한다. 경로가 없으면 None.

    - 커밋-부모 연결을 무방향 간선으로 보고, 간선 수가 가장 적은 경로를 찾는다.
    - 최단 경로가 여러 개면 'h1->h2->...' 문자열이 사전순으로 가장 작은 경로를 고른다.

    방법:
    1. end에서 BFS를 돌려 모든 노드의 'end까지 남은 거리'를 구한다.
    2. start에서 출발해, 매 단계 '남은 거리가 정확히 1 줄어드는' 이웃 중
       hash가 사전순으로 가장 작은 것을 고른다(그리디).
    hash가 모두 같은 길이라서 경로 문자열의 사전순 비교는 앞에서부터 hash를 하나씩
    비교하는 것과 같다. 따라서 매 단계 가장 작은 hash를 고르면 전체 경로도 사전순 최소가 된다.

    시간복잡도: O(V + E)
    """
    neighbors = _undirected_neighbors(graph)
    dist_to_end = _bfs_distances(neighbors, end)
    if start not in dist_to_end:
        return None
    path = [start]
    current = start
    while current != end:
        best = None
        for nxt in neighbors[current]:
            if dist_to_end.get(nxt) == dist_to_end[current] - 1:
                if best is None or nxt < best:
                    best = nxt
        current = best
        path.append(current)
    return path


def find_ancestors(graph: Graph, commit_hash: str) -> list[str]:
    """commit_hash에서 parents를 따라 도달 가능한 모든 조상 커밋을 반환한다 (BFS).

    visited 집합으로 이미 방문한 커밋은 다시 넣지 않으므로, merge로 인해
    같은 조상에 여러 경로로 도달해도 한 번만 출력된다. 가까운 조상부터 나온다.
    자기 자신은 포함하지 않는다.

    시간복잡도: O(V + E)
    """
    visited = {commit_hash}
    queue = deque([commit_hash])
    ancestors = []
    while queue:
        current = queue.popleft()
        for parent in graph[current].parents:
            if parent not in visited:
                visited.add(parent)
                ancestors.append(parent)
                queue.append(parent)
    return ancestors


def is_ancestor(graph: Graph, ancestor: str, descendant: str) -> bool:
    """ancestor가 descendant 자신이거나 그 조상이면 True."""
    return ancestor == descendant or ancestor in find_ancestors(graph, descendant)
