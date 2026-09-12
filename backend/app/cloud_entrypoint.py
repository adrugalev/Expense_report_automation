from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _terminate(processes: list[subprocess.Popen[bytes]]) -> None:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 10
    for process in processes:
        if process.poll() is not None:
            continue
        timeout = max(0.1, deadline - time.monotonic())
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        check=True,
    )

    frontend_env = os.environ.copy()
    frontend_env.setdefault("HOSTNAME", "0.0.0.0")
    frontend_env.setdefault("PORT", "3000")
    processes = [
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=PROJECT_ROOT,
        ),
        subprocess.Popen(["node", "frontend/server.js"], cwd=PROJECT_ROOT, env=frontend_env),
    ]

    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        if not stopping:
            stopping = True
            _terminate(processes)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        while not stopping:
            for process in processes:
                return_code = process.poll()
                if return_code is not None:
                    stopping = True
                    _terminate(processes)
                    return return_code
            time.sleep(0.5)
    finally:
        _terminate(processes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
