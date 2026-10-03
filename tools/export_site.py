#!/usr/bin/env python3
"""公開用ファイルだけを書き出し、内部リンクを検証する。"""
from html.parser import HTMLParser
from pathlib import Path
import argparse
import shutil
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
EXTENSIONS = {".html", ".css", ".js", ".json", ".png", ".jpg", ".jpeg", ".svg", ".webp", ".ico"}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"href", "src"} and value:
                self.urls.append(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "_site")
    output = parser.parse_args().output.resolve()
    # 出力先は新しいディレクトリに限定し、既存データを上書きしない。
    output.mkdir(parents=True, exist_ok=False)
    candidates = list(ROOT.glob("*.html")) + list(ROOT.glob("*.css")) + list(ROOT.glob("*.js"))
    candidates.append(ROOT / "search-index.json")
    for folder in ["data", *(f"第{i}部" for i in range(8)), "過去問/web"]:
        candidates.extend((ROOT / folder).rglob("*"))
    count = 0
    for source in sorted(set(candidates)):
        if not source.is_file() or source.is_symlink() or source.suffix.lower() not in EXTENSIONS:
            continue
        if source.name.startswith("IMG_"):
            raise SystemExit(f"原本画像を公開対象から外してください: {source}")
        destination = output / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        count += 1
    (output / ".nojekyll").touch()
    errors = []
    pages = list(output.rglob("*.html"))
    for page in pages:
        links = Links()
        links.feed(page.read_text(encoding="utf-8"))
        for url in links.urls:
            parts = urlsplit(url)
            if parts.scheme or parts.netloc or not parts.path:
                continue
            target = (page.parent / unquote(parts.path)).resolve()
            if not target.is_relative_to(output) or not target.exists():
                errors.append(f"{page.relative_to(output)}: {url}")
    if errors:
        raise SystemExit("公開先に存在しないリンク:\n" + "\n".join(errors))
    print(f"PASS: {count}ファイルを出力、HTML {len(pages)}ページの内部リンクを確認: {output}")


if __name__ == "__main__":
    main()
