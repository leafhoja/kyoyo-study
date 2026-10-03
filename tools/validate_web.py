#!/usr/bin/env python3
"""過去問Webの生成物とMarkdownの対応を検証する回帰チェック。

使い方: python3 tools/validate_web.py

このチェックは、生成HTMLに作業用のPDFページ見出しや正答情報が混入すること、
問題カードの選択肢・解説カードの正答表示が欠落すること、Markdownの問題・画像・PDFページ指定と
生成HTMLがずれること、ローカル原本PDFのページ範囲を越える指定が入ること、サイト内リンクや検索索引が
壊れることをビルド後に検出する。ルート以下の全HTMLを対象にし、問題UIがJSONの管理用メタデータを
表示用に参照していないことも確認する。
外部URLの到達確認は行わない。
"""

from __future__ import annotations

import html as html_lib
import ast
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - bundled runtime normally provides pypdf
    PdfReader = None


ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "過去問" / "web"
SOURCE = ROOT / "過去問" / "解説"
BUILD = WEB / "build.mjs"
CROP_SCRIPT = ROOT / "tmp" / "pdfs" / "rebuild_image_crops.py"
SOURCE_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(assets/[^)]+\)")
SOURCE_VISUAL_RE = re.compile(r"(?:表\s*(?:I|II|Ⅰ|Ⅱ)|図\s*(?:I|II|Ⅰ|Ⅱ|[1-9０-９])|グラフ|写真|画像)")
PDF_HEADING_RE = re.compile(
    r"^#{1,6}\s+PDF\s*(?:(?:p[.．]|page|ページ)\s*)?[0-9０-９]+\s*(?:ページ)?$",
    re.I,
)
PDF_HEADING_TEXT_RE = re.compile(
    r"^PDF\s*(?:(?:p[.．]|page|ページ)\s*)?[0-9０-９]+\s*(?:ページ)?$",
    re.I,
)
PDF_WORKING_PAGE_RE = re.compile(
    r"(?<![A-Za-z])PDF\s*(?:(?:p[.．]|page)\s*[0-9０-９]+)",
    re.I,
)
UNESCAPED_UNDERSCORE_RE = re.compile(r"(?<!\\)_")
# 問題JSONの管理用フィールドは公開UIへ出さない。出題可能性など、
# 学習者に必要な表示用フィールドとは区別して描画経路を監視する。
QUIZ_INTERNAL_FIELDS = ("createdDate", "lastUpdatedDate", "author", "reviewStatus")
QUIZ_PUBLIC_TEXT_FIELDS = (
    "questionText",
    "choices",
    "explanation",
    "hints",
    "basisDescription",
    "targetExamYear",
    "field",
    "examYear",
    "examSubject",
    "questionNumber",
    "likelihoodLabel",
)
QUIZ_PUBLIC_INTERNAL_TEXT_RE = re.compile(
    r"(?:\.md\b|設計書|制作中|今後追加予定|実装・更新時|現時点では未更新|拡充中|"
    r"転記注|\bOCR\b|校正|作業メモ|原本と照合|確認日|サイト制作者|未レビュー)",
    re.I,
)
PUBLIC_INTERNAL_FILENAME_RE = re.compile(r"(?<![A-Za-z0-9_])[^\s\"<>]*\.md\b", re.I)
# 原本との突合で確定した、図の位置に関する回帰条件。
# 画像内容が正しくても、本文・図・選択肢の順序が崩れると問題を再現できないため、
# 各画像が後続の本文アンカーより前にあることを確認する。
IMAGE_ORDER_RULES = {
    ("2025", "Ⅰ", 15): [("2025-i-q15-figure.png", r"^\s*1\.\s+")],
    ("2025", "Ⅰ", 17): [("2025-i-q17-figures.png", r"!\[[^\]]*問17の選択肢[^\]]*\]\(assets/")],
    ("2024", "Ⅰ", 21): [("2024-i-q21-figure.png", r"^\s*1\.\s+")],
    ("2025", "Ⅰ", 21): [("2025-i-q21-figure.png", r"^<!--\s*PDF page\s+30\s*-->$")],
    ("2025", "Ⅱ", 7): [("2025-ii-q7-wave.png", r"^<!--\s*PDF page\s+9\s*-->$")],
    ("2025", "Ⅱ", 30): [("2025-ii-q30-image.png", r"!\[[^\]]*問30の選択肢[^\]]*\]\(assets/")],
}

SPECS = [
    {"year": "2023", "part": "Ⅰ", "source": "過去問/2023年度/2023_基礎能力I.md", "pdf": "https://www.jinji.go.jp/content/000010518.pdf", "count": 24},
    {"year": "2023", "part": "Ⅱ", "source": "過去問/2023年度/2023_基礎能力II.md", "pdf": "https://www.jinji.go.jp/content/000010519.pdf", "count": 30},
    {"year": "2024", "part": "Ⅰ", "source": "過去問/2024年度/2024_基礎能力I.md", "pdf": "https://www.jinji.go.jp/content/900035940.pdf", "count": 24},
    {"year": "2024", "part": "Ⅱ", "source": "過去問/2024年度/2024_基礎能力II.md", "pdf": "https://www.jinji.go.jp/content/000002973.pdf", "count": 30},
    {"year": "2025", "part": "Ⅰ", "source": "過去問/2025年度/2025_基礎能力I.md", "pdf": "https://www.jinji.go.jp/content/000016198.pdf", "count": 24},
    {"year": "2025", "part": "Ⅱ", "source": "過去問/2025年度/2025_基礎能力II.md", "pdf": "https://www.jinji.go.jp/content/000013933.pdf", "count": 30},
]

LOCAL_PDFS = {
    ("2023", "Ⅰ"): ROOT / "過去問" / "2023年度" / "23I部.pdf",
    ("2023", "Ⅱ"): ROOT / "過去問" / "2023年度" / "23II部.pdf",
    ("2024", "Ⅰ"): ROOT / "過去問" / "2024年度" / "24I部.pdf",
    ("2024", "Ⅱ"): ROOT / "過去問" / "2024年度" / "24II部.pdf",
    ("2025", "Ⅰ"): ROOT / "過去問" / "2025年度" / "25I部.pdf",
    ("2025", "Ⅱ"): ROOT / "過去問" / "2025年度" / "25II部.pdf",
}


