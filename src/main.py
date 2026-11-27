import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from traffic_guard.cli import main  # noqa: E402

if __name__ == "__main__":
    main()
