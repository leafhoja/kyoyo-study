#!/usr/bin/env python3
"""独立したカードデータから、答えを隠せる分野別単語帳を生成する。"""
import json
import hashlib
from collections import Counter
from html import escape as esc
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data/wordbook'
OUT = ROOT / '用語集'
LEVELS = {'A': '最優先', 'B': '重要', 'C': '補強'}

def read_data():
    manifest = json.loads((DATA / 'manifest.json').read_text())
    sources = json.loads((DATA / 'sources.json').read_text())
    decks, seen = [], set()
    for meta in manifest:
        cards = []
        for n, line in enumerate((DATA / (meta['key'] + '.txt')).read_text().splitlines(), 1):
            if not line.strip() or line.startswith('#'): continue
            cols = line.split('|')
            if not 4 <= len(cols) <= 6: raise ValueError(f"{meta['key']}:{n}: 欄数不正")
            term, priority, definition, distinction = cols[:4]
            refs = cols[4].split(',') if len(cols) > 4 and cols[4] else []
            source_ids = cols[5].split(',') if len(cols) > 5 and cols[5] else meta.get('sources', [])
            ident = meta['key'] + '-' + hashlib.sha256(term.encode()).hexdigest()[:12]
            if priority not in LEVELS or not all((term, definition, distinction)):
                raise ValueError(f"{meta['key']}:{n}: 定義・注意点・重要度が必要")
            if term in seen: raise ValueError(f'用語の重複: {term}')
            seen.add(term)
            for ref in refs + source_ids:
                if ref not in sources: raise ValueError(f'出典ID不明: {ref}')
            cards.append(dict(id=ident, term=term, priority=priority, definition=definition,
                              distinction=distinction, refs=refs, sources=source_ids))
        decks.append(dict(meta, cards=cards))
    return decks, sources

def source_links(ids, sources):
    return '、'.join(f'<a href="{esc(sources[i]["url"])}">{esc(sources[i]["title"])}</a>（{esc(sources[i]["checked"])}確認）' for i in ids)

def frame(title, body, base='../'):
    return f'''<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#8b2f2f"><title>{esc(title)} — 国家総合職〈教養区分〉学習サイト</title>
<link rel="stylesheet" href="{base}kyoyo.css"><script src="{base}kyoyo.js" defer></script>
<script src="{base}wordbook.js" defer></script></head><body>
<header class="site-header"><a class="logo" href="{base}index.html">国家総合職〈教養区分〉学習サイト</a><nav></nav></header>
<main class="main-content glossary-main">{body}</main></body></html>'''

def legend():
    return '''<details class="wordbook-legend"><summary>重要度の基準</summary><p>重要度はこの単語帳の学習上の優先度です。A＝他の語や解法を理解する土台を先に定着、B＝標準的な知識や過去問に対応する論点、C＝周辺の知識を広げる補強。分野ごとに判断理由を示します。公式の指定や出題確率ではありません。</p><p>関連過去問は原本で論点を読んだ問題に限ります。誤った選択肢にも用語が登場するため、過去問への掲載と定義の正しさは別に確認します。2023〜2025年度と2026年度ではⅠ・Ⅱ部の構成が異なります。</p></details>'''

