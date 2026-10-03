import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SOURCE = path.resolve(HERE, "../解説");

const pageOrder = [
  "解説集.md",
  "2023年度_Ⅰ部.md",
  "2023年度_Ⅱ部.md",
  "2024年度_Ⅰ部.md",
  "2024年度_Ⅱ部.md",
  "2025年度_Ⅰ部.md",
  "2025年度_Ⅱ部.md",
  "学習ガイド.md",
  "問題別目次.md",
  "確認事項.md",
];

const supportPages = ["学習ガイド.md", "問題別目次.md", "確認事項.md"];
const yearPagePattern = /^(20\d{2})年度_([ⅠⅡ])部\.md$/;
const problemSources = [
  // PDFはiframeで全ページを埋め込まず、図表などの確認が必要なページだけを
  // 原本PDFの該当ページへリンクする。ページ番号は表紙を1とする。
  { year: "2023", part: "Ⅰ", source: "../2023年度/2023_基礎能力I.md", pdf: "https://www.jinji.go.jp/content/000010518.pdf", sourcePages: [18, 19, 20, 21, 22, 25, 26, 30, 33, 34] },
  { year: "2023", part: "Ⅱ", source: "../2023年度/2023_基礎能力II.md", pdf: "https://www.jinji.go.jp/content/000010519.pdf", sourcePages: [5, 16] },
  { year: "2024", part: "Ⅰ", source: "../2024年度/2024_基礎能力I.md", pdf: "https://www.jinji.go.jp/content/900035940.pdf", sourcePages: [23, 25, 29, 31, 33, 34, 35, 37] },
  { year: "2024", part: "Ⅱ", source: "../2024年度/2024_基礎能力II.md", pdf: "https://www.jinji.go.jp/content/000002973.pdf", sourcePages: [9, 16, 32, 33] },
  { year: "2025", part: "Ⅰ", source: "../2025年度/2025_基礎能力I.md", pdf: "https://www.jinji.go.jp/content/000016198.pdf", sourcePages: [23, 24, 25, 26, 29, 30, 31, 33] },
  { year: "2025", part: "Ⅱ", source: "../2025年度/2025_基礎能力II.md", pdf: "https://www.jinji.go.jp/content/000013933.pdf", sourcePages: [8, 9, 11, 28, 32] },
];

const officialPdfUrls = new Map([
  ["../2023年度/23I部.pdf", "https://www.jinji.go.jp/content/000010518.pdf"],
  ["../2023年度/23II部.pdf", "https://www.jinji.go.jp/content/000010519.pdf"],
  ["../2024年度/24I部.pdf", "https://www.jinji.go.jp/content/900035940.pdf"],
  ["../2024年度/24II部.pdf", "https://www.jinji.go.jp/content/000002973.pdf"],
  ["../2025年度/25I部.pdf", "https://www.jinji.go.jp/content/000016198.pdf"],
  ["../2025年度/25II部.pdf", "https://www.jinji.go.jp/content/000013933.pdf"],
]);

