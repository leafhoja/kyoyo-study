#!/usr/bin/env python3
"""問題データファイル内のquestionIdを、章ID・Levelごとに一意な連番へ振り直す。

大量の問題を手作業で追記する際にID採番が重複しやすいための保守ツール。
使い方: python3 tools/renumber_ids.py data/questions/ch05.json [ch06.json ...]
既存の並び順（配列の順序）は保持し、sequenceOrderも配列内の位置で振り直す。
"""
import json
import sys
from collections import defaultdict
from pathlib import Path


def renumber(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    chapter_num = path.stem.replace("ch", "").upper()
    counters = defaultdict(int)
    for i, q in enumerate(data):
        lvl = q["difficultyLevel"]
        counters[lvl] += 1
        q["questionId"] = f"Q-CH{chapter_num}-L{lvl:02d}-{counters[lvl]:03d}"
        q["sequenceOrder"] = i + 1
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{path}: {len(data)}問を再採番しました")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使い方: python3 tools/renumber_ids.py <file.json> [file2.json ...]")
        sys.exit(1)
    for arg in sys.argv[1:]:
        renumber(Path(arg))