class HtmlInventory(HTMLParser):
    """HTML内のリンク、ID、見出し、画像、問題カードだけを収集する。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.images: list[str] = []
        self.resources: list[str] = []
        self.image_alts: list[str | None] = []
        self.image_records: list[tuple[str, str | None]] = []
        self.id_values: list[str] = []
        self.ids: set[str] = set()
        self.headings: list[tuple[int, str]] = []
        self.questions: list[int] = []
        self._heading_level: int | None = None
        self._heading_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if attrs_dict.get("id"):
            identifier = attrs_dict["id"] or ""
            self.id_values.append(identifier)
            self.ids.add(identifier)
        if tag == "a" and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"] or "")
        if tag == "script" and attrs_dict.get("src"):
            self.resources.append(attrs_dict["src"] or "")
        if tag == "link" and attrs_dict.get("href"):
            self.resources.append(attrs_dict["href"] or "")
        if tag == "img" and attrs_dict.get("src"):
            self.images.append(attrs_dict["src"] or "")
            self.image_alts.append(attrs_dict.get("alt"))
            self.image_records.append((attrs_dict.get("src") or "", attrs_dict.get("alt")))
        if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
            self._heading_level = int(tag[1])
            self._heading_text = []
        if tag == "section" and attrs_dict.get("data-question"):
            try:
                self.questions.append(int(attrs_dict["data-question"] or ""))
            except ValueError:
                self.questions.append(-1)

    def handle_endtag(self, tag: str) -> None:
        if self._heading_level is not None and tag == f"h{self._heading_level}":
            text = re.sub(r"\s+", " ", "".join(self._heading_text)).strip()
            self.headings.append((self._heading_level, text))
            self._heading_level = None
            self._heading_text = []

    def handle_data(self, data: str) -> None:
        if self._heading_level is not None:
            self._heading_text.append(data)


class QuestionCardInventory(HTMLParser):
    """問題・解説カードの最低限の表示内容を収集する。"""

    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.cards: list[dict[str, object]] = []
        self.current: dict[str, object] | None = None
        self.depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if self.current is not None:
            if tag not in self.VOID_TAGS:
                self.depth += 1
            if tag == "li":
                self.current["li"] = int(self.current["li"]) + 1
            if tag == "img" and attrs_dict.get("src"):
                self.current["images"].append(attrs_dict["src"] or "")
            if tag == "h2":
                self.current["has_h2"] = True
            if tag == "a" and attrs_dict.get("href"):
                self.current["links"].append(attrs_dict["href"] or "")
            if tag == "button" and attrs_dict.get("data-question-done"):
                self.current["done_keys"].append(attrs_dict["data-question-done"] or "")
            return
        if tag != "section":
            return
        classes = set((attrs_dict.get("class") or "").split())
        if "question-card" not in classes:
            return
        self.current = {
            "id": attrs_dict.get("id") or "",
            "data_question": attrs_dict.get("data-question") or "",
            "text": [],
            "li": 0,
            "images": [],
            "links": [],
            "done_keys": [],
            "has_h2": False,
            "has_answer": False,
        }
        self.depth = 1

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if tag == "section" and self.depth == 1:
            self.cards.append(self.current)
            self.current = None
            self.depth = 0
        elif tag not in self.VOID_TAGS and self.depth > 0:
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.current is None:
            return
        text = " ".join(data.split())
        if not text:
            return
        self.current["text"].append(text)
        if "正答" in text:
            self.current["has_answer"] = True


class VisibleTextInventory(HTMLParser):
    """script/styleを除いたHTML本文のテキストを収集する。"""

    VOID_TAGS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.text: list[str] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.skip_depth:
            if tag not in self.VOID_TAGS:
                self.skip_depth += 1
            return
        if tag in {"script", "style"}:
            self.skip_depth = 1

    def handle_endtag(self, tag: str) -> None:
        if self.skip_depth and tag not in self.VOID_TAGS:
            self.skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self.skip_depth:
            self.text.append(data)


def markdown_visible_lines(markdown: str) -> list[str]:
    """生成HTMLに現れる通常本文の候補行を抽出する。

    PDFページコメント・出典記録・見出し・表・表示用画像・数式ブロックは、
    別の構造検査で確認するためここでは除外する。インラインコードは記号を
    保持し、Markdownの強調記号だけを取り除く。
    """
    markdown = re.sub(r"<出典>.*?(?=^#{1,6}\s+|\Z)", "", markdown, flags=re.S | re.M)
    markdown = re.sub(r"^<!--.*?-->\s*$", "", markdown, flags=re.M)
    result: list[str] = []
    in_math = False
    in_code = False
    for raw_line in markdown.splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            candidate = " ".join(line.split())
        else:
            if line == r"\[":
                in_math = True
                continue
            if in_math:
                if line == r"\]":
                    in_math = False
                continue
            if not line or line.startswith("|") or re.fullmatch(r"[-*_]{3,}", line):
                continue
            if re.fullmatch(r"#{1,6}\s+.+", line):
                continue
            line = re.sub(r"!\[[^]]*\]\(assets/[^)]+\)", "", line)
            line = re.sub(r"\[([^]]+)\]\((?:[^()]|\([^)]*\))*\)", r"\1", line)
            line = re.sub(r"<[^>]+>", "", line)
            line = re.sub(r"^\s*>\s?", "", line)
            line = re.sub(r"^\s*(?:[-*+] |\d+\. )", "", line)
            protected: list[str] = []

            def protect_code(match: re.Match[str]) -> str:
                protected.append(match.group(1))
                return f"\uE000{len(protected) - 1}\uE001"

            line = re.sub(r"`([^`]*)`", protect_code, line)
            line = re.sub(r"[*_~`]", "", line)
            line = re.sub(
                r"\uE000(\d+)\uE001",
                lambda match: protected[int(match.group(1))],
                line,
            )
            candidate = " ".join(line.split())
        if len(candidate) >= 18:
            result.append(candidate)
    return result


def problem_question_visible_lines(markdown: str) -> dict[int, list[str]]:
    """問題Markdownの設問本文を、生成HTMLとの照合用に設問別抽出する。"""
    markdown = re.sub(r"<出典>.*?(?=^#{1,6}\s+|\Z)", "", markdown, flags=re.S | re.M)
    chunks = re.split(r"^##\s+No\.\s*(\d+)\s*$", markdown, flags=re.M)
    result: dict[int, list[str]] = {}
    for index in range(1, len(chunks), 2):
        question_number = int(chunks[index])
        candidates: list[str] = []
        for raw_line in chunks[index + 1].splitlines():
            line = raw_line.strip()
            if (
                not line
                or line.startswith("<!--")
                or re.fullmatch(r"#{1,6}\s+.+", line)
                or re.fullmatch(r"!\[[^]]*\]\(assets/[^)]+\)", line)
                or line.startswith("|")
                or line.startswith(">")
                or line.startswith("```")
                or "$" in line
                or line in {r"\[", r"\]"}
            ):
                continue
            line = re.sub(r"!\[[^]]*\]\(assets/[^)]+\)", "", line)
            line = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", line)
            line = re.sub(r"<[^>]+>", " ", line)
            line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
            line = re.sub(r"__([^_]+)__", r"\1", line)
            line = line.replace(r"\_", "_")
            # 問題ページでは *1 の脚注記号を ＊1 として表示する。
            line = line.replace("*", "＊")
            line = re.sub(r"[~`]", "", line)
            line = re.sub(r"^\s*(?:[-*+] |\d+\. )", "", line)
            line = " ".join(line.split())
            if len(line) >= 25:
                candidates.append(line)
        result[question_number] = candidates
    return result


def visible_text_contains(candidate: str, rendered: str) -> bool:
    """HTMLタグ境界で挿入される空白を無視して本文の包含を判定する。"""
    return "".join(candidate.split()) in "".join(rendered.split())


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def pdf_page_count(path: Path) -> int:
    """暗号化PDFにも対応してローカル原本の総ページ数を取得する。"""
    if PdfReader is not None:
        try:
            return len(PdfReader(str(path)).pages)
        except Exception:
            pass
    result = subprocess.run(
        ["pdfinfo", str(path)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"pdfinfo exit={result.returncode}")
    match = re.search(r"^Pages:\s+(\d+)\s*$", result.stdout, re.M)
    if not match:
        raise RuntimeError("pdfinfoのPages項目を解釈できません")
    return int(match.group(1))


def normalize_image_alt(alt: str) -> str:
    """build.mjs と同じ画像altの利用者向け整形を適用する。"""
    return (
        alt
        .replace("（原本PDFから切り出し。著作権保護対象部分は原本どおり伏せ字）", "（一部伏せ字）")
        .replace("（原本PDFから切り出し）", "")
        .strip()
    )


def markdown_images(markdown: str) -> list[tuple[str, str]]:
    return [
        (href, normalize_image_alt(alt))
        for alt, href in re.findall(r"!\[([^\]]*)\]\((assets/[^)]+)\)", markdown)
    ]


def markdown_links(markdown: str) -> list[str]:
    """画像記法を除いたMarkdownリンクのhrefを返す。"""
    return [href.strip() for href in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", markdown)]


def markdown_question_images(markdown: str, heading_pattern: str) -> dict[int, list[str]]:
    """Markdownの設問ごとの画像参照順を返す。"""
    parts = re.split(heading_pattern, markdown, flags=re.M)
    result: dict[int, list[str]] = {}
    for index in range(1, len(parts), 2):
        question = int(parts[index])
        result[question] = [image for image, _alt in markdown_images(parts[index + 1])]
    return result


def generated_question_images(html: str) -> dict[int, list[str]]:
    """生成HTMLの設問カードごとの画像参照順を返す。"""
    result: dict[int, list[str]] = {}
    cards = re.finditer(
        r'<section class="question-card" id="q(\d+)"[^>]*>(.*?)(?=<section class="question-card"|</article>)',
        html,
        re.S,
    )
    for card in cards:
        result[int(card.group(1))] = re.findall(r'<img src="(assets/[^"?]+)"', card.group(2))
    return result


def problem_html(spec: dict[str, object]) -> Path:
    return WEB / f"{spec['year']}年度_{spec['part']}部_問題.html"


def explanation_html(spec: dict[str, object]) -> Path:
    return WEB / f"{spec['year']}年度_{spec['part']}部.html"


def explanation_markdown(spec: dict[str, object]) -> Path:
    return ROOT / "過去問" / "解説" / f"{spec['year']}年度_{spec['part']}部.md"


def parse_index_rows(index_html: str, year: str, part: str) -> list[tuple[int, str, str, str, int]]:
    """問題別目次の1年度・1部の行を、番号・リンク先・題名・PDF・ページで返す。"""
    section = re.search(
        rf"<h2>{re.escape(year)}年度 {re.escape(part)}部</h2>(.*?)(?=<h2>|</article>)",
        index_html,
        re.S,
    )
    if not section:
        return []
    return [
        (int(number), f"{target}#q{question}", title, pdf, int(page))
        for number, target, question, title, pdf, page in re.findall(
            r'<tr><td[^>]*>(\d+)</td><td[^>]*><a href="([^"]+)#q(\d+)">([^<]+)</a></td>'
            r'<td[^>]*><a href="([^"]+?)#page=(\d+)">',
            section.group(1),
        )
    ]


def parse_source_pages() -> dict[tuple[str, str], list[int]]:
    build = read(BUILD)
    result: dict[tuple[str, str], list[int]] = {}
    pattern = re.compile(
        r'\{\s*year:\s*"(20\d{2})",\s*part:\s*"([ⅠⅡ])".*?sourcePages:\s*\[([^]]*)\]\s*\}',
        re.S,
    )
    for match in pattern.finditer(build):
        pages = [int(value) for value in re.findall(r"\d+", match.group(3))]
        result[(match.group(1), match.group(2))] = pages
    return result


def parse_problem_source_metadata() -> dict[tuple[str, str], tuple[str, str]]:
    """build.mjsの問題ソース定義から、(Markdown相対パス, 公式PDF URL)を返す。"""
    build = read(BUILD)
    result: dict[tuple[str, str], tuple[str, str]] = {}
    pattern = re.compile(
        r'\{\s*year:\s*"(20\d{2})",\s*part:\s*"([ⅠⅡ])",\s*source:\s*"([^"]+)",\s*pdf:\s*"([^"]+)"',
    )
    for match in pattern.finditer(build):
        result[(match.group(1), match.group(2))] = (match.group(3), match.group(4))
    return result


def source_preview_questions(markdown: str) -> dict[int, int]:
    """MarkdownのPDFページマーカーを、対応する問題番号へ割り当てる。"""
    lines = markdown.replace("\r\n", "\n").split("\n")
    result: dict[int, int] = {}
    current_question: int | None = None
    pending_pages: list[int] = []
    for index, line in enumerate(lines):
        heading = re.match(r"^##\s+No\.\s*(\d+)\s*$", line)
        if heading:
            current_question = int(heading.group(1))
            for page in pending_pages:
                result[page] = current_question
            pending_pages = []
            continue
        marker = re.match(r"^<!--\s*PDF page\s+(\d+)\s*-->$", line.strip())
        if not marker:
            continue
        page = int(marker.group(1))
        next_index = index + 1
        while next_index < len(lines) and not lines[next_index].strip():
            next_index += 1
        if next_index < len(lines) and re.match(r"^##\s+No\.\s*\d+\s*$", lines[next_index]):
            pending_pages.append(page)
        elif current_question is not None:
            result[page] = current_question
    return result


def generated_preview_questions(html: str) -> dict[int, int]:
    """生成HTMLのPDFプレビューリンクを、包含する問題カードへ割り当てる。"""
    result: dict[int, int] = {}
    cards = re.finditer(
        r'<section class="question-card" id="q(\d+)"[^>]*>(.*?)(?=<section class="question-card"|</article>)',
        html,
        re.S,
    )
    for card in cards:
        question = int(card.group(1))
        for page in re.findall(r"\.pdf#page=(\d+)", card.group(2)):
            result[int(page)] = question
    return result


def parse_crop_specs() -> list[tuple[str, int, str]]:
    """原本PDFからの画像切り出し定義を読み取り、(PDF, ページ, ファイル名)を返す。"""
    tree = ast.parse(read(CROP_SCRIPT), filename=str(CROP_SCRIPT))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "SPECS" for target in node.targets):
            continue
        specs = ast.literal_eval(node.value)
        return [(str(pdf), int(page), str(name)) for pdf, page, name, _box in specs]
    raise ValueError(f"SPECS が見つかりません: {CROP_SCRIPT}")


def crop_pdf_key(pdf: str) -> tuple[str, str] | None:
    match = re.fullmatch(r"(\d{2})(I|II|Ⅱ)部\.pdf", Path(pdf).name)
    if not match:
        return None
    year = str(2000 + int(match.group(1)))
    part = "Ⅰ" if match.group(2) == "I" else "Ⅱ"
    return year, part


def local_target(source: Path, href: str) -> tuple[Path, str] | None:
    href = html_lib.unescape(href).strip()
    if not href or href.startswith(("#", "//", "data:", "mailto:", "javascript:", "tel:")):
        return None
    parsed = urlsplit(href)
    if parsed.scheme:
        return None
    target = (source.parent / parsed.path).resolve()
    try:
        target.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return target, parsed.fragment


def generated_markdown_target(source_html: Path, href: str) -> tuple[Path, str] | None:
    """生成器のmapHref後に解決される、Markdown内ローカルリンクの参照先を返す。"""
    href = html_lib.unescape(href).strip()
    parsed = urlsplit(href)
    if parsed.scheme or href.startswith("//"):
        return None
    if parsed.path.lower().endswith(".pdf"):
        # build.mjs は原本PDFへの相対リンクを公式PDFの外部URLへ変換する。
        return None
    path = re.sub(r"\.md$", ".html", parsed.path, flags=re.I)
    essay = re.fullmatch(r"\.\./(20\d{2})年度/\1_総合論文\.md", parsed.path)
    if essay:
        path = f"{essay[1]}年度_総合論文_問題.html"
    elif parsed.path.startswith("../解説/"):
        path = Path(path).name
    mapped = path + (f"#{parsed.fragment}" if parsed.fragment else "")
    return local_target(source_html, mapped)


def main() -> int:
    errors: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    html_files = sorted(ROOT.rglob("*.html"))
    inventories: dict[Path, HtmlInventory] = {}
    card_inventories: dict[Path, QuestionCardInventory] = {}
    visible_text_checks = 0
    app_js = read(WEB / "app.js")
    quiz_js = read(ROOT / "quiz.js")
    render_check = subprocess.run(
        ["node", str(ROOT / "tools" / "validate_quiz_render.js")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    check(
        render_check.returncode == 0,
        f"quiz.js動的描画検査に失敗しました: {(render_check.stdout + render_check.stderr).strip()}",
    )
    for field in QUIZ_INTERNAL_FIELDS:
        check(
            not re.search(rf"\bq\s*(?:\.\s*{re.escape(field)}|\[\s*['\"]{re.escape(field)}['\"]\s*\])", quiz_js),
            f"問題UIが内部管理フィールドを表示用に参照しています: q.{field}",
        )
    rendered_question_fields = set(re.findall(r"\bq\.([A-Za-z_$][A-Za-z0-9_$]*)", quiz_js))
    non_text_question_fields = {"type", "difficultyLevel", "questionId", "chapterId", "correctAnswer"}
    allowed_question_fields = set(QUIZ_PUBLIC_TEXT_FIELDS) | non_text_question_fields | {"sources"}
    check(
        rendered_question_fields <= allowed_question_fields,
        "問題UIが未監視のJSONフィールドを表示用に参照しています: "
        + ", ".join(sorted(rendered_question_fields - allowed_question_fields)),
    )
    for data_path in sorted((ROOT / "data" / "questions").glob("*.json")):
        try:
            question_data = json.loads(read(data_path))
        except (OSError, json.JSONDecodeError) as exc:
            check(False, f"問題UI用JSONを読めません: {data_path} ({exc})")
            continue
        for question in question_data if isinstance(question_data, list) else []:
            question_id = question.get("questionId", "<不明>")
            # 確認資料はtitle/urlのみ公開する。確認日は管理情報として保持する。
            for source in question.get("sources", []):
                for field in ("title", "url"):
                    check(
                        not QUIZ_PUBLIC_INTERNAL_TEXT_RE.search(str(source.get(field, ""))),
                        f"問題UIの確認資料に制作メモが表示されます: {data_path}:{question_id}:sources.{field}",
                    )
            for field in QUIZ_PUBLIC_TEXT_FIELDS:
                value = question.get(field)
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if isinstance(item, str):
                        check(
                            not QUIZ_PUBLIC_INTERNAL_TEXT_RE.search(item),
                            f"問題UIに内部参照・制作メモが表示されます: {data_path}:{question_id}:{field}",
                        )
    # 各章ページが読み込むJSON、JSON内のchapterId、問題順を対応付ける。
    referenced_quiz_data: set[Path] = set()
    for quiz_page in sorted(ROOT.rglob("*.html")):
        quiz_page_text = read(quiz_page)
        data_refs = re.findall(
            r"loadAndRender\(document\.getElementById\([\"']quiz-container[\"']\),\s*[\"']([^\"']+)[\"']\)",
            quiz_page_text,
        )
        if not data_refs:
            continue
        chapter_id = quiz_page.stem
        check(len(data_refs) == 1, f"問題ページのJSON参照数が不正です: {quiz_page}")
        if len(data_refs) != 1:
            continue
        data_path = (quiz_page.parent / data_refs[0]).resolve()
        referenced_quiz_data.add(data_path)
        check(data_path.exists(), f"問題ページのJSON参照先がありません: {quiz_page} -> {data_refs[0]}")
        if not data_path.exists():
            continue
        check(
            data_path.stem == chapter_id,
            f"問題ページとJSONファイル名の章対応が不一致です: {quiz_page} -> {data_path.name}",
        )
        try:
            page_questions = json.loads(read(data_path))
        except (OSError, json.JSONDecodeError) as exc:
            check(False, f"問題ページのJSONを読めません: {data_path} ({exc})")
            continue
        sequence = [question.get("sequenceOrder") for question in page_questions]
        check(sequence == sorted(sequence), f"問題ページのJSON問題順が不正です: {data_path}")
        check(
            all(question.get("chapterId") == chapter_id for question in page_questions),
            f"問題ページとJSON内chapterIdが不一致です: {quiz_page} -> {data_path.name}",
        )
    for data_path in sorted((ROOT / "data" / "questions").glob("*.json")):
        check(data_path.resolve() in referenced_quiz_data, f"問題JSONがどの章ページからも参照されていません: {data_path}")
    check("kakomon-explanation-progress-v2" in app_js, "復習進捗キーが年度対応版ではありません")
    check("body.dataset.current" in app_js, "復習進捗キーにページ識別子が使われていません")
    check("questionProgressKey(card)" in app_js, "復習進捗の設問キー生成が使われていません")
    expected_web_files = {
        "index.html",
        "解説集.html",
        "学習ガイド.html",
        "問題別目次.html",
        "確認事項.html",
    }
    expected_web_files.update(explanation_html(spec).name for spec in SPECS)
    expected_web_files.update(problem_html(spec).name for spec in SPECS)
    essay_problem_files = {f"{year}年度_総合論文_問題.html" for year in (2023, 2024, 2025)}
    expected_web_files.update(essay_problem_files)
    expected_web_files.update(f"{year}年度_総合論文.html" for year in (2023, 2024, 2025))
    expected_web_files.add("総合論文_目次.html")
    actual_web_files = {path.name for path in WEB.glob("*.html")}
    check(
        actual_web_files == expected_web_files,
        f"生成HTMLのファイル集合が生成器定義と不一致です: 余分={sorted(actual_web_files - expected_web_files)}, 欠落={sorted(expected_web_files - actual_web_files)}",
    )
    expected_source_html = {path.with_suffix(".html").name for path in SOURCE.glob("*.md")}
    actual_source_html = actual_web_files - {"index.html"} - {problem_html(spec).name for spec in SPECS} - essay_problem_files
    check(
        actual_source_html == expected_source_html,
        f"解説Markdownと生成HTMLの集合が不一致です: 余分={sorted(actual_source_html - expected_source_html)}, 欠落={sorted(expected_source_html - actual_source_html)}",
    )
    for path in html_files:
        parser = HtmlInventory()
        parser.feed(read(path))
        inventories[path] = parser
        cards = QuestionCardInventory()
        cards.feed(read(path))
        card_inventories[path] = cards
        if cards.current is not None:
            check(False, f"問題カードのsectionが閉じていません: {path}")
        matching_spec = next(
            (spec for spec in SPECS if path.name in {problem_html(spec).name, explanation_html(spec).name}),
            None,
        )
        if matching_spec is not None:
            expected_card_count = int(matching_spec["count"])
            check(
                len(cards.cards) == expected_card_count,
                f"問題カード数が年度・部の定義と不一致です: {path} ({len(cards.cards)} != {expected_card_count})",
            )
            is_problem_page = path.name == problem_html(matching_spec).name
            expected_card_ids = [f"q{number}" for number in range(1, expected_card_count + 1)]
            actual_card_ids = [str(card["id"]) for card in cards.cards]
            actual_data_questions = [str(card["data_question"]) for card in cards.cards]
            check(actual_card_ids == expected_card_ids, f"問題カードのidが連番ではありません: {path}")
            check(
                actual_data_questions == [str(number) for number in range(1, expected_card_count + 1)],
                f"問題カードのdata-questionが連番ではありません: {path}",
            )
            for card in cards.cards:
                card_id = str(card["id"])
                text = card["text"]
                check(bool(card_id), f"問題カードのidがありません: {path}")
                check(bool(text), f"問題カードの本文が空です: {path}#{card_id}")
                if is_problem_page:
                    images = [str(src).lower() for src in card["images"]]
                    has_visual_choices = any("choices" in src for src in images)
                    card_markup = re.search(
                        rf'<section class="question-card" id="{re.escape(card_id)}"[^>]*>(.*?)(?=<section class="question-card"|</article>)',
                        read(path), re.S,
                    )
                    table_choice_numbers = re.findall(
                        r'<tr>\s*<td\b[^>]*>\s*([1-5])\s*</td>',
                        card_markup[1] if card_markup else "",
                    )
                    has_table_choices = table_choice_numbers == list("12345")
                    check(
                        int(card["li"]) >= 2 or has_visual_choices or has_table_choices,
                        f"問題カードに選択肢がありません（テキストまたは選択肢画像が必要）: {path}#{card_id}",
                    )
                    expected_explanation_href = f"{explanation_html(matching_spec).name}#{card_id}"
                    check(
                        expected_explanation_href in card["links"],
                        f"問題カードの解説リンクが年度・設問番号と不一致です: {path}#{card_id}",
                    )
                else:
                    check(bool(card["has_h2"]), f"解説カードにh2見出しがありません: {path}#{card_id}")
                    check(bool(card["has_answer"]), f"解説カードに正答表示がありません: {path}#{card_id}")
                    check(
                        card_id in card["done_keys"],
                        f"解説カードの復習キーが設問番号と不一致です: {path}#{card_id}",
                    )
        check(len(parser.id_values) == len(parser.ids), f"HTML内のidが重複しています: {path}")
        for level, heading in parser.headings:
            check(not PDF_HEADING_TEXT_RE.match(heading), f"PDFページ見出しが表示されています: {path}:{heading}")
        levels = [level for level, _ in parser.headings]
        check(levels.count(1) == 1, f"h1が1個ではありません: {path} ({levels.count(1)})")
        for previous, current in zip(levels, levels[1:]):
            check(current <= previous + 1, f"見出しレベルを飛ばしています: {path} (h{previous}->h{current})")
        text = read(path)
        check("59問" not in text, f"古い問題数表示が残っています: {path}")
        check("window.SITE_INDEX" not in text, f"内部サイト索引がHTMLに埋め込まれています: {path}")
        check("sourcePages" not in text, f"内部PDFページ定義がHTMLに埋め込まれています: {path}")
        check("<!-- PDF page" not in text, f"Markdown内部のPDFページマーカーがHTMLに残っています: {path}")
        current_match = re.search(r'<body\b[^>]*\bdata-current="([^"]+)"', text)
        if path.parent == WEB:
            check(
                current_match is not None and current_match.group(1) == path.name,
                f"HTMLのページ識別子data-currentがファイル名と不一致です: {path}",
            )
        check(
            not re.search(r"<h[1-6][^>]*>\s*PDF\s*(?:(?:p[.．]|page|ページ)\s*)?[0-9０-９]+\s*(?:ページ)?\s*</h[1-6]>", text, re.I),
            f"PDFページ識別子が本文に残っています: {path}",
        )
        check(
            not PDF_WORKING_PAGE_RE.search(text),
            f"作業用PDFページ表記がHTMLに残っています: {path}",
        )
        for forbidden in (
            "<出典>",
            "source-attribution",
            "＊No.",
            "作成・確認日",
            "確認日：",
            "確認日:",
            "原本と照合しています",
            "制作中",
            "今後追加予定",
            "実装・更新時",
            "現時点では未更新",
            "Phase 2",
            "拡充中",
            "プロジェクト仕様書",
            "設計書",
        ):
            check(forbidden not in text, f"内部の出典識別子がHTMLに残っています: {path} ({forbidden})")
        check(
            not PUBLIC_INTERNAL_FILENAME_RE.search(text),
            f"設計・制作側Markdownのファイル名がHTMLに残っています: {path}",
        )
        visible_parser = VisibleTextInventory()
        visible_parser.feed(text)
        visible_text = " ".join(" ".join(visible_parser.text).split())
        check(
            not PDF_WORKING_PAGE_RE.search(visible_text),
            f"表示本文に作業用PDFページ表記が残っています: {path}",
        )
        check(
            not PUBLIC_INTERNAL_FILENAME_RE.search(visible_text),
            f"表示本文に設計・制作側Markdownのファイル名が残っています: {path}",
        )
        for forbidden in (
            "プロジェクト仕様書",
            "設計書",
            "確認日",
            "サイト制作者",
            "未レビュー",
            "制作中",
            "今後追加予定",
            "実装・更新時",
            "現時点では未更新",
            "Phase 2",
            "拡充中",
            "転記注",
            "転記時",
            "作業メモ",
            "原本と照合",
            "読み取り補助",
            "原本画像を確認",
            "画像で確認した",
        ):
            check(forbidden not in visible_text, f"表示本文に制作時情報が残っています: {path} ({forbidden})")
        check(
            not re.search(r"(?<![A-Za-z])OCR(?![A-Za-z])", visible_text, re.I),
            f"表示本文にOCR工程情報が残っています: {path}",
        )
        if "source-preview-link" in text:
            check(path.name.endswith("_問題.html"), f"PDFプレビューリンクが問題ページ以外に表示されています: {path}")
        check(all(alt is not None and alt.strip() for alt in parser.image_alts), f"画像altが空または未設定です: {path}")
        for forbidden in (
            "原本PDFから切り出し",
            "元PDFを参照",
            "原本PDFの図を参照",
            "転記注",
            "OCR層を基礎に",
            "OCRは",
            "OCRの",
            "OCR付き",
            "読み取り補助",
            "原本画像を確認",
            "画像で確認した",
            "作業メモ",
            "転記時",
        ):
            check(forbidden not in text, f"制作時の参照メモが利用者向けHTMLに残っています: {path} ({forbidden})")

        for href in parser.links + parser.images + parser.resources:
            target_info = local_target(path, href)
            if target_info is None:
                continue
            target, fragment = target_info
            check(target.exists(), f"ローカル参照先がありません: {path} -> {href}")
            if fragment and target.suffix.lower() == ".html" and target in inventories:
                check(fragment in inventories[target].ids, f"フラグメントIDがありません: {path} -> {href}")

    # 問題ページは正答表・内部ページマーカーを除く専用変換があるため、
    # 通常の解説・支援Markdownについて本文行の保持も確認する。
    for markdown_path in sorted(SOURCE.glob("*.md")):
        generated_path = WEB / markdown_path.with_suffix(".html").name
        inventory = inventories.get(generated_path)
        if inventory is None:
            continue
        visible = VisibleTextInventory()
        visible.feed(read(generated_path))
        rendered_text = " ".join(" ".join(visible.text).split())
        for line in markdown_visible_lines(read(markdown_path)):
            visible_text_checks += 1
            check(
                visible_text_contains(line, rendered_text),
                f"Markdown本文が生成HTMLに保持されていません: {markdown_path} -> {generated_path} ({line[:80]})",
            )

    # Markdown側のリンクも、生成後のhrefに変換したうえで先に検証する。
    # HTMLに現れなかったリンクは、生成器の分岐漏れで静かに失われる可能性があるため、
    # 生成HTMLのリンク検査だけではなく、元Markdownからの対応も確認する。
    source_output_pairs: list[tuple[Path, Path]] = []
    for spec in SPECS:
        source_output_pairs.append((ROOT / str(spec["source"]), problem_html(spec)))
        explanation_source = explanation_markdown(spec)
        source_output_pairs.append((explanation_source, explanation_html(spec)))
    for markdown_path in sorted(SOURCE.glob("*.md")):
        source_output_pairs.append((markdown_path, WEB / markdown_path.with_suffix(".html").name))
    for year in (2023, 2024, 2025):
        source_output_pairs.append((
            ROOT / f"過去問/{year}年度/{year}_総合論文.md",
            WEB / f"{year}年度_総合論文_問題.html",
        ))
    seen_pairs: set[tuple[Path, Path]] = set()
    for markdown_path, output_path in source_output_pairs:
        pair = (markdown_path.resolve(), output_path.resolve())
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        markdown_text = read(markdown_path)
        if output_path.name in essay_problem_files and output_path in inventories:
            visible = VisibleTextInventory()
            visible.feed(read(output_path))
            rendered_text = " ".join(" ".join(visible.text).split())
            for line in markdown_visible_lines(markdown_text):
                visible_text_checks += 1
                check(
                    visible_text_contains(line, rendered_text),
                    f"総合論文の本文が生成HTMLに保持されていません: {markdown_path} ({line[:80]})",
                )
            source_headings = [
                (len(match[1]), match[2].strip())
                for match in re.finditer(r"^(#{1,3})\s+(.+)$", markdown_text, re.M)
            ]
            check(
                [heading for heading in inventories[output_path].headings if heading[0] <= 3] == source_headings,
                f"総合論文の見出し列が不一致です: {markdown_path}",
            )
            for anchor in ("part1", "part2"):
                check(anchor in inventories[output_path].ids, f"総合論文の部別アンカーがありません: {output_path}#{anchor}")
        check(
            output_path.exists() and output_path.stat().st_mtime >= markdown_path.stat().st_mtime,
            f"Markdown更新後に生成HTMLが再生成されていません: {markdown_path} -> {output_path}",
        )
        for forbidden in (
            "> **転記注**",
            "／PDF",
            "原本：PDF",
            "OCR層を基礎に",
            "OCRは",
            "OCRの",
            "OCR付き",
            "読み取り補助",
            "原本画像を確認",
            "画像で確認した",
            "作業メモ",
            "転記時",
        ):
            check(forbidden not in markdown_text, f"Markdownに制作時の参照メモが残っています: {markdown_path} ({forbidden})")
        for href in markdown_links(markdown_text):
            target_info = generated_markdown_target(output_path, href)
            if target_info is None:
                continue
            target, fragment = target_info
            check(target.exists(), f"Markdownリンクの生成先がありません: {markdown_path} -> {href}")
            if fragment and target.suffix.lower() == ".html" and target in inventories:
                check(
                    fragment in inventories[target].ids,
                    f"MarkdownリンクのフラグメントIDがありません: {markdown_path} -> {href}",
                )

    for markdown_path in sorted(SOURCE.glob("*.md")):
        generated_path = WEB / markdown_path.with_suffix(".html").name
        if generated_path not in inventories:
            continue
        source_headings = [
            (len(match.group(1)), match.group(2).strip())
            for match in re.finditer(r"^(#{1,3})\s+(.+)$", read(markdown_path), re.M)
        ]
        generated_headings = [heading for heading in inventories[generated_path].headings if heading[0] <= 3]
        check(
            generated_headings == source_headings,
            f"MarkdownとHTMLの見出し列が不一致です: {markdown_path} -> {generated_path}",
        )

    source_pages = parse_source_pages()
    build_source = read(BUILD)
    generated_html_paths = sorted(WEB.glob("*.html"))
    if generated_html_paths:
        newest_build_time = BUILD.stat().st_mtime
        oldest_html_time = min(path.stat().st_mtime for path in generated_html_paths)
        check(
            oldest_html_time >= newest_build_time,
            "生成器更新後に全HTMLが再生成されていません",
        )
    search_index_path = ROOT / "search-index.json"
    if search_index_path.exists() and generated_html_paths:
        newest_html_time = max(path.stat().st_mtime for path in generated_html_paths)
        check(
            search_index_path.stat().st_mtime >= newest_html_time,
            "HTML更新後に検索索引が再生成されていません",
        )
    check("function assertPublicHtml" in build_source, "生成器に公開HTMLの内部情報ガードがありません")
    check("writePublicHtml(" in build_source, "生成器が公開HTML書き出しガードを使用していません")
    check("const pendingWrites = new Map()" in build_source, "生成器が検証前にHTMLを書き出す構造です")
    check("for (const [filename, html] of pendingWrites)" in build_source, "生成器のHTML一括書き出しがありません")
    check(len(source_pages) == len(SPECS), f"build.mjsの問題ソース定義数が不正です: {len(source_pages)}")
    for spec in SPECS:
        key = (str(spec["year"]), str(spec["part"]))
        pdf_path = LOCAL_PDFS.get(key)
        check(pdf_path is not None and pdf_path.exists(), f"年度・部に対応するローカル原本PDFがありません: {key}")
        if pdf_path is None or not pdf_path.exists():
            continue
        try:
            page_count = pdf_page_count(pdf_path)
        except Exception as exc:  # pragma: no cover - malformed local PDF
            errors.append(f"ローカル原本PDFを読めません: {pdf_path} ({exc})")
            continue
        source_path = ROOT / str(spec["source"])
        marker_numbers = [
            int(value)
            for value in re.findall(r"^<!--\s*PDF page\s+(\d+)\s*-->$", read(source_path), re.M)
        ]
        configured = source_pages.get(key, [])
        check(
            all(1 <= page <= page_count for page in marker_numbers),
            f"Markdown内部PDFページが原本の範囲外です: {key} (原本={page_count}ページ)",
        )
        check(
            all(1 <= page <= page_count for page in configured),
            f"生成器のPDFページ指定が原本の範囲外です: {key} (原本={page_count}ページ)",
        )
    source_metadata = parse_problem_source_metadata()
    expected_metadata = {
        (str(spec["year"]), str(spec["part"])): (str(spec["source"]), str(spec["pdf"]))
        for spec in SPECS
    }
    check(
        set(source_metadata) == set(expected_metadata),
        f"build.mjsの年度・部定義が検証仕様と不一致です: {sorted(set(source_metadata) ^ set(expected_metadata))}",
    )
    for key, (expected_source, expected_pdf) in expected_metadata.items():
        actual_source, actual_pdf = source_metadata.get(key, ("", ""))
        check(
            (WEB / actual_source).resolve() == (ROOT / expected_source).resolve(),
            f"build.mjsのMarkdown参照先が年度・部と不一致です: {key} ({actual_source})",
        )
        check(actual_pdf == expected_pdf, f"build.mjsの公式PDF URLが年度・部と不一致です: {key}")
    try:
        crop_specs = parse_crop_specs()
    except (OSError, SyntaxError, ValueError) as exc:
        crop_specs = []
        errors.append(f"原本PDF切り出し定義を読めません: {exc}")
    crop_names: set[str] = set()
    for pdf, page, name in crop_specs:
        crop_names.add(name)
        key = crop_pdf_key(pdf)
        check(key is not None, f"切り出し定義のPDF名を解釈できません: {pdf}")
        if key is not None:
            configured = source_pages.get(key, [])
            check(page in configured, f"切り出し画像のPDFページがsourcePagesにありません: {key} p.{page} ({name})")
        check((WEB / "assets" / name).exists(), f"切り出し画像がありません: {name}")
    check(len(crop_specs) == len(crop_names), "原本PDF切り出し定義に重複ファイル名があります")
    asset_paths = [WEB / "assets" / name for name in crop_names if (WEB / "assets" / name).exists()]
    if asset_paths:
        check(
            min(path.stat().st_mtime for path in asset_paths) >= CROP_SCRIPT.stat().st_mtime,
            "画像切り出し定義の更新後にPNG資産が再生成されていません",
        )
    markdown_asset_names: set[str] = set()
    for markdown_path in sorted((ROOT / "過去問").rglob("*.md")):
        markdown_text = read(markdown_path)
        check(
            not any(PDF_HEADING_RE.match(line.strip()) for line in markdown_text.splitlines()),
            f"MarkdownにPDFページ見出しが残っています: {markdown_path}",
        )
        if markdown_path.parent.name in {"2023年度", "2024年度", "2025年度"}:
            markdown_lines = markdown_text.replace("\r\n", "\n").split("\n")
            for line_index, line in enumerate(markdown_lines):
                if not re.search(r"!\[[^\]]*\]\(assets/[^)]+\)", line):
                    continue
                previous_index = line_index - 1
                while previous_index >= 0 and not markdown_lines[previous_index].strip():
                    previous_index -= 1
                previous = markdown_lines[previous_index].strip() if previous_index >= 0 else ""
                if previous and not re.match(r"^<!--\s*PDF page\s+\d+\s*-->$", previous) and not re.search(r"!\[[^\]]*\]\(assets/[^)]+\)$", previous):
                    check(
                        bool(re.search(r"[。！？.!?」』）)\]】]$", previous)),
                        f"画像直前の本文が句読点で終わっていません（OCR残片の可能性）: {markdown_path}:{line_index + 1}",
                    )
        for image, _alt in markdown_images(markdown_text):
            markdown_asset_names.add(Path(image).name)
            check((WEB / image).exists(), f"Markdownの画像ファイルがありません: {markdown_path} -> {image}")
    asset_names = {path.name for path in (WEB / "assets").iterdir() if path.is_file()}
    check(asset_names == markdown_asset_names, "Web画像ファイルとMarkdownの画像参照集合が不一致です")
    check(asset_names == crop_names, "Web画像ファイルとPDF切り出し定義の集合が不一致です")
    problem_image_names: set[str] = set()
    for spec in SPECS:
        key = (spec["year"], spec["part"])
        source_path = ROOT / str(spec["source"])
        problem_path = problem_html(spec)
        explanation_path = explanation_html(spec)
        source = read(source_path)
        problem = read(problem_path)
        explanation = read(explanation_path)
        explanation_source = read(explanation_markdown(spec))
        check(
            not any(UNESCAPED_UNDERSCORE_RE.search(line) for line in source.splitlines()),
            f"問題Markdownに未エスケープのアンダースコアがあります: {source_path}",
        )
        check(
            not any(PDF_HEADING_RE.match(line.strip()) for line in source.splitlines()),
            f"MarkdownにPDFページ見出しが残っています: {source_path}",
        )
        check(
            not any(PDF_HEADING_RE.match(line.strip()) for line in explanation_source.splitlines()),
            f"解説MarkdownにPDFページ見出しが残っています: {explanation_markdown(spec)}",
        )
        for markdown_path, markdown_text in ((source_path, source), (explanation_markdown(spec), explanation_source)):
            check(
                not re.search(r"!\[[^\]]*(?:原本PDFから切り出し|元PDFを参照)[^\]]*\]", markdown_text),
                f"Markdownの画像altに制作時情報が残っています: {markdown_path}",
            )
        source_numbers = [int(value) for value in re.findall(r"^##\s+No\.\s*(\d+)\s*$", source, re.M)]
        expected_numbers = list(range(1, int(spec["count"]) + 1))
        check(source_numbers == expected_numbers, f"Markdownの問題番号が連番ではありません: {source_path}")
        question_parts = re.split(r"^##\s+No\.\s*(\d+)\s*$", source, flags=re.M)
        for index in range(1, len(question_parts), 2):
            question_number = question_parts[index]
            question_body = question_parts[index + 1]
            passage = question_body.split("<出典>", 1)[0]
            for paragraph in re.split(r"\n\s*\n", passage):
                check(
                    not re.search(r"[。！？]\s*[○〇]\s+|\S\s+[ア-オ][:：]\s|\S\s+（注）", paragraph),
                    f"問題の条件・並べ替え項目・注記が前の本文に連結しています: {source_path} 問{question_number}",
                )
                check(
                    not re.search(r"\S\n(?:方法[①②]|[①②]−\s*[12]\s)", paragraph),
                    f"問題の方法・作業番号が前の本文に連結しています: {source_path} 問{question_number}",
                )
            if SOURCE_VISUAL_RE.search(question_body):
                check(
                    bool(SOURCE_IMAGE_RE.search(question_body)),
                    f"原本の図表語を含む問題に画像がありません: {source_path} 問{question_number}",
                )
            order_key = (str(spec["year"]), str(spec["part"]), int(question_number))
            for image_name, anchor_pattern in IMAGE_ORDER_RULES.get(order_key, []):
                image_match = re.search(
                    rf"!\[[^\]]*\]\(assets/{re.escape(image_name)}\)",
                    question_body,
                )
                anchor_match = re.search(anchor_pattern, question_body, re.M)
                check(
                    image_match is not None and anchor_match is not None and image_match.start() < anchor_match.start(),
                    f"本文・図・選択肢の順序が原本と不一致です: {source_path} 問{question_number} ({image_name})",
                )
        for path, content in ((problem_path, problem), (explanation_path, explanation)):
            inventory = inventories.get(path)
            check(inventory is not None, f"HTMLを解析できません: {path}")
            if inventory:
                check(inventory.questions == expected_numbers, f"生成HTMLの問題番号が連番ではありません: {path}")
                h1_texts = [heading for level, heading in inventory.headings if level == 1]
                expected_title = f"{spec['year']}年度 基礎能力試験{spec['part']}部 {'問題' if path == problem_path else '解説'}"
                check(h1_texts == [expected_title], f"HTMLの年度・部タイトルが不一致です: {path}")
                if path == problem_path:
                    generated_question_titles = [
                        heading for level, heading in inventory.headings
                        if level == 2 and re.fullmatch(r"問\d+", heading)
                    ]
                    check(
                        generated_question_titles == [f"問{number}" for number in expected_numbers],
                        f"問題HTMLの設問見出しがMarkdownの問題番号と不一致です: {path}",
                    )
                else:
                    expected_explanation_titles = re.findall(r"^##\s+(問\d+｜.+?)\s*$", explanation_source, re.M)
                    generated_explanation_titles = [
                        heading for level, heading in inventory.headings
                        if level == 2 and re.match(r"^問\d+｜", heading)
                    ]
                    check(
                        generated_explanation_titles == expected_explanation_titles,
                        f"解説HTMLの設問見出しがMarkdownと不一致です: {path}",
                    )
        problem_inventory = inventories.get(problem_path)
        problem_cards = card_inventories.get(problem_path)
        explanation_inventory = inventories.get(explanation_path)
        source_image_records = markdown_images(source)
        explanation_image_records = markdown_images(explanation_source)
        source_images = [image for image, _alt in source_image_records]
        explanation_images = [image for image, _alt in explanation_image_records]
        if problem_inventory:
            generated_problem_images = {image for image in problem_inventory.images if image.startswith("assets/")}
            check(generated_problem_images == set(source_images), f"問題MarkdownとHTMLの画像集合が不一致です: {problem_path}")
            generated_problem_records = [record for record in problem_inventory.image_records if record[0].startswith("assets/")]
            check(generated_problem_records == source_image_records, f"問題MarkdownとHTMLの画像altまたは順序が不一致です: {problem_path}")
            check(
                generated_question_images(problem) == markdown_question_images(source, r"^##\s+No\.\s*(\d+)\s*$"),
                f"問題MarkdownとHTMLの設問別画像配置が不一致です: {problem_path}",
            )
            expected_explanation_links = [f"{explanation_path.name}#q{number}" for number in expected_numbers]
            actual_explanation_links = re.findall(r'href="([^"#]+#q\d+)"', problem)
            check(actual_explanation_links == expected_explanation_links, f"問題→解説リンクの年度・設問対応が不一致です: {problem_path}")
            cards_by_question = {
                int(str(card["data_question"])): card
                for card in (problem_cards.cards if problem_cards else [])
                if str(card["data_question"]).isdigit()
            }
            for question_number, candidates in problem_question_visible_lines(source).items():
                card = cards_by_question.get(question_number)
                rendered_text = " ".join(str(value) for value in (card or {}).get("text", []))
                for candidate in candidates:
                    visible_text_checks += 1
                    check(
                        visible_text_contains(candidate, rendered_text),
                        f"問題Markdown本文が生成HTMLに保持されていません: {source_path} 問{question_number} ({candidate[:80]})",
                    )
        if explanation_inventory:
            generated_explanation_images = {image for image in explanation_inventory.images if image.startswith("assets/")}
            check(generated_explanation_images == set(explanation_images), f"解説MarkdownとHTMLの画像集合が不一致です: {explanation_path}")
            generated_explanation_records = [record for record in explanation_inventory.image_records if record[0].startswith("assets/")]
            check(generated_explanation_records == explanation_image_records, f"解説MarkdownとHTMLの画像altまたは順序が不一致です: {explanation_path}")
            check(
                generated_question_images(explanation) == markdown_question_images(explanation_source, r"^##\s+問(\d+)｜"),
                f"解説MarkdownとHTMLの設問別画像配置が不一致です: {explanation_path}",
            )
            check(f'href="{problem_path.name}"' in explanation, f"解説→問題リンクの年度・部対応がありません: {explanation_path}")
        check("正答番号表" not in problem, f"問題ページに正答番号表が混入しています: {problem_path}")
        check("正答：" not in problem, f"問題ページに正答が混入しています: {problem_path}")
        check("source-attribution" not in problem, f"問題ページに出典ブロックが混入しています: {problem_path}")
        check(not re.search(r"＊No\.\s*\d+", problem), f"問題ページに出典識別子が混入しています: {problem_path}")

        marker_numbers = [int(value) for value in re.findall(r"^<!--\s*PDF page\s+(\d+)\s*-->$", source, re.M)]
        markers = set(marker_numbers)
        configured = source_pages.get(key, [])
        check(configured and set(configured) <= markers, f"PDFページ指定に対応するMarkdown内部マーカーがありません: {key}")
        check(len(marker_numbers) == len(markers), f"MarkdownのPDFページ内部マーカーが重複しています: {key}")
        preview_pages = [int(value) for value in re.findall(re.escape(str(spec["pdf"])) + r"#page=(\d+)", problem)]
        check(preview_pages == configured, f"PDFプレビューのページ対応が不一致です: {key} {preview_pages} != {configured}")
        expected_preview_questions = {page: source_preview_questions(source)[page] for page in configured}
        actual_preview_questions = generated_preview_questions(problem)
        check(actual_preview_questions == expected_preview_questions, f"PDFプレビューの設問対応が不一致です: {key} {actual_preview_questions} != {expected_preview_questions}")
        source_question_image_map = markdown_question_images(source, r"^##\s+No\.\s*(\d+)\s*$")
        check(
            all(source_question_image_map.get(question) for question in expected_preview_questions.values()),
            f"図表のない設問にPDFプレビューを設定しています: {key}",
        )
        preview_questions = set(expected_preview_questions.values())
        check(
            all(not images or question in preview_questions for question, images in source_question_image_map.items()),
            f"画像のある設問にPDFプレビューがありません: {key}",
        )

        for image in source_images:
            asset = WEB / image
            problem_image_names.add(Path(image).name)
            check(asset.exists(), f"Markdownの画像ファイルがありません: {source_path} -> {image}")
            check(Path(image).name in crop_names, f"問題Markdownの画像が切り出し定義にありません: {source_path} -> {image}")
            check(f'src="{image}"' in problem, f"問題HTMLから画像が欠落しています: {problem_path} -> {image}")

        for image in explanation_images:
            asset = WEB / image
            check(asset.exists(), f"解説Markdownの画像ファイルがありません: {explanation_markdown(spec)} -> {image}")
            check(Path(image).name in crop_names, f"解説Markdownの画像が切り出し定義にありません: {explanation_markdown(spec)} -> {image}")
            check(f'src="{image}"' in explanation, f"解説HTMLから画像が欠落しています: {explanation_path} -> {image}")

        for path, content in ((problem_path, problem), (explanation_path, explanation)):
            official_links = re.findall(r'href="(https://www\.jinji\.go\.jp/content/[^"#]+\.pdf)', content)
            check(str(spec["pdf"]) in official_links, f"公式PDFリンクが年度・部と一致しません: {path}")
            check(set(official_links) <= {str(spec["pdf"])}, f"別年度・別部の公式PDFリンクが混入しています: {path}")

    for name in sorted(crop_names - problem_image_names):
        errors.append(f"切り出し画像が問題Markdownから参照されていません: {name}")

    home = read(WEB / "index.html")
    for year in {str(spec["year"]) for spec in SPECS}:
        count = sum(int(spec["count"]) for spec in SPECS if str(spec["year"]) == year)
        check(home.count(f"{count}問の問題と解説。") == len({str(spec["year"]) for spec in SPECS}), f"トップの年度別問題数表示が不一致です: {year} ({count})")
    check("基礎能力162問・総合論文6題を収録" in home, "トップの総問題数表示がありません")

    index_html = read(WEB / "問題別目次.html")
    for spec in SPECS:
        year = str(spec["year"])
        part = str(spec["part"])
        key = (year, part)
        rows = parse_index_rows(index_html, year, part)
        expected_numbers = list(range(1, int(spec["count"]) + 1))
        check(len(rows) == int(spec["count"]), f"問題別目次の行数が不一致です: {key} ({len(rows)})")
        check([row[0] for row in rows] == expected_numbers, f"問題別目次の表示番号が連番ではありません: {key}")
        explanation = explanation_html(spec)
        explanation_titles = {
            int(match.group(1)): match.group(2)
            for level, heading in inventories[explanation].headings
            if level == 2
            for match in [re.match(r"^問(\d+)｜(.+)$", heading)]
            if match
        }
        source_path = ROOT / str(spec["source"])
        source_page_questions = source_preview_questions(read(source_path))
        for number, href, title, pdf, page in rows:
            check(
                href == f"{explanation.name}#q{number}",
                f"問題別目次の解説リンクが年度・設問と不一致です: {key} 問{number} -> {href}",
            )
            check(title == explanation_titles.get(number), f"問題別目次の題名が解説見出しと不一致です: {key} 問{number}")
            check(pdf == str(spec["pdf"]), f"問題別目次の公式PDFが年度・部と不一致です: {key} 問{number}")
            check(
                source_page_questions.get(page) == number,
                f"問題別目次のPDFページがMarkdownの設問対応と不一致です: {key} 問{number} p.{page}",
            )

    index_path = ROOT / "search-index.json"
    try:
        search_index = json.loads(read(index_path))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"検索索引を読めません: {exc}")
        search_index = []
    check(isinstance(search_index, list) and bool(search_index), "検索索引が空です")
    if isinstance(search_index, list):
        question_entries = [
            entry
            for entry in search_index
            if isinstance(entry, dict)
            and str(entry.get("url", "")).startswith("過去問/web/")
            and re.match(r"^問\d+(?:｜|$)", str(entry.get("heading", "")))
        ]
        question_urls = [entry.get("url") for entry in question_entries]
        duplicate_urls = sorted({url for url in question_urls if question_urls.count(url) > 1})
        check(
            not duplicate_urls,
            "過去問の設問検索URLが重複しています（見出し固有のフラグメントが欠落している可能性）: "
            + ", ".join(duplicate_urls[:10]),
        )
        expected_question_search_urls = {
            f"過去問/web/{page_name}#q{number}"
            for spec in SPECS
            for page_name in (problem_html(spec).name, explanation_html(spec).name)
            for number in range(1, int(spec["count"]) + 1)
        }
        actual_question_search_urls = {str(entry.get("url")) for entry in question_entries}
        check(
            actual_question_search_urls == expected_question_search_urls,
            "検索索引の過去問設問URL集合が年度・部・設問番号定義と不一致です: "
            f"欠落={sorted(expected_question_search_urls - actual_question_search_urls)[:10]}, "
            f"余分={sorted(actual_question_search_urls - expected_question_search_urls)[:10]}",
        )
        for entry in question_entries:
            heading = str(entry.get("heading", ""))
            question_match = re.match(r"^問(\d+)(?:｜|$)", heading)
            if question_match:
                expected_fragment = f"#q{question_match.group(1)}"
                check(
                    str(entry.get("url", "")).endswith(expected_fragment),
                    f"過去問の設問検索URLに設問フラグメントがありません: {entry.get('url')} ({heading})",
                )
    for entry in search_index if isinstance(search_index, list) else []:
        serialized = json.dumps(entry, ensure_ascii=False)
        check("59問" not in serialized, "検索索引に古い問題数表示が残っています")
        check(
            not PDF_WORKING_PAGE_RE.search(serialized),
            "検索索引に作業用PDFページ表記が残っています",
        )
        for forbidden in (
            "原本PDFから切り出し",
            "元PDFを参照",
            "原本PDFの図を参照",
            "転記注",
            "OCR層を基礎に",
            "制作中",
            "今後追加予定",
            "実装・更新時",
            "現時点では未更新",
            "Phase 2",
            "拡充中",
            "プロジェクト仕様書",
            "設計書",
            "確認日",
            "サイト制作者",
            "未レビュー",
        ):
            check(forbidden not in serialized, f"検索索引に制作時情報が残っています: {forbidden}")
        check(
            not PUBLIC_INTERNAL_FILENAME_RE.search(serialized),
            "検索索引に設計・制作側Markdownのファイル名が残っています",
        )
        url = entry.get("url") if isinstance(entry, dict) else None
        if not isinstance(url, str):
            errors.append(f"検索索引のURLが不正です: {entry!r}")
            continue
        target_info = local_target(index_path, url)
        if target_info is not None:
            target, fragment = target_info
            check(target.exists(), f"検索索引の参照先がありません: {url}")
            if fragment and target.suffix.lower() == ".html" and target in inventories:
                check(fragment in inventories[target].ids, f"検索索引のフラグメントIDがありません: {url}")

    if errors:
        print(f"FAIL: {len(errors)}件")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        f"PASS: HTML {len(html_files)}ページ、問題ソース {len(SPECS)}組、"
        f"本文照合 {visible_text_checks}行、検索索引 {len(search_index)}件"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
