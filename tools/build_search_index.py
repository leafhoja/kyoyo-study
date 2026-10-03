#!/usr/bin/env python3
"""サイト内検索用インデックス生成スクリプト。

docs/技術設計/12_技術基本設計.md §5.10（既存3サイトのbuild-search-index.py方式を踏襲）の
教養区分サイト版。全HTMLページの <main class="main-content"> 内を h1/h2/h3 単位で
分割し、search-index.json を生成する。kyoyo.js がこれを遅延fetchして検索窓に使う。

使い方: python3 tools/build_search_index.py
"""
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "search-index.json"

TARGET_DIRS = [".", "第0部", "第1部", "第2部", "第3部", "第4部", "第5部", "第6部", "第7部", "過去問/web"]


class SectionExtractor(HTMLParser):
    """main.main-content 内の h1/h2/h3 を見出しとして、それ以降のテキストを
    次の見出しまで1セクションとして集める簡易パーサー。"""

    def __init__(self):
        super().__init__()
        self.in_main = False
        self.main_depth = 0
        self.depth = 0
        self.current_tag = None
        self.current_heading = None
        self.current_id = None
        self.buffer = []
        self.sections = []
        self.title = None
        self.in_title_tag = False
        self.capture_heading_text = False
        self.heading_text_buf = []
        # Markdown由来の問題ページでは、見出しを包む <section id="q1"> または
        # 見出し直前の <a id="q1"></a> が設問アンカーになる。見出し自体にidが
        # ない場合も、検索結果から各問へ直接移動できるようこのidを引き継ぐ。
        self.pending_heading_id = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.depth += 1
        if tag == "title":
            self.in_title_tag = True
        if tag == "main" and "main-content" in (attrs_dict.get("class") or ""):
            self.in_main = True
            self.main_depth = self.depth
        if (
            self.in_main
            and attrs_dict.get("id")
            and (
                (tag == "a" and not attrs_dict.get("href"))
                or tag == "section"
            )
        ):
            self.pending_heading_id = attrs_dict["id"]
        if self.in_main and tag in ("h1", "h2", "h3"):
            self._flush_section()
            self.current_heading = ""
            self.current_id = attrs_dict.get("id") or self.pending_heading_id
            self.pending_heading_id = None
            self.capture_heading_text = True
            self.heading_text_buf = []

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title_tag = False
        if self.in_main and tag in ("h1", "h2", "h3") and self.capture_heading_text:
            self.current_heading = "".join(self.heading_text_buf).strip()
            self.capture_heading_text = False
        if tag == "main" and self.in_main:
            self._flush_section()
            self.in_main = False
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.depth -= 1

    def handle_data(self, data):
        if self.in_title_tag:
            self.title = (self.title or "") + data
        if self.capture_heading_text:
            self.heading_text_buf.append(data)
        elif self.in_main:
            self.buffer.append(data)

    def _flush_section(self):
        text = re.sub(r"\s+", " ", "".join(self.buffer)).strip()
        if self.current_heading and text:
            self.sections.append(
                {"heading": self.current_heading, "id": self.current_id, "text": text[:600]}
            )
        self.buffer = []


def build():
    entries = []
    files = []
    for d in TARGET_DIRS:
        files.extend(sorted(Path(ROOT / d).glob("*.html")))

    for f in files:
        text = f.read_text(encoding="utf-8")
        parser = SectionExtractor()
        parser.feed(text)
        rel_url = str(f.relative_to(ROOT))
        page_title = (parser.title or f.stem).split("—")[0].strip()
        for sec in parser.sections:
            url = rel_url if not sec["id"] else f"{rel_url}#{sec['id']}"
            entries.append(
                {
                    "url": url,
                    "pageTitle": page_title,
                    "heading": sec["heading"],
                    "text": sec["text"],
                }
            )

    OUTPUT.write_text(json.dumps(entries, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"索引エントリ数: {len(entries)}（{len(files)}ページから生成）")
    print(f"出力先: {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    build()
