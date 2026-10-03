#!/usr/bin/env python3
"""入力ファイルの更新を検知してサイト生成と全検証を実行する。"""

from __future__ import annotations

import hashlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLL_SECONDS = 2.0
STOP = False


def handle_stop(_signum: int, _frame: object) -> None:
    global STOP
    STOP = True


def monitored_files() -> list[Path]:
    paths: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in {".git", "__pycache__"} for part in relative.parts):
            continue
        if relative == Path("search-index.json"):
            continue
        # 生成HTMLは生成元の変更で再生成するため、監視対象から除外する。
        if len(relative.parts) >= 2 and relative.parts[:2] == ("過去問", "web") and path.suffix.lower() == ".html":
            continue
        if path.suffix.lower() in {".html", ".md", ".js", ".mjs", ".py", ".json", ".pdf", ".png"}:
            paths.append(path)
    return sorted(paths)


def signature(paths: list[Path]) -> tuple[tuple[str, int, int, str], ...]:
    result: list[tuple[str, int, int, str]] = []
    for path in paths:
        try:
            stat = path.stat()
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except FileNotFoundError:
            continue
        result.append((path.relative_to(ROOT).as_posix(), stat.st_mtime_ns, stat.st_size, digest))
    return tuple(result)


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def rebuild_and_validate() -> None:
    run(["node", "過去問/web/build.mjs"])
    run([sys.executable, "tools/build_search_index.py"])
    run([sys.executable, "tools/validate_web.py"])
    run([sys.executable, "tools/validate_tables.py"])
    run([sys.executable, "tools/validate_questions.py"])
    run([sys.executable, "tools/verify_explanations.py"])
    run(["node", "tools/validate_quiz_render.js"])


def main() -> int:
    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)
    paths = monitored_files()
    previous = signature(paths)
    print(f"[watch {time.strftime('%Y-%m-%d %H:%M:%S %Z')}] 監視開始（{len(paths)}ファイル）", flush=True)
    while not STOP:
        time.sleep(POLL_SECONDS)
        current_paths = monitored_files()
        current = signature(current_paths)
        if current == previous:
            continue
        changed = sorted({item[0] for item in previous} ^ {item[0] for item in current})
        old = dict((item[0], item[1:]) for item in previous)
        new = dict((item[0], item[1:]) for item in current)
        changed.extend(sorted(name for name in set(old) & set(new) if old[name] != new[name]))
        print(
            f"[watch {time.strftime('%Y-%m-%d %H:%M:%S %Z')}] 変更検知: {', '.join(changed[:20])}",
            flush=True,
        )
        succeeded = False
        try:
            rebuild_and_validate()
        except subprocess.CalledProcessError as exc:
            print(f"[watch {time.strftime('%Y-%m-%d %H:%M:%S %Z')}] 検証失敗（終了コード {exc.returncode}）", flush=True)
        else:
            succeeded = True
            print(f"[watch {time.strftime('%Y-%m-%d %H:%M:%S %Z')}] 再生成・全検証完了", flush=True)
        if succeeded:
            previous = signature(monitored_files())
            paths = monitored_files()
    print(f"[watch {time.strftime('%Y-%m-%d %H:%M:%S %Z')}] 監視終了", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
