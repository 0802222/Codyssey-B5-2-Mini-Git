"""시연 자동화 스크립트. 실행: python demo.py  (장면마다 멈추려면 python demo.py --step)

main.py와 같은 MiniGitCLI에 명령을 차례로 넣고, 입력한 명령과 출력 결과를 그대로 보여 준다.
hash는 실행할 때마다 새로 만들어지므로, PATH / ANCESTORS에 쓸 hash는 저장소에서 찾아 넣는다.
"""

import os  # 파일 경로 합치기
import sys  # 파이썬 버전 확인, 실행 옵션 읽기
import tempfile  # DIFF 시연용 임시 폴더
import unittest  # 마지막에 단위 테스트 실행

if sys.version_info < (3, 10):  # 파이썬 버전이 3.10보다 낮으면
    sys.exit("Mini Git requires Python 3.10 or later.")  # main.py와 같은 안내 후 종료

# 버전 확인이 끝난 뒤에 가져온다 (3.10 문법을 쓰는 모듈이라서)
from minigit import graph  # noqa: E402
from minigit.cli import MiniGitCLI  # noqa: E402
from minigit.commit import Commit  # noqa: E402

STEP = "--step" in sys.argv  # --step 옵션이 있으면 장면마다 Enter를 기다린다
cli = MiniGitCLI()  # main.py가 쓰는 것과 같은 CLI 객체
scene_no = 0  # 지금 몇 번째 장면인지


def scene(title: str) -> None:
    """장면 제목을 출력한다. --step이면 Enter를 누를 때까지 기다린다."""
    global scene_no  # 바깥의 장면 번호를 바꾸기 위해
    scene_no += 1  # 장면 번호 1 증가
    if STEP and scene_no > 1:  # 두 번째 장면부터, --step일 때만
        input("\n(Enter를 누르면 다음 장면)")  # 사용자가 Enter를 누를 때까지 대기
    print(f"\n{'=' * 64}\n[{scene_no}] {title}\n{'=' * 64}")  # 구분선과 제목 출력


def run(line: str) -> list[str]:
    """명령 한 줄을 실행하고, 프롬프트와 함께 입력/출력을 화면에 보여 준다."""
    print(f"💾 mini-git> {line}")  # 실제 프로그램처럼 입력한 명령을 보여 준다
    out = cli.execute(line)  # main.py의 REPL과 같은 함수로 실행
    for text in out:  # 출력 줄마다
        print(text)  # 화면에 출력
    print()  # 명령어 출력이 끝난 뒤 빈 줄 추가
    return out  # 결과를 돌려준다 (필요할 때 확인용)


def check(text: str) -> None:
    """평가자가 눈여겨볼 확인 포인트를 출력한다."""
    print(f"  → 확인 : {text}")  # 들여쓰기해서 출력 결과와 구분
    print()  # 명령어 출력이 끝난 뒤 빈 줄 추가


def hash_of(message: str) -> str:
    """메시지로 커밋 hash를 찾는다 (hash가 실행마다 달라서 직접 찾아 넣는다)."""
    for commit in cli.repo.commits.values():  # 저장된 커밋마다
        if commit.message == message:  # 메시지가 같으면
            return commit.hash  # 그 커밋의 hash 반환
    raise KeyError(message)  # 없으면 시연 스크립트 오류


# ---------- 필수 기능 ----------

# ============================================================================
# 장면 1: INIT
# ============================================================================
scene("INIT : main 브랜치 생성, HEAD 설정, 현재 사용자 초기화")  # 장면 1
run('init "홍길동"')  # 저장소 만들기
run("branch")  # 브랜치 목록 보기
check("main 브랜치가 생기고 HEAD(*)가 main, 아직 커밋이 없어서 (no commits)")  # 확인 포인트

# ============================================================================
# 장면 2: COMMIT / BRANCH / SWITCH
# ============================================================================
scene("COMMIT / BRANCH / SWITCH : 커밋이 현재 브랜치에만 반영")  # 장면 2
run("branch")  # 커밋 전 브랜치 상태 보기
run('commit "1. Initial commit"')  # 첫 커밋

run("branch A_feature")  # A_feature 브랜치 만들기
run("branch")  # 새 브랜치가 같은 커밋을 가리키는지 보기
run("switch A_feature")  # A_feature로 이동

run('commit "2. Add login feature"')  # feature에 커밋

run("switch main")  # main으로 돌아오기

run('commit "3. Add payment feature"')  # main에 커밋

run("branch")  # 두 브랜치가 각자 다른 커밋을 가리키는지 보기
check("[A_feature ...], [main ...] 처럼 커밋이 HEAD가 가리키는 브랜치에만 붙음")  # 확인 포인트

# ============================================================================
# 장면 3: LOG
# ============================================================================
scene("LOG : 부모 커밋이 항상 자식보다 먼저")  # 장면 3
run("log")  # 위상 정렬 순서로 출력
check("시각이 같아도 부모 Initial commit이 가장 먼저 (위상 정렬)")  # 확인 포인트

# ============================================================================
# 장면 4: PATH
# ============================================================================
scene("PATH : 무방향 최단 경로 / 경로가 없을 때")  # 장면 4
run("log")  # 커밋 순서 확인

login, payment = hash_of("2. Add login feature"), hash_of("3. Add payment feature")  # 형제 커밋 두 개의 hash
run(f"path {login} {payment}")  # 형제 커밋 사이 경로
check("형제 커밋은 공통 부모를 거쳐 2칸 (방향을 무시하고 연결)")  # 확인 포인트

