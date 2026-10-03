/* 分野別単語帳：答えの開閉・検索・復習記録 */
(function () {
  "use strict";
  var container = document.querySelector(".wordbook-cards");
  if (!container) return;
  var cards = Array.from(container.querySelectorAll(".word-card"));
  var search = document.querySelector("[data-wordbook-search]");
  var priority = document.querySelector("[data-wordbook-priority]");
  var status = document.querySelector("[data-wordbook-status]");
  var count = document.querySelector("[data-wordbook-count]");
  var empty = document.querySelector(".wordbook-empty");
  var answerButton = document.querySelector("[data-wordbook-answers]");
  var saveNote = document.querySelector(".wordbook-save-note");
  var key = "kyoyo-wordbook-v1";
  var states = Object.create(null);
  var searchText = new Map();
  var showingAnswers = false;

  function normalize(value) {
    return value.normalize("NFKC").toLocaleLowerCase("ja");
  }
  function load() {
    states = Object.create(null);
    try {
      var saved = JSON.parse(localStorage.getItem(key) || "{}");
      if (saved && typeof saved === "object" && !Array.isArray(saved)) {
        Object.keys(saved).forEach(function (id) {
          if (saved[id] === "review" || saved[id] === "learned") states[id] = saved[id];
        });
      }
    } catch (_) {
      saveNote.textContent = "保存データを読み込めません。この画面では復習の印を付けられます。";
    }
  }
  function save() {
    try {
      localStorage.setItem(key, JSON.stringify(states));
      saveNote.textContent = "復習の記録はこのブラウザに保存されます。同じボタンを再度押すと未習得に戻ります。";
    } catch (_) {
      saveNote.textContent = "このブラウザでは保存できません。復習の印はこの画面を開いている間だけ有効です。";
    }
  }
  function renderState(card) {
    var state = states[card.dataset.cardId] || "unlearned";
    card.dataset.state = state;
    card.querySelector("[data-card-state]").textContent = state === "learned" ? "習得済み" : state === "review" ? "要復習" : "未習得";
    card.querySelectorAll("[data-set-state]").forEach(function (button) {
      button.setAttribute("aria-pressed", String(button.dataset.setState === state));
    });
  }
  function filter() {
    var terms = normalize(search.value.trim()).split(/\s+/).filter(Boolean);
    var shown = 0;
    var learned = 0;
    cards.forEach(function (card) {
      var state = states[card.dataset.cardId] || "unlearned";
      if (state === "learned") learned++;
      var statusMatches = status.value === "all" ||
        (status.value === "unlearned" ? state !== "learned" : state === status.value);
      card.hidden = !(statusMatches && (priority.value === "all" || priority.value === card.dataset.priority) &&
        terms.every(function (term) { return searchText.get(card).includes(term); }));
      if (!card.hidden) shown++;
    });
    count.textContent = shown + " / " + cards.length + "語を表示・この分野の習得 " + learned + "語";
    empty.hidden = shown !== 0;
  }
  load();
  cards.forEach(function (card) {
    // 状態ラベル・操作文言を検索対象に入れず、用語と答えを検索する。
    searchText.set(card, normalize(card.querySelector("h3").textContent + " " + card.querySelector(".word-answer").textContent));
    renderState(card);
    card.querySelectorAll("[data-set-state]").forEach(function (button) {
      button.addEventListener("click", function () {
        var id = card.dataset.cardId;
        if (states[id] === button.dataset.setState) delete states[id];
        else states[id] = button.dataset.setState;
        save();
        renderState(card);
        filter();
        if (card.hidden) status.focus();
      });
    });
  });
  search.addEventListener("input", filter);
  priority.addEventListener("change", filter);
  status.addEventListener("change", filter);
  document.querySelector("[data-wordbook-shuffle]").addEventListener("click", function () {
    var shuffled = cards.slice();
    for (var i = shuffled.length - 1; i > 0; i--) {
      var j = Math.floor(Math.random() * (i + 1));
      var old = shuffled[i]; shuffled[i] = shuffled[j]; shuffled[j] = old;
    }
    shuffled.forEach(function (card) { container.appendChild(card); });
    filter();
  });
  answerButton.addEventListener("click", function () {
    showingAnswers = !showingAnswers;
    cards.forEach(function (card) {
      card.querySelector(".word-answer").open = showingAnswers;
    });
    answerButton.textContent = showingAnswers ? "答えをまとめて隠す" : "答えをまとめて表示";
    answerButton.setAttribute("aria-pressed", String(showingAnswers));
  });
  window.addEventListener("storage", function (event) {
    if (event.key === key || event.key === null) {
      load(); cards.forEach(renderState); filter();
    }
  });
  function revealLinkedCard() {
    var id;
    try { id = decodeURIComponent(window.location.hash.slice(1)); } catch (_) { return; }
    var target = cards.find(function (card) { return card.id === id; });
    if (!target) return;
    search.value = ""; priority.value = "all"; status.value = "all";
    filter();
    target.querySelector(".word-answer").open = true;
    target.scrollIntoView({ block: "start" });
  }
  window.addEventListener("hashchange", revealLinkedCard);
  filter();
  revealLinkedCard();
})();