def build():
    OUT.mkdir(exist_ok=True)
    decks, sources = read_data()
    total = sum(len(d['cards']) for d in decks)
    for d in decks:
        counts = Counter(c['priority'] for c in d['cards'])
        body = f'<div class="crumbs"><a href="../index.html">ホーム</a> › <a href="../用語集.html">単語帳</a> › {esc(d["name"])}</div><h1>{esc(d["name"])}の単語帳</h1>'
        body += f'<p class="abstract">{esc(d["intro"])} {len(d["cards"])}語。まずAを説明できるようにし、B・Cへ進みます。</p>'
        body += legend() + '<dl class="priority-reasons">' + ''.join(f'<dt>{p}・{LEVELS[p]}（{counts[p]}語）</dt><dd>{esc(d["reasons"][p])}</dd>' for p in LEVELS) + '</dl>'
        body += '''<section class="wordbook-controls" aria-label="復習の設定"><label>語句を検索 <input type="search" data-wordbook-search placeholder="用語・意味を検索"></label><label>重要度 <select data-wordbook-priority><option value="all">すべて</option><option value="A">A・最優先</option><option value="B">B・重要</option><option value="C">C・補強</option></select></label><label>復習対象 <select data-wordbook-status><option value="all">すべて</option><option value="unlearned">まだ覚えていない語</option><option value="review">要復習にした語</option><option value="learned">覚えた語</option></select></label><button type="button" data-wordbook-shuffle>順番を混ぜる</button><button type="button" data-wordbook-answers>答えをまとめて表示</button><p role="status" aria-live="polite" data-wordbook-count></p><p class="wordbook-save-note">復習の記録はこのブラウザに保存されます。</p></section>'''
        body += '<h2 id="cards">思い出してから答えを開く</h2><div class="wordbook-cards">'
        for c in d['cards']:
            p = c['priority']
            body += f'''<section class="word-card" id="{c['id']}" data-card-id="{c['id']}" data-priority="{p}">
<div class="word-card-meta"><span class="word-priority priority-{p}">重要度 {p}・{LEVELS[p]}</span><span data-card-state>未習得</span></div>
<h3>{esc(c['term'])}</h3><p class="wordbook-prompt">意味・特徴を説明し、条件や似た語との違いも挙げてください。</p>
<details class="word-answer"><summary>答えと判定の注意点</summary><p><strong>覚える内容：</strong>{esc(c['definition'])}</p><p><strong>選択肢を見分ける：</strong>{esc(c['distinction'])}</p>'''
            if c['refs']: body += '<p class="glossary-source">関連過去問：' + source_links(c['refs'], sources) + '</p>'
            if c['sources']: body += '<p class="glossary-source">定義・制度の参照：' + source_links(c['sources'], sources) + '</p>'
            body += f'<p class="glossary-source"><a href="../{esc(d["chapter"])}">関連する章で学ぶ</a></p></details><div class="word-card-actions"><button type="button" data-set-state="review" aria-pressed="false">要復習</button><button type="button" data-set-state="learned" aria-pressed="false">覚えた</button></div></section>'
        body += '</div><p class="wordbook-empty" hidden>条件に一致する語がありません。検索語や復習対象を変えてください。</p><p><a href="../用語集.html">分野一覧に戻る</a></p>'
        (OUT / (d['name'] + '.html')).write_text(frame(d['name'] + 'の単語帳', body), encoding='utf-8')
    categories = {}
    for d in decks: categories.setdefault(d['category'], []).append(d)
    body = f'<div class="crumbs"><a href="index.html">ホーム</a> › 単語帳</div><h1>試験対策の分野別単語帳</h1><p class="abstract">{len(decks)}分野・{total}語。各語を自分で説明してから答えを開き、混同しやすい点まで確かめます。重要度・検索・習得状況で復習対象を絞れます。</p>' + legend()
    for cat, ds in categories.items():
        body += f'<h2>{esc(cat)}</h2><ul class="chapter-list">'
        for d in ds:
            counts = Counter(c['priority'] for c in d['cards'])
            body += f'<li><a href="用語集/{esc(d["name"])}.html">{esc(d["name"])}（{len(d["cards"])}語）</a><p>{esc(d["intro"])}<br>A {counts["A"]}語 ／ B {counts["B"]}語 ／ C {counts["C"]}語</p></li>'
        body += '</ul>'
        if cat in ('自然科学', '人文科学', '社会科学', '時事・情報'):
            hub = f'<div class="crumbs"><a href="../用語集.html">単語帳</a> › {cat}</div><h1>{cat}の単語帳</h1><ul class="chapter-list">' + ''.join(f'<li><a href="{esc(d["name"])}.html">{esc(d["name"])}（{len(d["cards"])}語）</a></li>' for d in ds) + '</ul>' + legend()
            (OUT / (('時事の基礎' if cat == '時事・情報' else cat) + '.html')).write_text(frame(cat + 'の単語帳', hub), encoding='utf-8')
    body += '<h2>使い方</h2><ol><li>Aの語を、答えを開かずに説明する。</li><li>意味が言えても注意点が曖昧なら「要復習」にする。</li><li>関連過去問や章の演習で、知識を選択肢の判定に使う。</li><li>B・Cへ進み、翌日以降に「要復習」の語を再度答える。</li></ol><p>数値を含む説明例は独自の演習用設定です。最新の統計値や制度の改正は受験年度の一次資料で確認してください。</p>'
    (ROOT / '用語集.html').write_text(frame('分野別単語帳', body, './'), encoding='utf-8')
    print(f'単語帳: {len(decks)}分野、{total}語（重複なし）')

if __name__ == '__main__': build()