run(f"path {login} zzzzzzz")  # 없는 hash
check("없는 커밋은 No path가 아니라 Unknown commit")  # 확인 포인트
# CLI에서는 모든 커밋이 첫 커밋과 이어져서 No path 상황을 만들 수 없다 → 끊어진 그래프로 같은 함수를 직접 호출
alone = {  # 서로 연결되지 않은 커밋 두 개짜리 그래프
    "aaaaaaa": Commit("aaaaaaa", "root A", "홍길동", cli.repo.commits[login].timestamp),  # 첫 번째 뿌리
    "bbbbbbb": Commit("bbbbbbb", "root B", "홍길동", cli.repo.commits[login].timestamp),  # 두 번째 뿌리
}
result = graph.shortest_path(alone, "aaaaaaa", "bbbbbbb")  # PATH가 쓰는 함수 그대로 호출
print("(끊어진 그래프에서 graph.shortest_path 호출)")  # 무엇을 했는지 표시
print("No path" if result is None else "Path: " + " -> ".join(result))  # cmd_path와 같은 규칙으로 출력
check("첫 커밋 말고는 모두 부모가 있어서 CLI에선 항상 연결됨, 끊어진 그래프에서는 No path")  # 확인 포인트

# ============================================================================
# 장면 5: SEARCH / LOG --sort-by
# ============================================================================
scene("SEARCH / SEARCH --author / LOG --sort-by")  # 장면 5
run('init "아무개"')  # 작성자를 아무개로 바꾸기 (기록은 유지)
run('commit "4. Fix login bug"')  # 아무개의 커밋
run('search "LOGIN"')  # 대소문자 다르게 검색

run('search "add login"')  # 두 단어 모두 들어간 커밋

run('search "log"')  # 단어 단위라 login을 찾지 않음

run("search --author=아무개")  # 작성자 검색

run("log --sort-by=author")  # 작성자 정렬

run("log --sort-by=date")  # 날짜 정렬
check("대소문자 무시, 여러 단어는 AND, 단어 단위 일치, 같은 작성자 안에서는 원래 순서 유지")  # 확인 포인트

# ============================================================================
# 장면 6: 예외 처리
# ============================================================================
scene("예외 처리 : 잘못된 입력에도 프로그램이 멈추지 않음")  # 장면 6
for bad in ["commit", "commit Add login", 'commit "unclosed', "log --sort-by=size",  # 인자 오류들
            "switch nope", "branch main", "hello"]:  # 없는 브랜치, 중복 브랜치, 없는 명령어
    run(bad)  # 하나씩 실행
check("모든 에러가 메시지만 출력하고 다음 입력으로 넘어감")  # 확인 포인트

# ---------- 보너스 ----------

# ============================================================================
# 장면 7: MERGE
# ============================================================================
scene("[보너스] MERGE : 부모가 2개인 커밋")  # 장면 7
run("merge A_feature")  # A_feature를 main에 합치기
run("log")  # Merge: 부모1 부모2 표시 확인
merge = cli.repo.head_commit()  # 방금 만든 merge 커밋 hash
run(f"ancestors {merge}")  # merge 커밋의 조상
run(f"path {login} {hash_of('4. Fix login bug')}")  # merge 뒤에 짧아진 경로
run("merge A_feature")  # 한 번 더 합치기
run("merge main")  # 자기 자신과 합치기
check("Initial commit은 두 갈래로 닿지만 조상 목록에 한 번만, 이미 합쳤으면 Already up to date.")  # 확인 포인트

# ============================================================================
# 장면 8: DIFF
# ============================================================================
scene("[보너스] DIFF : 두 파일 줄 단위 비교")  # 장면 8
with tempfile.TemporaryDirectory() as tmp:  # 시연이 끝나면 지워지는 임시 폴더
    a_path, b_path = os.path.join(tmp, "a.txt"), os.path.join(tmp, "b.txt")  # 비교할 파일 두 개
    with open(a_path, "w", encoding="utf-8") as f:  # 첫 파일 쓰기
        f.write("apple\nbanana\ncherry\n")  # 첫 파일 내용
    with open(b_path, "w", encoding="utf-8") as f:  # 둘째 파일 쓰기
        f.write("apple\ncherry\ndragonfruit\n")  # 둘째 파일 내용
    print("(a.txt = apple, banana, cherry / b.txt = apple, cherry, dragonfruit)")  # 파일 내용 안내
    cwd = os.getcwd()  # 원래 작업 폴더 기억
    os.chdir(tmp)  # 짧은 파일 이름으로 보여 주려고 임시 폴더로 이동
    try:
        run("diff a.txt b.txt")  # 두 파일 비교
        run("diff a.txt nope.txt")  # 없는 파일
    finally:
        os.chdir(cwd)  # 원래 폴더로 복귀
check("공통은 공백 2칸, 삭제는 -, 추가는 +")  # 확인 포인트

# ============================================================================
# 장면 9: BENCH
# ============================================================================
scene("[보너스] BENCH : 정렬 알고리즘 실행 시간 비교")  # 장면 9
run("bench")  # 원소 개수 100, 500, 1000, 2000으로 측정
check("크기가 2배일 때 삽입 정렬만 약 4배 → O(N²), 병합·퀵은 2배 조금 넘게 → O(N log N)")  # 확인 포인트

# ---------- 테스트 ----------

# ============================================================================
# 장면 10: 단위 테스트
# ============================================================================
scene("단위 테스트 전체 실행")  # 장면 10
suite = unittest.defaultTestLoader.discover("tests")  # tests 폴더의 테스트를 모두 찾기
result = unittest.TextTestRunner(stream=sys.stdout, verbosity=1).run(suite)  # 실행하고 요약을 화면 순서대로 출력
check(f"테스트 {result.testsRun}개 중 실패 {len(result.failures)}개, 에러 {len(result.errors)}개")  # 확인 포인트
sys.exit(0 if result.wasSuccessful() else 1)  # 테스트가 실패하면 종료 코드 1
