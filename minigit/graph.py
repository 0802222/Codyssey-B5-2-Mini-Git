"""커밋 그래프 탐색 알고리즘.

그래프는 dict[str, Commit] (hash -> Commit) 형태로 받는다.
각 커밋은 parents 목록으로 부모를 가리키므로 간선 방향은 '자식 -> 부모'이다.
부모는 항상 자식보다 먼저 만들어지기 때문에 사이클이 생길 수 없다 → DAG.
"""

from collections import deque  # 앞뒤로 빠르게 넣고 빼는 큐 (BFS용)

from .commit import Commit  # 커밋 노드 타입

Graph = dict[str, Commit]  # 타입 별명: hash -> Commit 딕셔너리


def build_children(graph: Graph) -> dict[str, list[str]]:
    """parents 정보를 뒤집어 '부모 -> 자식 목록' 맵을 만든다. 자식은 생성 순서대로 들어간다."""
    children: dict[str, list[str]] = {h: [] for h in graph}  # 모든 커밋에 빈 자식 목록 준비
    for commit in graph.values():  # 커밋마다
        for parent in commit.parents:  # 그 커밋의 부모마다
            children[parent].append(commit.hash)  # 부모의 자식 목록에 나를 추가
    return children  # 부모 -> 자식 맵 반환


def topological_sort(graph: Graph) -> list[str]:
    """부모 커밋이 항상 자식 커밋보다 먼저 나오도록 커밋 hash를 나열한다 (Kahn 알고리즘).

    1. 각 커밋의 진입 차수 = 아직 출력되지 않은 부모 수 (처음엔 len(parents))
    2. 진입 차수가 0인 커밋(부모가 없는 루트)을 큐에 넣는다.
    3. 큐에서 하나 꺼내 출력하고, 그 자식들의 진입 차수를 1씩 줄인다.
       0이 된 자식은 '모든 부모가 출력됨'이므로 큐에 넣는다.
    4. 큐가 빌 때까지 반복. 출력 개수가 전체보다 적으면 사이클이 있다는 뜻이다.

    시간복잡도: O(V + E) (V = 커밋 수, E = 부모 연결 수)
    """
    children = build_children(graph)  # 부모 -> 자식 맵
    indegree = {h: len(c.parents) for h, c in graph.items()}  # 커밋별 남은 부모 수
    queue = deque(h for h in graph if indegree[h] == 0)  # 부모 없는 커밋부터 큐에 넣는다
    order = []  # 결과 순서
    while queue:  # 큐가 빌 때까지
        current = queue.popleft()  # 맨 앞 커밋을 꺼낸다
        order.append(current)  # 결과에 추가
        for child in children[current]:  # 그 커밋의 자식마다
            indegree[child] -= 1  # 부모 하나가 처리됐으니 1 감소
            if indegree[child] == 0:  # 부모가 전부 처리됐으면
                queue.append(child)  # 이제 자식을 내보낼 차례
    if len(order) != len(graph):  # 못 꺼낸 커밋이 있으면
        raise ValueError("Commit graph has a cycle")  # 사이클이 있다는 뜻 → 에러
    return order  # 부모가 먼저 나오는 순서 반환


def _undirected_neighbors(graph: Graph) -> dict[str, list[str]]:
    """부모/자식 연결을 무방향 간선으로 본 인접 리스트를 만든다."""
    neighbors: dict[str, list[str]] = {h: [] for h in graph}  # 모든 커밋에 빈 이웃 목록 준비
    for commit in graph.values():  # 커밋마다
        for parent in commit.parents:  # 부모마다
            neighbors[commit.hash].append(parent)  # 나 -> 부모 연결
            neighbors[parent].append(commit.hash)  # 부모 -> 나 연결 (양방향)
    return neighbors  # 이웃 목록 반환


def _bfs_distances(neighbors: dict[str, list[str]], start: str) -> dict[str, int]:
    """start에서 각 노드까지의 최단 거리(간선 수)를 BFS로 구한다."""
    dist = {start: 0}  # 시작점까지 거리는 0
    queue = deque([start])  # 시작점을 큐에 넣는다
    while queue:  # 큐가 빌 때까지
        current = queue.popleft()  # 가장 먼저 들어온 노드를 꺼낸다
        for nxt in neighbors[current]:  # 이웃마다
            if nxt not in dist:  # 처음 보는 노드면
                dist[nxt] = dist[current] + 1  # 거리 = 현재 거리 + 1
                queue.append(nxt)  # 나중에 그 이웃도 탐색
    return dist  # 노드별 거리 반환 (도달 못 한 노드는 없음)


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
    neighbors = _undirected_neighbors(graph)  # 양방향 이웃 목록
    dist_to_end = _bfs_distances(neighbors, end)  # 각 노드에서 end까지 남은 거리
    if start not in dist_to_end:  # start에서 end로 갈 수 없으면
        return None  # 경로 없음
    path = [start]  # 경로는 start에서 시작
    current = start  # 현재 위치
    while current != end:  # 도착할 때까지
        best = None  # 이번에 갈 다음 노드 후보
        for nxt in neighbors[current]:  # 이웃마다
            if dist_to_end.get(nxt) == dist_to_end[current] - 1:  # end에 한 걸음 가까워지는 이웃이면
                if best is None or nxt < best:  # 그중 hash가 사전순으로 가장 작으면
                    best = nxt  # 후보로 정한다
        current = best  # 고른 이웃으로 이동
        path.append(current)  # 경로에 추가
    return path  # 완성된 경로 반환


def find_ancestors(graph: Graph, commit_hash: str) -> list[str]:
    """commit_hash에서 parents를 따라 도달 가능한 모든 조상 커밋을 반환한다 (BFS).

    visited 집합으로 이미 방문한 커밋은 다시 넣지 않으므로, merge로 인해
    같은 조상에 여러 경로로 도달해도 한 번만 출력된다. 가까운 조상부터 나온다.
    자기 자신은 포함하지 않는다.

    시간복잡도: O(V + E)
    """
    visited = {commit_hash}  # 방문한 커밋 기록 (자기 자신 포함)
    queue = deque([commit_hash])  # 탐색 시작점
    ancestors = []  # 찾은 조상 목록
    while queue:  # 큐가 빌 때까지
        current = queue.popleft()  # 맨 앞 커밋을 꺼낸다
        for parent in graph[current].parents:  # 그 커밋의 부모마다
            if parent not in visited:  # 아직 안 본 부모면
                visited.add(parent)  # 방문 표시
                ancestors.append(parent)  # 조상 목록에 추가
                queue.append(parent)  # 그 부모의 부모도 탐색
    return ancestors  # 가까운 순서의 조상 목록 반환


def is_ancestor(graph: Graph, ancestor: str, descendant: str) -> bool:
    """ancestor가 descendant 자신이거나 그 조상이면 True."""
    return ancestor == descendant or ancestor in find_ancestors(graph, descendant)  # 같은 커밋이거나 조상 목록에 있으면 True
