"""Mini Git 엔트리 포인트. 실행: python main.py"""

import sys

if sys.version_info < (3, 10):
    sys.exit("Mini Git requires Python 3.10 or later.")

from minigit.cli import run  # noqa: E402

if __name__ == "__main__":
    run()
