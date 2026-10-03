// 実行準備: npm install --prefix tmp/wordbook-test --no-save --no-package-lock jsdom
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { JSDOM } = require(require.resolve('jsdom', { paths: [path.resolve(__dirname, '../tmp/wordbook-test'), __dirname] }));
const root = path.resolve(__dirname, '..');
const code = fs.readFileSync(path.join(root, 'wordbook.js'), 'utf8');
const manifest = JSON.parse(fs.readFileSync(path.join(root, 'data/wordbook/manifest.json'), 'utf8'));
const key = 'kyoyo-wordbook-v1';
let checks = 0;
const check = (value, message) => { assert.ok(value, message); checks++; };
function open(name, options = {}) {
  const html = fs.readFileSync(path.join(root, '用語集', name + '.html'), 'utf8');
  const dom = new JSDOM(html, { url: 'https://example.org/' + (options.hash || ''),
    runScripts: 'outside-only', storageQuota: options.failStorage ? 0 : 5000000 });
  dom.window.HTMLElement.prototype.scrollIntoView = function () {};
  if (options.saved) dom.window.localStorage.setItem(key, options.saved);
  dom.window.eval(code);
  return dom;
}
const q = (dom, selector) => dom.window.document.querySelector(selector);
const cards = dom => [...dom.window.document.querySelectorAll('.word-card')];
const visible = dom => cards(dom).filter(card => !card.hidden);
function set(dom, selector, value, event = 'change') {
  const control = q(dom, selector);
  control.value = value;
  control.dispatchEvent(new dom.window.Event(event, { bubbles: true }));
}
for (const deck of manifest) {
  const dom = open(deck.name);
  const rows = fs.readFileSync(path.join(root, 'data/wordbook', deck.key + '.txt'), 'utf8')
    .split('\n').filter(line => line.trim() && !line.startsWith('#'));
  check(cards(dom).length === rows.length && visible(dom).length === rows.length,
    deck.name + ': source and displayed card count');
  check(cards(dom).every(card => !card.querySelector('.word-answer').open),
    deck.name + ': answers initially hidden');
  dom.window.close();
}
const physics = open('物理', { saved: JSON.stringify({ foreign: 'review' }) });
check(cards(physics).length === 40, 'physics count');
set(physics, '[data-wordbook-search]', '慣性の法則', 'input');
check(visible(physics).length === 1 && visible(physics)[0].querySelector('h3').textContent === '慣性の法則', 'search');
set(physics, '[data-wordbook-priority]', 'B');
check(visible(physics).length === 0 && !q(physics, '.wordbook-empty').hidden, 'combined filters and empty message');
set(physics, '[data-wordbook-priority]', 'all');
const card = visible(physics)[0];
const id = card.dataset.cardId;
card.querySelector('[data-set-state="review"]').click();
check(card.dataset.state === 'review' && card.querySelector('[data-set-state="review"]').getAttribute('aria-pressed') === 'true', 'review state');
card.querySelector('[data-set-state="learned"]').click();
check(card.dataset.state === 'learned' && card.querySelector('[data-set-state="review"]').getAttribute('aria-pressed') === 'false', 'exclusive learned state');
set(physics, '[data-wordbook-status]', 'unlearned');
check(visible(physics).length === 0, 'unlearned excludes learned');
set(physics, '[data-wordbook-status]', 'learned');
check(visible(physics).length === 1, 'learned filter');
const saved = physics.window.localStorage.getItem(key);
check(JSON.parse(saved).foreign === 'review' && JSON.parse(saved)[id] === 'learned', 'preserve another field');
const reloaded = open('物理', { saved });
check(q(reloaded, '#' + id).dataset.state === 'learned', 'persistence on reload');
q(reloaded, '#' + id + ' [data-set-state="learned"]').click();
check(q(reloaded, '#' + id).dataset.state === 'unlearned' && !(id in JSON.parse(reloaded.window.localStorage.getItem(key))), 'toggle back to unlearned');
card.querySelector('[data-set-state="review"]').click();
set(physics, '[data-wordbook-status]', 'review');
check(visible(physics).length === 1, 'review filter');
set(physics, '[data-wordbook-search]', '', 'input');
set(physics, '[data-wordbook-status]', 'all');
q(physics, '[data-wordbook-answers]').click();
check(cards(physics).every(c => c.querySelector('details').open), 'open all answers');
q(physics, '[data-wordbook-answers]').click();
check(cards(physics).every(c => !c.querySelector('details').open), 'close all answers');
const before = cards(physics).map(c => c.id).sort();
q(physics, '[data-wordbook-shuffle]').click();
check(JSON.stringify(cards(physics).map(c => c.id).sort()) === JSON.stringify(before), 'shuffle preserves every card');
physics.window.localStorage.setItem(key, JSON.stringify({ [id]: 'learned' }));
physics.window.dispatchEvent(new physics.window.StorageEvent('storage', { key }));
check(card.dataset.state === 'learned', 'storage event updates state');
physics.window.localStorage.clear();
physics.window.dispatchEvent(new physics.window.StorageEvent('storage', { key: null }));
check(card.dataset.state === 'unlearned', 'storage clear updates state');
const linked = open('物理', { hash: '#' + id });
check(q(linked, '#' + id + ' details').open && !q(linked, '#' + id).hidden, 'search result hash reveals answer');
set(linked, '[data-wordbook-search]', '存在しない語', 'input');
set(linked, '[data-wordbook-priority]', 'C');
linked.window.dispatchEvent(new linked.window.HashChangeEvent('hashchange'));
check(!q(linked, '#' + id).hidden && q(linked, '[data-wordbook-priority]').value === 'all', 'hash resets conflicting filters');
const corrupt = open('物理', { saved: '{invalid' });
check(cards(corrupt).every(c => c.dataset.state === 'unlearned') && q(corrupt, '.wordbook-save-note').textContent.includes('読み込めません'), 'corrupt storage fallback');
const noStorage = open('物理', { failStorage: true });
cards(noStorage)[0].querySelector('[data-set-state="review"]').click();
check(cards(noStorage)[0].dataset.state === 'review' && q(noStorage, '.wordbook-save-note').textContent.includes('保存できません'), 'storage failure keeps session working');
const biology = open('生物');
set(biology, '[data-wordbook-search]', '内耳 音', 'input');
check(visible(biology).some(c => c.querySelector('h3').textContent === '蝸牛'), 'AND search in answer text');
set(biology, '[data-wordbook-search]', 'ＡＴＰ', 'input');
check(visible(biology).some(c => c.querySelector('h3').textContent === 'ATP'), 'NFKC search');
[physics, reloaded, linked, corrupt, noStorage, biology].forEach(dom => dom.window.close());
console.log('PASS: ' + checks + ' wordbook DOM checks (no visual layout check)');
