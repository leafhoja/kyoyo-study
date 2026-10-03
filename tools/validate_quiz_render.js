#!/usr/bin/env node
"use strict";

// 外部DOMライブラリに依存せず、quiz.jsの描画経路だけを実行する回帰検査。
// 問題JSONの管理用メタデータや制作側参照が、動的DOMへ漏れないことを確認する。
const fs = require("fs");
const vm = require("vm");

class FakeNode {
  constructor(tag) {
    this.tagName = String(tag).toUpperCase();
    this.children = [];
    this.text = "";
    this.attrs = {};
    this.dataset = {};
    this.listeners = {};
    this.className = "";
    this.innerHTML = "";
  }

  set textContent(value) {
    this.text = String(value ?? "");
  }

  get textContent() {
    return this.text;
  }

  setAttribute(key, value) {
    this.attrs[key] = String(value);
    if (key.startsWith("data-")) {
      this.dataset[key.slice(5).replace(/-([a-z])/g, (_match, letter) => letter.toUpperCase())] = String(value);
    }
  }

  appendChild(child) {
    this.children.push(child);
    return child;
  }

  addEventListener(type, callback) {
    this.listeners[type] = callback;
  }

  querySelectorAll() {
    return [];
  }

  hasAttribute(key) {
    return Object.prototype.hasOwnProperty.call(this.attrs, key);
  }

  get open() {
    return false;
  }
}

const document = { createElement: (tag) => new FakeNode(tag) };
const window = {
  document,
  KyoyoHistory: {
    recordAnswer() {},
    recomputeLevelStats() {},
  },
};
const context = vm.createContext({ window, document, console });
vm.runInContext(fs.readFileSync(`${__dirname}/../quiz.js`, "utf8"), context, { filename: "quiz.js" });

const forbidden = /\.md\b|設計書|仕様書|制作中|今後追加予定|実装・更新時|現時点では未更新|拡充中|転記注|\bOCR\b|校正|作業メモ|原本と照合|確認日|サイト制作者|未レビュー/i;
const questionsDir = `${__dirname}/../data/questions`;
let pageCount = 0;
let questionCount = 0;
const errors = [];

function visibleText(node) {
  return [node.text, ...node.children.map(visibleText)].join(" ");
}

for (const filename of fs.readdirSync(questionsDir).filter((name) => name.endsWith(".json")).sort()) {
  const path = `${questionsDir}/${filename}`;
  const questions = JSON.parse(fs.readFileSync(path, "utf8"));
  const container = new FakeNode("div");
  context.window.KyoyoQuiz.renderQuizSet(container, questions);
  pageCount += 1;
  questionCount += questions.length;
  if (forbidden.test(visibleText(container))) {
    errors.push(`${filename}: rendered quiz text contains production metadata`);
  }
}

if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`PASS: quiz.js描画検査 ${pageCount} JSONページ、${questionCount}問、制作情報漏れ0件`);
