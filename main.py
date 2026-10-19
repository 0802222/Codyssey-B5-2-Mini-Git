"""Mini Git 엔트리 포인트. 실행: python main.py"""

import sys  # 파이썬 버전 확인, 프로그램 종료에 쓰는 표준 모듈

if sys.version_info < (3, 10):  # 파이썬 버전이 3.10보다 낮으면
    sys.exit("Mini Git requires Python 3.10 or later.")  # 안내 메시지를 띄우고 종료한다

# REPL을 시작하는 run 함수를 가져온다 (버전 확인 뒤에 import해야 해서 맨 위에 두지 않음)
from minigit.cli import run  # noqa: E402

if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만
    run()  # Mini Git 프로그램을 시작한다