function escapeHtml(value = "") {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function pageName(filename) {
  return filename.replace(/\.md$/u, ".html");
}

function mapHref(href) {
  if (/^(https?:|mailto:|#|javascript:)/u.test(href)) return href;
  const [pathPart, fragment] = href.split("#", 2);
  const officialPdf = officialPdfUrls.get(pathPart);
  if (officialPdf) return officialPdf + (fragment ? `#${fragment}` : "");
  return href.replace(/\.md(?=#|$)/u, ".html");
}

function renderInlineMath(latex) {
  return latex
    .replace(/\\tfrac\s*(\d)(\d)/gu, "$1/$2")
    .replace(/\\binom\{([^{}]+)\}\{([^{}]+)\}/gu, "C($1,$2)")
    .replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/gu, "$1/$2")
    .replace(/\\frac\{(.+)\}\{([^{}]+)\}/gu, "$1/$2")
    .replace(/\\frac\s*(\d)(\d)/gu, "$1/$2")
    .replace(/\\sqrt\{([^{}]+)\}/gu, "√$1")
    .replace(/\\sqrt([A-Za-z0-9]+)/gu, "√$1")
    .replaceAll("\\pi", "π")
    .replaceAll("\\times", "×")
    .replaceAll("\\cdots", "…")
    .replaceAll("\\cdot", "·")
    .replaceAll("\\qquad", "    ")
    .replaceAll("\\quad", "  ")
    .replaceAll("\\geq", "≥")
    .replaceAll("\\leq", "≤")
    .replaceAll("\\neq", "≠")
    .replaceAll("\\left", "")
    .replaceAll("\\right", "")
    .replaceAll("\\{", "{")
    .replaceAll("\\}", "}")
    .replaceAll("\\,", " ");
}

function renderDisplayMath(latex) {
  return latex.split("\n").map((line) => renderInlineMath(line)).join("\n");
}

function splitTableRow(row) {
  let value = row.trim();
  if (value.startsWith("|")) value = value.slice(1);
  if (value.endsWith("|") && !value.endsWith("\\|")) value = value.slice(0, -1);

  const cells = [];
  let cell = "";
  let escaped = false;
  for (const character of value) {
    if (character === "|" && !escaped) {
      cells.push(cell.trim());
      cell = "";
      continue;
    }
    if (character === "|" && escaped) {
      cell = cell.slice(0, -1) + "|";
      escaped = false;
      continue;
    }
    cell += character;
    escaped = character === "\\";
  }
  cells.push(cell.trim());
  return cells;
}

function isTableRow(line) {
  return /^\s*\|/u.test(line) && !/^\s*\\\|/u.test(line) && splitTableRow(line).length >= 2;
}

function isTableSeparator(line) {
  return isTableRow(line) && splitTableRow(line).every((cell) => /^\s*:?-{3,}:?\s*$/u.test(cell));
}

function validateMarkdownTableSyntax(markdown, sourceName) {
  const lines = markdown.replaceAll("\r\n", "\n").split("\n");
  let inFence = false;
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (/^\s*(```|~~~)/u.test(line)) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;
    if (/^\s*\\\|/u.test(line) && line.includes("|", 2)) {
      throw new Error(`表行の先頭が \\| でエスケープされています in ${sourceName}:${index + 1}`);
    }
    const previous = lines[index - 1] || "";
    const next = lines[index + 1] || "";
    const startsTableCandidate = isTableRow(line) && !isTableRow(previous);
    if (startsTableCandidate && isTableRow(next) && !isTableSeparator(next)) {
      throw new Error(`表の区切り行がありません in ${sourceName}:${index + 2}`);
    }
  }
}

function inlineMarkdown(source, { footnoteMarkers = false } = {}) {
  let value = escapeHtml(source);
  const stash = [];
  const hold = (html) => {
    const token = `\uE000${stash.length}\uE001`;
    stash.push(html);
    return token;
  };

  // Markdownの強調記号を文字として表示するためのエスケープを、
  // 強調処理より先に保護する（例: 原本の空欄を示す \_）。
  value = value.replace(/\\([\\_*~])/gu, (_, character) => hold(character));

  // 問題文の空欄記号は元PDFと同じ文字・幅を保ちつつ、Web上では
  // 空欄だと認識しやすいように装飾用の要素で包む。
  value = value.replace(/[□⬜](?:\uFE0E)?/gu, (marker) => {
    // 原本PDFでは、設問の語句補充欄は短い横長の枠、本文中の
    // 文補充欄は長い横長の枠になっている。元データ上はいずれも
    // □一文字なので、後者だけ周囲の文脈から長い欄として扱う。
    const sizeClass = source.length > 100 && /□(?=[。．,，])/u.test(source)
      ? "pdf-blank--long"
      : "pdf-blank--short";
    return hold(
      `<span class="pdf-blank ${sizeClass}" role="img" aria-label="空欄" title="空欄">${marker}</span>`,
    );
  });

  value = value.replace(/`([^`]+)`/gu, (_, code) => hold(`<code>${code}</code>`));
  value = value.replace(/\$([^$\n]+)\$/gu, (match, math) => {
    if (!/\\(?:frac|sqrt|pi|times|cdot|left|right|,)/u.test(math)) return match;
    return hold(`<span class="math-inline">${renderInlineMath(math)}</span>`);
  });
  value = value.replace(/!\[([^\]]*)\]\(([^)]+)\)/gu, (_, alt, href) => {
    const accessibleAlt = alt
      .replace(/（原本PDFから切り出し。著作権保護対象部分は原本どおり伏せ字）/gu, "（一部伏せ字）")
      .replace(/（原本PDFから切り出し）/gu, "")
      .trim();
    return hold(`<img src="${mapHref(href)}" alt="${accessibleAlt}">`);
  });
  value = value.replace(/\[([^\]]+)\]\(([^)]+)\)/gu, (_, label, href) =>
    hold(`<a href="${mapHref(href)}">${inlineMarkdown(label)}</a>`));
  value = value.replace(/\*\*([^*]+)\*\*/gu, "<strong>$1</strong>");
  value = value.replace(/__([^_]+)__/gu, "<strong>$1</strong>");
  value = value.replace(/~~([^~]+)~~/gu, "<del>$1</del>");
  value = value.replace(/\*([^*]+)\*/gu, "<em>$1</em>");
  value = value.replace(/_([^_]+)_/gu, "<em>$1</em>");
  if (footnoteMarkers) {
    value = value.replace(/＊(\d+)/gu, '<sup class="footnote-marker" aria-label="脚注$1">＊$1</sup>');
    value = value.replace(/＊(?!(?:No\.|\d))(?=[,，、。]|\s|[A-Za-zぁ-んァ-ヶ一-龥])/gu, '<sup class="footnote-marker" aria-label="脚注">＊</sup>');
    value = value.replace(/《中　略》/gu, '<span class="omission-inline">《中　略》</span>');
  }
  value = value.replace(/ {2,}\n/gu, "<br>");
  return value.replace(/\uE000(\d+)\uE001/gu, (_, index) => stash[Number(index)]);
}

function normalizeQuestionMarkdown(markdown) {
  return markdown
    // PDFの冊子ページ番号が本文末尾に混入している場合は表示しない。
    // 本文中の「4—5倍」など、数値範囲や通常の数式は対象にしない。
    .replace(/(?<![0-9０-９])[—–―ー]\s*[0-9０-９]{1,3}\s*[—–―ー](?=\s|$|[.,;:!?。、，；：！？)」』])/gu, "")
    .replace(/[=＝—–―ー−-]\s*[0-9０-９]{1,3}\s*[=＝—–―ー−-]\s*$/gmu, "")
    // 図を埋め込んだ問題に残る制作時の参照メモは、利用者向けには重複するため表示しない。
    .replace(/^>\s*(?:図IVの仕切り位置・空欄・札の数字|図の経路・交差点記号|立方体ア・イ・ウの穴の形状および図IIの立体配置|円の移動を示す図)は元PDFを参照。\s*$/gmu, "")
    .replace(/図I〜図IVは原本PDFの図を参照。/gu, "")
    .replace(/(?:図は|散布図は)元PDFを参照。/gu, "")
    .replace(/(?:図・表　患者数（直近5日間移動平均・特定の日）|表I・表II　年齢階級別の「旅行」の行動者率・人口構成比)（原本PDFから切り出し）\s*/gu, "")
    .replace(/表・図I・図IIは原本PDFから切り出し。\s*/gu, "")
    // 2024年度Ⅰ部の図表問題に残っていた連結OCR本文を、上に置いた校正版と重複させない。
    .replace(/^ーEを含む36.*$/gmu, "")
    .replace(/^生、2年生の4人ずつ計8人が.*$/gmu, "")
    .replace(/^116のそれぞれ異なる整数[\s\S]*?あのや\n?/mu, "")
    .replace(/^1\. 58台台台司のちあのやー3\]一$/gmu, "")
    .replace(/^1辺の長さが1の正三角形が、1辺の長さが1の正三十六角形の内側に、1辺が重な[\s\S]*?^5\. 9\/3\+7一$/mu, "")
    .replace(/^図\n\nは、ある国の2022年における年齢階層別の完全失業者数[\s\S]*?(?=\n\n<!-- PDF page 35 -->)/mu, "")
    .replace(/^表\n\nは、ある国の20132022年における、漁業生産量及び養殖業生産量[\s\S]*?(?=\n\n<!-- PDF page 36 -->)/mu, "")
    .replace(/^1\. 2013-2022年についてみると、[\s\S]*?(?=\n\n<!-- PDF page 37 -->)/mu, "")
    .replace(/^表\n\nは、ある国のAー日地域における2007年と2022年の森林面積[\s\S]*?(?=\n\n<!-- PDF page 38 -->)/mu, "")
    // 図表のOCR末尾に混入した選択肢番号・記号の断片を落とす。
    .replace(/裏表紙表紙表紙ー一のちあのや一/gu, "図を確認してください。")
    .replace(/(?:のあのや一|のあの一|のあの)(?=\s*$)/gmu, "")
    .replace(/[ーゥ一]+(?=\s*$)/gmu, "")
    // OCR sometimes concatenates consecutive circle conditions into one paragraph.
    // Keep each condition on its own block so the Web page follows the source PDF.
    .replace(/([。！？])\s*〇\s*/gu, "$1\n\n〇 ")
    // OCRで英語のアポストロフィがバッククォートとして取り込まれた箇所を戻す。
    .replace(/(?<=[A-Za-z])`(?=[A-Za-z])/gu, "'")
    // 省略記号は原本PDFの全角空白を保持する。
    .replace(/《\s*中\s*略\s*》/gu, "《中　略》")
    // 問題文中の脚注記号（*、*1など）がMarkdownの強調記法として解釈されないようにする。
    .replace(/(?<!\*)\*(?!\*)/gu, "＊")
    // 問題文では残ったバッククォートをコード記法として表示しない。
    .replaceAll("`", "");
}

function renderTable(lines, { footnoteMarkers = false, sourceName = "" } = {}) {
  const headers = splitTableRow(lines[0]);
  const alignments = splitTableRow(lines[1]).map((cell) => {
    if (cell.startsWith(":") && cell.endsWith(":")) return "center";
    if (cell.endsWith(":")) return "right";
    return "left";
  });
  const rows = lines.slice(2).map(splitTableRow);
  const tableName = sourceName ? ` in ${sourceName}` : "";
  if (alignments.length !== headers.length) {
    throw new Error(`表の列数が不一致です${tableName}: header=${headers.length}, separator=${alignments.length}`);
  }
  rows.forEach((row, index) => {
    if (row.length !== headers.length) {
      throw new Error(`表の列数が不一致です${tableName}: row=${index + 1}, expected=${headers.length}, actual=${row.length}`);
    }
  });
  const renderInline = (cell) => inlineMarkdown(cell, { footnoteMarkers });
  const head = headers.map((cell, index) => `<th style="text-align:${alignments[index] || "left"}">${renderInline(cell)}</th>`).join("");
  const body = rows.map((row) => `<tr>${row.map((cell, index) => `<td style="text-align:${alignments[index] || "left"}">${renderInline(cell)}</td>`).join("")}</tr>`).join("");
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

function renderMarkdown(markdown, { questionPage = false, problemPdf = "", sourcePages = [], companionHref = "", sourceName = "" } = {}) {
  const sourceMarkdown = questionPage === "problem" ? normalizeQuestionMarkdown(markdown) : markdown;
  const renderInline = (source) => inlineMarkdown(source, { footnoteMarkers: Boolean(questionPage) });
  const lines = sourceMarkdown.replaceAll("\r\n", "\n").split("\n");
  const output = [];
  let paragraph = [];
  let list = null;
  let code = null;
  let math = null;
  let quote = [];
  let currentQuestion = false;
  let pendingPdfPreview = "";

  const isOmissionMarker = (lines) => lines.length === 1
    && /^[《〈]\s*中\s*略\s*[》〉]$/u.test(lines[0].trim());

  const closeParagraph = () => {
    if (paragraph.length) {
      output.push(`<p>${renderInline(paragraph.join("\n"))}</p>`);
      paragraph = [];
    }
  };
  const closeList = () => {
    if (!list) return;
    output.push(`<${list.type}>${list.items.map((item) => `<li>${renderInline(item)}</li>`).join("")}</${list.type}>`);
    list = null;
  };
  const closeQuote = () => {
    if (!quote.length) return;
    const className = isOmissionMarker(quote) ? ' class="omission-marker"' : "";
    output.push(`<blockquote${className}>${quote.map((line) => `<p>${renderInline(line)}</p>`).join("")}</blockquote>`);
    quote = [];
  };
  const closeQuestion = () => {
    if (currentQuestion) {
      output.push("</section>");
      currentQuestion = false;
    }
  };
  const closeAll = () => {
    closeParagraph();
    closeList();
    closeQuote();
  };

  const pdfPreviewMarkup = (pageNumber) => problemPdf && sourcePages.includes(pageNumber)
    ? `<p class="source-preview-link"><a href="${escapeHtml(problemPdf)}#page=${pageNumber}&view=FitH" target="_blank" rel="noopener">原本PDFのこのページを開く（図・表の確認） ↗</a></p>`
    : "";

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    if (code) {
      if (/^```/u.test(line)) {
        output.push(`<pre><code class="language-${escapeHtml(code.lang)}">${escapeHtml(code.lines.join("\n"))}</code></pre>`);
        code = null;
      } else {
        code.lines.push(line);
      }
      continue;
    }
    if (math) {
      if (/^\\\]/u.test(line.trim())) {
        output.push(`<div class="math-display"><pre>${escapeHtml(renderDisplayMath(math.join("\n")))}</pre></div>`);
        math = null;
      } else {
        math.push(line);
      }
      continue;
    }
    if (/^```/u.test(line)) {
      closeAll();
      code = { lang: line.slice(3).trim() || "text", lines: [] };
      continue;
    }
    if (line.trim() === "\\[") {
      closeAll();
      math = [];
      continue;
    }
    const pdfPageMarker = line.trim().match(/^<!--\s*PDF page\s+(\d+)\s*-->$/iu);
    if (pdfPageMarker) {
      if (questionPage === "problem") {
        const pageNumber = Number(pdfPageMarker[1]);
        let next = i + 1;
        while (next < lines.length && !lines[next].trim()) next += 1;
        if (/^##\s+No\.\s*\d+/u.test(lines[next] || "")) {
          pendingPdfPreview = pdfPreviewMarkup(pageNumber);
        } else if (currentQuestion && sourcePages.includes(pageNumber)) {
          closeAll();
          output.push(pdfPreviewMarkup(pageNumber));
        }
      }
      continue;
    }
    if (/^<!--.*-->$/u.test(line.trim())) continue;
    if (/^<a\s+id=["']q\d+["']><\/a>$/u.test(line.trim())) continue;
    if (line.trim() === "<出典>") {
      // 出典ブロックはMarkdown側の確認記録として保持するが、
      // ＊No.や制作時の参照情報を利用者向けページへは出力しない。
      closeAll();
      i += 1;
      while (i < lines.length && !/^#{1,6}\s+/u.test(lines[i])) {
        i += 1;
      }
      i -= 1;
      continue;
    }
    if (!line.trim()) {
      const nextListItem = lines[i + 1]?.match(/^\s*([-*+]|\d+\.)\s+(.+)$/u);
      const nextListType = nextListItem ? (/^\d/u.test(nextListItem[1]) ? "ol" : "ul") : null;
      if (list && nextListType === list.type) continue;
      closeAll();
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/u);
    if (heading) {
      closeAll();
      const level = heading[1].length;
      const title = heading[2].trim();
      const question = title.match(/^問(\d+)[｜|\s]/u) || title.match(/^No\.\s*(\d+)/u);
      // 内部ページ対応用の見出しは、表記揺れを含めて利用者向けHTMLへ出さない。
      // 例: 「PDF p.33」「PDF page 33」「PDF 33ページ」「PDFページ33」
      const pdfPage = title.match(/^PDF\s*(?:(?:p[.．]|page|ページ)\s*)?(\d+)\s*(?:ページ)?$/iu);
      if (pdfPage) {
        let next = i + 1;
        while (next < lines.length && !lines[next].trim()) next += 1;
        if (questionPage === "problem" && level === 3 && /^##\s+No\.\s*\d+/u.test(lines[next] || "")) {
          pendingPdfPreview = pdfPreviewMarkup(Number(pdfPage[1]));
        }
        continue;
      }
      if (questionPage && level === 2 && question) {
        closeQuestion();
        currentQuestion = true;
        output.push(`<section class="question-card" id="q${question[1]}" data-question="${question[1]}">`);
        const questionAction = questionPage === "explanation"
          ? `<button class="done-button" type="button" data-question-done="q${question[1]}">未復習</button>`
          : questionPage === "problem" && companionHref
            ? `<a class="question-explanation-link" href="${companionHref}#q${question[1]}">この問題の解説 →</a>`
            : "";
        output.push(`<div class="question-tools"><span class="question-kicker">QUESTION ${question[1].padStart(2, "0")}</span>${questionAction}</div>`);
        output.push(`<h2>${renderInline(title.replace(/^No\.\s*/u, "問"))}</h2>`);
        if (pendingPdfPreview) {
          output.push(pendingPdfPreview);
          pendingPdfPreview = "";
        }
      } else {
        if (level === 1) closeQuestion();
        output.push(`<h${level}>${renderInline(title)}</h${level}>`);
      }
      continue;
    }
    if (/^\s*(\*{3,}|-{3,}|_{3,})\s*$/u.test(line)) {
      closeAll();
      output.push("<hr>");
      continue;
    }
    if (isTableRow(line) && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      closeAll();
      const tableLines = [line, lines[i + 1]];
      i += 2;
      while (i < lines.length && isTableRow(lines[i])) {
        tableLines.push(lines[i]);
        i += 1;
      }
      i -= 1;
      output.push(renderTable(tableLines, { footnoteMarkers: Boolean(questionPage), sourceName }));
      continue;
    }
    const rawTableStart = /^\s*(?:<table\b|<div\b[^>]*class=["'][^"']*\btable-wrap\b)/iu.test(line);
    if (rawTableStart) {
      closeAll();
      const rawTable = [line];
      const rawTableStartedWithDiv = /^\s*<div\b/iu.test(line);
      const rawTableIsClosed = () => {
        const markup = rawTable.join("\n");
        return markup.includes("</table>") && (!rawTableStartedWithDiv || markup.includes("</div>"));
      };
      while (i + 1 < lines.length && !rawTableIsClosed()) {
        i += 1;
        rawTable.push(lines[i]);
      }
      if (!rawTableIsClosed()) {
        throw new Error(`閉じタグ </table> のないHTML表です${sourceName ? ` in ${sourceName}` : ""}`);
      }
      output.push(rawTable.join("\n"));
      continue;
    }
    const listItem = line.match(/^\s*([-*+]|\d+\.)\s+(.+)$/u);
    if (listItem) {
      closeParagraph();
      closeQuote();
      const type = /^\d/u.test(listItem[1]) ? "ol" : "ul";
      if (!list || list.type !== type) {
        closeList();
        list = { type, items: [] };
      }
      list.items.push(listItem[2]);
      continue;
    }
    const quoteLine = line.match(/^>\s?(.*)$/u);
    if (quoteLine) {
      closeParagraph();
      closeList();
      quote.push(quoteLine[1]);
      continue;
    }
    closeList();
    closeQuote();
    paragraph.push(line);
  }
  closeAll();
  closeQuestion();
  return output.join("\n");
}

function pageMeta(filename) {
  const year = filename.match(yearPagePattern);
  if (year) {
    return { filename, href: pageName(filename), year: year[1], part: year[2], kind: "exam", questionPage: true };
  }
  const labels = {
    "解説集.md": "解説集の入口",
    "学習ガイド.md": "学習ガイド",
    "問題別目次.md": "問題別目次",
    "確認事項.md": "確認事項",
  };
  return { filename, href: pageName(filename), kind: "support", label: labels[filename] || filename.replace(/\.md$/u, "") };
}

function problemPageMeta({ year, part, source, pdf, sourcePages }) {
  return {
    filename: `${year}年度_${part}部_問題.html`,
    href: `${year}年度_${part}部_問題.html`,
    year,
    part,
    kind: "questions",
    source,
    pdf,
    sourcePages,
    explanationHref: `${year}年度_${part}部.html`,
  };
}

function navMarkup(index, current) {
  const exams = index.filter((page) => page.kind === "exam");
  const questions = index.filter((page) => page.kind === "questions");
  const supports = index.filter((page) => page.kind === "support" && page.filename !== "解説集.md");
  const years = ["2023", "2024", "2025"];
  const yearGroups = years.map((year) => {
    const pages = exams.filter((page) => page.year === year);
    const problemPages = questions.filter((page) => page.year === year);
    return `<div class="nav-year"><p>${year}年度</p>${pages.map((page) => `<a class="nav-link ${page.href === current ? "is-current" : ""}" href="${page.href}"><span>${page.part}部</span><small>解説</small></a>`).join("")}${problemPages.map((page) => `<a class="nav-link nav-problem ${page.href === current ? "is-current" : ""}" href="${page.href}"><span>↳ ${page.part}部</span><small>問題</small></a>`).join("")}</div>`;
  }).join("");
  const studyLinks = [
    ["第0部　試験概要", "../../第0部/ch0.html"],
    ["第1部　知能分野", "../../第1部/ch1.html"],
    ["第2部　知識分野", "../../第2部/ch5.html"],
    ["第3〜6部　記述・面接", "../../第3部/ch9.html"],
    ["第7部　総仕上げ", "../../第7部/ch15.html"],
  ].map(([label, href]) => `<a class="nav-link nav-study" href="${href}">${label}</a>`).join("");
  return `<nav class="site-nav" aria-label="サイトナビゲーション"><a class="nav-back" href="../../index.html">← 学習サイト本体へ戻る</a><a class="nav-home ${current === "index.html" ? "is-current" : ""}" href="index.html">⌂　過去問トップ</a><p class="nav-label">年度別 解説／問題</p>${yearGroups}<p class="nav-label">学習ツール</p>${supports.map((page) => `<a class="nav-link ${page.href === current ? "is-current" : ""}" href="${page.href}">${page.label}</a>`).join("")}<p class="nav-label">講義へ戻る</p>${studyLinks}</nav>`;
}

function shell({ title, body, index, current, pageType = "support" }) {
  return `<!doctype html>
<html lang="ja" data-page-type="${pageType}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="theme-color" content="#0d6b6b">
  <title>${escapeHtml(title)}｜国家総合職 教養区分 過去問解説</title>
  <link rel="stylesheet" href="style.css">
</head>
<body data-current="${current}" data-page-type="${pageType}">
  <a class="skip-link" href="#main-content">本文へ移動</a>
  <header class="topbar">
    <div class="topbar-inner">
      <button class="mobile-menu" id="mobile-menu" type="button" aria-controls="sidebar" aria-label="サイドバーを格納" aria-expanded="true" title="サイドバーを格納">☰</button>
      <a class="brand" href="../../index.html"><span class="brand-mark">教</span><span><strong>教養区分</strong><small>過去問・解説ノート</small></span></a>
      <div class="top-actions">
        <label class="search-box" for="site-search"><span aria-hidden="true">⌕</span><input id="site-search" type="search" placeholder="${pageType === "questions" ? "問題を検索…" : "解説を検索…"}" autocomplete="off"><kbd>/</kbd></label>
        <button class="icon-button" id="theme-toggle" type="button" aria-label="表示テーマを切り替える">◐</button>
      </div>
    </div>
  </header>
  <div class="layout">
    <aside class="sidebar" id="sidebar">${navMarkup(index, current)}<div class="progress-panel" id="progress-panel"></div></aside>
    <main class="main-content" id="main-content">${body}</main>
  </div>
  <div class="search-overlay" id="search-empty" hidden>検索条件に一致する問題がありません。</div>
  <script src="app.js" defer></script>
</body>
</html>`;
}

const pendingWrites = new Map();

// ビルド単体でも、Markdownの内部記録が利用者向けHTMLへ流出しないようにする。
// 「PDF 33ページ」のような学習上の原本ページ情報や、図表確認用の公式PDFリンクは許可し、
// 内部マーカー・制作工程・出典識別子だけを公開出力の境界で拒否する。
function assertPublicHtml(html, filename) {
  const forbidden = [
    [/<!--\s*PDF page\s+\d+\s*-->/iu, "内部PDFページマーカー"],
    [/\bsourcePages\b/u, "内部PDFページ定義"],
    [/<出典>/u, "出典ブロック"],
    [/source-attribution/u, "出典識別子"],
    [/＊No\.\s*\d+/u, "出典識別子"],
    [/<h[1-6][^>]*>\s*PDF\s*(?:(?:p[.．]|page|ページ)\s*)?\d+\s*(?:ページ)?\s*<\/h[1-6]>/iu, "PDFページ見出し"],
    [/(?<![A-Za-z])PDF\s*(?:(?:p[.．]|page)\s*\d+)/iu, "作業用PDFページ表記"],
    [/／PDF\s*[0-9０-９]+\s*ページ/iu, "旧形式の原本ページ表記"],
    [/原本：PDF\s*[0-9０-９]+\s*ページ/iu, "旧形式の原本ページ表記"],
    [/作成・確認日|確認日[：:]/u, "確認日メタデータ"],
    [/(?<![A-Za-z0-9_])[^\s"<>]+\.md\b/iu, "制作側Markdownファイル名"],
    [/プロジェクト仕様書|設計書/u, "制作側設計情報"],
    [/原本と照合しています/u, "制作時の照合メモ"],
    [/原本PDFから切り出し|元PDFを参照|原本PDFの図を参照/u, "制作時の参照メモ"],
    [/転記注|転記時|OCR層を基礎に|読み取り補助|原本画像を確認|画像で確認した|作業メモ/u, "制作時の転記メモ"],
    [/(?<![A-Za-z])OCR(?![A-Za-z])/iu, "OCR工程情報"],
  ];
  for (const [pattern, label] of forbidden) {
    if (pattern.test(html)) {
      throw new Error(`${filename}: 公開HTMLに${label}が含まれています`);
    }
  }

  // Markdownの強調などで内部語がタグをまたいでも、利用者に見える本文として拒否する。
  const visibleText = html
    .replace(/<script\b[\s\S]*?<\/script>/giu, "")
    .replace(/<style\b[\s\S]*?<\/style>/giu, "")
    .replace(/<[^>]+>/gu, "");
  const visibleForbidden = [
    [/プロジェクト仕様書|設計書/u, "表示本文の制作側設計情報"],
    [/作成・確認日|確認日[：:]/u, "表示本文の確認日メタデータ"],
    [/サイト制作者|未レビュー/u, "表示本文の管理用メタデータ"],
    [/制作中|今後追加予定|実装・更新時|現時点では未更新|拡充中|Phase 2/u, "表示本文の制作進捗情報"],
    [/転記注|転記時|OCR層を基礎に|読み取り補助|原本画像を確認|画像で確認した|作業メモ|原本と照合/u, "表示本文の制作時メモ"],
    [/(?<![A-Za-z])OCR(?![A-Za-z])/iu, "表示本文のOCR工程情報"],
  ];
  for (const [pattern, label] of visibleForbidden) {
    if (pattern.test(visibleText)) {
      throw new Error(`${filename}: ${label}が含まれています`);
    }
  }
}

function writePublicHtml(filename, html) {
  assertPublicHtml(html, filename);
  pendingWrites.set(filename, html);
}

function homeBody(index, questionCounts) {
  const exams = index.filter((page) => page.kind === "exam");
  const questions = index.filter((page) => page.kind === "questions");
  const cards = ["2025", "2024", "2023"].map((year, yearIndex) => {
    const pages = exams.filter((page) => page.year === year);
    const problemPages = questions.filter((page) => page.year === year);
    const count = questionCounts.get(year) || 0;
    return `<article class="year-card" data-searchable="${year}年度 基礎能力試験 Ⅰ部 Ⅱ部 解説 問題 ${yearIndex === 0 ? "最新" : ""}"><div class="year-card-top"><span class="year-badge">${year}</span><span class="year-status">${yearIndex === 0 ? "最新年度" : "演習用"}</span></div><h2>${year}年度</h2><p>Ⅰ部・Ⅱ部、${count}問の問題と解説。</p><div class="card-links">${pages.map((page) => { const problem = problemPages.find((item) => item.part === page.part); return `<div class="card-link-row"><a href="${page.href}"><span>${page.part}部</span>解説<b>→</b></a><a class="problem-link" href="${problem.href}">問題だけ</a></div>`; }).join("")}</div></article>`;
  }).join("");
  const support = index.filter((page) => page.kind === "support" && page.filename !== "解説集.md").map((page) => `<a class="tool-card" data-searchable="${page.label}" href="${page.href}"><span class="tool-icon">${page.filename.startsWith("学") ? "✦" : page.filename.startsWith("問") ? "▦" : "✓"}</span><span><strong>${page.label}</strong><small>${page.filename.startsWith("学") ? "初回の取り組み方・解法・復習" : page.filename.startsWith("問") ? "全162問をテーマから探す" : "原本の欠落・時点・検証内容"}</small></span><b>→</b></a>`).join("");
  return `<section class="hero"><div class="eyebrow">NATIONAL CIVIL SERVICE EXAM</div><h1>過去問を、<em>解ける知識</em>に変える。</h1><p>まず問題だけを解き、必要なときに解説へ移れる、国家総合職〈教養区分〉の学習サイトです。</p><div class="hero-actions"><a class="primary-button" href="2025年度_Ⅰ部_問題.html">最新年度の問題から始める <span>→</span></a><a class="text-button" href="問題別目次.html">問題を探す</a></div><div class="hero-note"><span>◈</span><span><strong>全162問を収録</strong><br>2023〜2025年度・Ⅰ部／Ⅱ部</span></div></section><section class="section-block"><div class="section-heading"><div><span class="eyebrow">YEAR BY YEAR</span><h2>年度別に読む・解く</h2></div><span class="section-count">3 YEARS</span></div><div class="year-grid">${cards}</div></section><section class="section-block tools-section"><div class="section-heading"><div><span class="eyebrow">STUDY TOOLS</span><h2>学習を支えるページ</h2></div></div><div class="tools-grid">${support}</div></section><section class="principle"><span class="principle-mark">“</span><p>先に問題だけで考え、<br><strong>必要なときに解説へ進む。</strong></p></section>`;
}

function withoutAnswerKey(markdown) {
  const lines = markdown.replaceAll("\r\n", "\n").split("\n");
  const start = lines.findIndex((line) => /^##\s+試験問題\s*$/u.test(line.trim()));
  const answerKey = lines.findIndex((line, index) => index > start && /^##\s+CP-\d{4}.*正答番号表/u.test(line.trim()));
  const content = lines.slice(start >= 0 ? start + 1 : 0, answerKey >= 0 ? answerKey : lines.length);
  return content.join("\n").replace(/^###\s+注意事項\s*$/mu, "## 注意事項");
}

function pageSwitcher({ href, label, description, tone }) {
  return `<div class="page-switcher ${tone}"><div><span class="eyebrow">${tone === "problem-mode" ? "QUESTION MODE" : "EXPLANATION MODE"}</span><strong>${description}</strong></div><a class="switcher-button" href="${href}">${label}<span>→</span></a></div>`;
}

function pageTitleFromMarkdown(markdown, fallback) {
  const match = markdown.match(/^#\s+(.+)$/mu);
  return match ? match[1].trim() : fallback;
}

fs.mkdirSync(HERE, { recursive: true });
const index = [...pageOrder.map(pageMeta), ...problemSources.map(problemPageMeta)];

for (const page of problemSources) {
  const source = fs.readFileSync(path.resolve(HERE, page.source), "utf8");
  validateMarkdownTableSyntax(source, page.source);
  const markedPages = new Set(
    [...source.matchAll(/^<!--\s*PDF page\s+(\d+)\s*-->$/gmu)].map((match) => Number(match[1])),
  );
  const missingPages = page.sourcePages.filter((pageNumber) => !markedPages.has(pageNumber));
  if (missingPages.length) {
    throw new Error(`${page.source}: sourcePages に内部ページマーカーのないページがあります: ${missingPages.join(", ")}`);
  }
}

const questionCounts = new Map();
for (const page of problemSources) {
  const source = fs.readFileSync(path.resolve(HERE, page.source), "utf8");
  const count = [...source.matchAll(/^##\s+No\.\s*\d+/gmu)].length;
  questionCounts.set(page.year, (questionCounts.get(page.year) || 0) + count);
}

for (const page of index) {
  if (page.kind === "questions") {
    const markdown = fs.readFileSync(path.resolve(HERE, page.source), "utf8");
    validateMarkdownTableSyntax(markdown, page.source);
    const title = `${page.year}年度 基礎能力試験${page.part}部 問題`;
    const problemMarkdown = withoutAnswerKey(markdown);
    const body = `${pageSwitcher({ href: page.explanationHref, label: "解説を見る", description: "問題文と選択肢だけを表示中", tone: "problem-mode" })}<h1>${title}</h1><p class="problem-lead">先に自力で解いてから、必要な問題だけ解説へ進みます。正答番号・解法はこのページには表示していません。<a href="${page.pdf}" target="_blank" rel="noopener">人事院公式の原本PDFを開く ↗</a></p>${renderMarkdown(problemMarkdown, { questionPage: "problem", problemPdf: page.pdf, sourcePages: page.sourcePages, companionHref: page.explanationHref, sourceName: page.source })}`;
    const html = shell({ title, body: `<article class="document problem-page">${body}</article>`, index, current: page.href, pageType: page.kind });
    writePublicHtml(page.href, html);
    continue;
  }
  const markdown = fs.readFileSync(path.join(SOURCE, page.filename), "utf8");
  validateMarkdownTableSyntax(markdown, page.filename);
  const title = pageTitleFromMarkdown(markdown, page.label || page.filename);
  const companion = page.kind === "exam" ? index.find((item) => item.kind === "questions" && item.year === page.year && item.part === page.part) : null;
  const switcher = companion ? pageSwitcher({ href: companion.href, label: "問題だけを見る", description: "解説を表示中", tone: "explanation-mode" }) : "";
  const body = renderMarkdown(markdown, { questionPage: page.questionPage ? "explanation" : false, sourceName: page.filename });
  const html = shell({ title, body: `<article class="document">${switcher}${body}</article>`, index, current: page.href, pageType: page.kind });
  writePublicHtml(page.href, html);
}

const home = shell({ title: "過去問解説集", body: homeBody(index, questionCounts), index, current: "index.html", pageType: "home" });
writePublicHtml("index.html", home);
for (const [filename, html] of pendingWrites) {
  fs.writeFileSync(path.join(HERE, filename), html);
}
console.log(`Generated ${index.length + 1} HTML pages in ${HERE}`);
