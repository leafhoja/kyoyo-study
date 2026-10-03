#!/usr/bin/env python3
"""Markdown/HTML の表崩れを検出する静的検証ツール。

検出対象:
- Markdown 表の区切り行欠落、列数不一致、行間の空行
- 先頭の ``\\|`` による表行のエスケープ
- HTML 内に文字列として残った escaped table markup
- HTML の <p> 内に置かれた Markdown 表行
- HTML 表のタグ不整合、rowspan/colspan を考慮した列幅不一致

使い方: python3 tools/validate_tables.py
"""

from __future__ import annotations

import re
import sys
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROBLEM_SOURCES = {
    ("2023", "Ⅰ"): "過去問/2023年度/2023_基礎能力I.md",
    ("2023", "Ⅱ"): "過去問/2023年度/2023_基礎能力II.md",
    ("2024", "Ⅰ"): "過去問/2024年度/2024_基礎能力I.md",
    ("2024", "Ⅱ"): "過去問/2024年度/2024_基礎能力II.md",
    ("2025", "Ⅰ"): "過去問/2025年度/2025_基礎能力I.md",
    ("2025", "Ⅱ"): "過去問/2025年度/2025_基礎能力II.md",
}
SEP_RE = re.compile(r"^\s*:?-{3,}:?\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
TABLE_MARKUP_RE = re.compile(r"&lt;(?:div|table|thead|tbody|tr|td|th)(?:[ >]|&)")
MARKDOWN_IN_P_RE = re.compile(r"<p>\s*\|[^<\n]*\|[^<\n]*\|")


def is_markdown_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and not stripped.startswith(r"\|") and stripped.count("|") >= 2


def split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith(r"\|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def validate_markdown(path: Path) -> tuple[int, list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    errors: list[str] = []
    table_count = 0
    in_fence = False
    index = 0

    while index < len(lines):
        line = lines[index]
        if FENCE_RE.match(line):
            in_fence = not in_fence
            index += 1
            continue
        if in_fence:
            index += 1
            continue

        if re.match(r"^\s*\\\|", line) and line.count("|") >= 2:
            errors.append(f"{path}:{index + 1}: 表行の先頭が \\| でエスケープされています")

        if not is_markdown_row(line) or index + 1 >= len(lines) or not is_markdown_row(lines[index + 1]):
            index += 1
            continue

        header = split_markdown_row(line)
        delimiter = split_markdown_row(lines[index + 1])
        if not all(SEP_RE.fullmatch(cell) for cell in delimiter):
            index += 1
            continue

        table_count += 1
        expected = len(header)
        if len(delimiter) != expected:
            errors.append(
                f"{path}:{index + 2}: 区切り行の列数が不一致（期待={expected}, 実際={len(delimiter)}）"
            )

        row_index = index + 2
        while row_index < len(lines) and is_markdown_row(lines[row_index]):
            actual = len(split_markdown_row(lines[row_index]))
            if actual != expected:
                errors.append(
                    f"{path}:{row_index + 1}: 表行の列数が不一致（期待={expected}, 実際={actual}）"
                )
            row_index += 1

        if (
            row_index + 1 < len(lines)
            and not lines[row_index].strip()
            and is_markdown_row(lines[row_index + 1])
            and not (
                row_index + 2 < len(lines)
                and is_markdown_row(lines[row_index + 2])
                and all(SEP_RE.fullmatch(cell) for cell in split_markdown_row(lines[row_index + 2]))
            )
        ):
            errors.append(f"{path}:{row_index + 1}: 表の行間に空行があります")

        index = row_index

    return table_count, errors


def count_markdown_tables(markdown: str) -> int:
    """Markdown本文中の表数を数える（コードフェンス内は除外）。"""
    lines = markdown.replace("\r\n", "\n").split("\n")
    count = 0
    in_fence = False
    index = 0
    while index + 1 < len(lines):
        if FENCE_RE.match(lines[index]):
            in_fence = not in_fence
            index += 1
            continue
        if (
            not in_fence
            and is_markdown_row(lines[index])
            and is_markdown_row(lines[index + 1])
            and all(SEP_RE.fullmatch(cell) for cell in split_markdown_row(lines[index + 1]))
        ):
            count += 1
            index += 2
            continue
        index += 1
    return count


def validate_problem_page_table_counts() -> list[str]:
    """問題文Markdownと、正答表を除いた問題HTMLの表数を突合する。"""
    errors: list[str] = []
    answer_heading = re.compile(r"^##\s+CP-\d{4}.*正答番号表", re.MULTILINE)
    for (year, part), source_name in PROBLEM_SOURCES.items():
        source_path = ROOT / source_name
        output_path = ROOT / f"過去問/web/{year}年度_{part}部_問題.html"
        markdown = source_path.read_text(encoding="utf-8")
        start = re.search(r"^##\s+試験問題\s*$", markdown, re.MULTILINE)
        answer = answer_heading.search(markdown)
        if start:
            end = answer.start() if answer else len(markdown)
            expected = count_markdown_tables(markdown[start.end():end])
        else:
            expected = count_markdown_tables(markdown)

        # 問題文の表は、PDFの罫線・結合セル・文字配置を再現するため、
        # Markdownで再入力せず原本PDFから切り出した画像を使う。
        if expected:
            errors.append(
                f"{source_path}: 問題文セクションにMarkdown表が残っています（{expected}件。原本PDF画像へ置換してください）"
            )

        # 文字だけの組合せ選択肢は、生成器が対応するHTML表も使用できる。
        # 原稿に明示された表を数え、生成HTMLでの追加・欠落を検出する。
        expected += len(re.findall(r"<table\b", markdown[start.end():end] if start else markdown))
        parser = HTMLTreeParser()
        parser.feed(output_path.read_text(encoding="utf-8"))
        actual = len(descendants(parser.root, "table"))
        if expected != actual:
            errors.append(
                f"{output_path}: 元Markdown表数と生成HTML表数が不一致（期待={expected}, 実際={actual}）"
            )
    return errors


class Node:
    def __init__(self, tag: str, attrs: list[tuple[str, str | None]], parent: Node | None) -> None:
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children: list[Node] = []


class HTMLTreeParser(HTMLParser):
    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
        "meta", "param", "source", "track", "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = Node("root", [], None)
        self.stack = [self.root]
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1].children.append(Node(tag, attrs, self.stack[-1]))

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID_TAGS:
            return
        if not self.stack or self.stack[-1].tag != tag:
            self.errors.append(f"タグの閉じ方が不正（</{tag}>）")
            return
        self.stack.pop()


def descendants(node: Node, tag: str) -> list[Node]:
    result: list[Node] = []
    for child in node.children:
        if child.tag == tag:
            result.append(child)
        result.extend(descendants(child, tag))
    return result


def direct_children(node: Node, tag: str) -> list[Node]:
    return [child for child in node.children if child.tag == tag]


def table_rows(table: Node) -> list[Node]:
    rows: list[Node] = []
    sections = [child for child in table.children if child.tag in {"thead", "tbody", "tfoot"}]
    for section in sections:
        rows.extend(child for child in section.children if child.tag == "tr")
    if not sections:
        rows.extend(child for child in table.children if child.tag == "tr")
    return rows


def cell_width(cell: Node, attribute: str) -> int:
    try:
        return max(1, int(cell.attrs.get(attribute, "1") or "1"))
    except ValueError:
        return 1


def effective_widths(rows: list[Node]) -> list[int]:
    occupied: set[tuple[int, int]] = set()
    widths: list[int] = []
    for row_number, row in enumerate(rows):
        column = 0
        cells = [child for child in row.children if child.tag in {"td", "th"}]
        for cell in cells:
            while (row_number, column) in occupied:
                column += 1
            colspan = cell_width(cell, "colspan")
            rowspan = cell_width(cell, "rowspan")
            for row_offset in range(rowspan):
                for column_offset in range(colspan):
                    occupied.add((row_number + row_offset, column + column_offset))
            column += colspan
        widths.append(max((col for row, col in occupied if row == row_number), default=-1) + 1)
    return widths


def validate_html(path: Path) -> tuple[int, list[str]]:
    text = path.read_text(encoding="utf-8")
    parser = HTMLTreeParser()
    parser.feed(text)
    errors = [f"{path}: {error}" for error in parser.errors]
    if len(parser.stack) > 1:
        errors.append(f"{path}: 未閉鎖のHTMLタグがあります")
    if TABLE_MARKUP_RE.search(text):
        errors.append(f"{path}: HTML表のマークアップが文字列としてエスケープされています")
    if MARKDOWN_IN_P_RE.search(text):
        errors.append(f"{path}: Markdown表の行が <p> 内に残っています")

    tables = descendants(parser.root, "table")
    for number, table in enumerate(tables, start=1):
        if table.parent and table.parent.tag == "p":
            errors.append(f"{path}: table #{number} が <p> 内にあります")
        rows = table_rows(table)
        if not rows:
            errors.append(f"{path}: table #{number} に行がありません")
            continue
        widths = effective_widths(rows)
        if len(set(widths)) > 1:
            errors.append(f"{path}: table #{number} の実効列幅が不一致です（{widths}）")
    return len(tables), errors


def main() -> int:
    markdown_tables = 0
    html_tables = 0
    errors: list[str] = []

    for path in sorted(ROOT.rglob("*.md")):
        if "tmp" not in path.parts:
            count, path_errors = validate_markdown(path)
            markdown_tables += count
            errors.extend(path_errors)

    for path in sorted(ROOT.rglob("*.html")):
        if "tmp" not in path.parts:
            count, path_errors = validate_html(path)
            html_tables += count
            errors.extend(path_errors)

    errors.extend(validate_problem_page_table_counts())

    print(f"Markdown tables: {markdown_tables}")
    print(f"HTML tables: {html_tables}")
    if errors:
        print(f"\nFAIL: {len(errors)}件")
        for error in errors:
            print(f"- {error}")
        return 1
    print("PASS: 表の構造検証を通過しました")
    return 0


if __name__ == "__main__":
    sys.exit(main())
