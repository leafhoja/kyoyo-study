/* 国家総合職〈教養区分〉学習サイト 共通JS：ヘッダーnav注入・テーマ切替 */
(function () {
  "use strict";

  // このスクリプト自身のURLからサイトルートを求める（人工知能/金融ノートのai.js/fin.jsと同じ方式）
  function computeBase() {
    var scripts = document.getElementsByTagName("script");
    for (var i = 0; i < scripts.length; i++) {
      var src = scripts[i].getAttribute("src") || "";
      if (src.indexOf("kyoyo.js") !== -1) {
        var url = new URL(src, window.location.href);
        return url.href.replace(/kyoyo\.js.*$/, "");
      }
    }
    return "./";
  }

  var BASE = computeBase();

  // 部を追加したらここに1行足すだけでnavに反映される（02番§5.1）
  var NAV_PARTS = [
    { title: "ホーム", href: BASE + "index.html" },
    { title: "第0部 試験概要", href: BASE + "第0部/ch0.html" },
    { title: "第1部 知能分野", href: BASE + "第1部/ch1.html" },
    { title: "第2部 知識分野", href: BASE + "第2部/ch5.html" },
    { title: "第3部 総合論文", href: BASE + "第3部/ch9.html" },
    { title: "第4部 企画提案", href: BASE + "第4部/ch11.html" },
    { title: "第5部 討議", href: BASE + "第5部/ch13.html" },
    { title: "第6部 面接", href: BASE + "第6部/ch14.html" },
    { title: "第7部 総仕上げ", href: BASE + "第7部/ch15.html" },
    { title: "過去問・解説", href: BASE + "過去問/web/index.html" },
    { title: "用語集", href: BASE + "用語集.html" }
  ];

  function injectHeader() {
    var header = document.querySelector(".site-header");
    if (!header) return;
    var nav = header.querySelector("nav");
    if (!nav) return;

    var currentPath = window.location.pathname;
    nav.innerHTML = "";
    NAV_PARTS.forEach(function (part) {
      var a = document.createElement("a");
      a.href = part.href;
      a.textContent = part.title;
      var linkPath = new URL(part.href, window.location.href).pathname;
      if (linkPath === currentPath) {
        a.setAttribute("aria-current", "page");
      }
      nav.appendChild(a);
    });

    header.appendChild(buildSearchBox());

    var toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "theme-toggle";
    toggle.setAttribute("aria-label", "配色を切り替える");
    toggle.textContent = currentThemeLabel();
    toggle.addEventListener("click", function () {
      toggleTheme();
      toggle.textContent = currentThemeLabel();
    });
    header.appendChild(toggle);
  }

  // --- サイト内検索（12_技術基本設計.md §5.10：事前生成索引＋クライアント側フィルタ） ---
  var searchIndexPromise = null;

  function loadSearchIndex() {
    if (!searchIndexPromise) {
      searchIndexPromise = fetch(BASE + "search-index.json")
        .then(function (res) {
          if (!res.ok) throw new Error("検索索引の取得に失敗: " + res.status);
          return res.json();
        })
        .catch(function (err) {
          console.error("[kyoyo.js search]", err);
          return [];
        });
    }
    return searchIndexPromise;
  }

  function scoreEntry(entry, terms) {
    var haystack = (entry.pageTitle + " " + entry.heading + " " + entry.text).toLowerCase();
    var score = 0;
    for (var i = 0; i < terms.length; i++) {
      var t = terms[i];
      if (!t) continue;
      if (haystack.indexOf(t) === -1) return 0;
      if (entry.heading.toLowerCase().indexOf(t) !== -1) score += 3;
      if (entry.pageTitle.toLowerCase().indexOf(t) !== -1) score += 2;
      score += 1;
    }
    return score;
  }

  function buildSearchBox() {
    var wrap = document.createElement("div");
    wrap.className = "search-box";
    wrap.setAttribute("role", "search");

    var input = document.createElement("input");
    input.type = "search";
    input.placeholder = "サイト内を検索";
    input.setAttribute("aria-label", "サイト内検索");
    input.className = "search-input";

    var results = document.createElement("ul");
    results.className = "search-results";
    results.hidden = true;

    function closeResults() {
      results.hidden = true;
      results.innerHTML = "";
    }

    function renderResults(entries, query) {
      results.innerHTML = "";
      if (!entries.length) {
        var li = document.createElement("li");
        li.className = "search-no-result";
        li.textContent = "「" + query + "」に一致する結果は見つかりませんでした。";
        results.appendChild(li);
        results.hidden = false;
        return;
      }
      entries.slice(0, 10).forEach(function (entry) {
        var li = document.createElement("li");
        var a = document.createElement("a");
        a.href = BASE + entry.url;
        var titleLine = document.createElement("span");
        titleLine.className = "search-result-title";
        titleLine.textContent = entry.pageTitle + " › " + entry.heading;
        var snippet = document.createElement("span");
        snippet.className = "search-result-snippet";
        snippet.textContent = entry.text.slice(0, 80) + (entry.text.length > 80 ? "…" : "");
        a.appendChild(titleLine);
        a.appendChild(snippet);
        li.appendChild(a);
        results.appendChild(li);
      });
      results.hidden = false;
    }

    var debounceTimer = null;
    input.addEventListener("input", function () {
      var query = input.value.trim();
      window.clearTimeout(debounceTimer);
      if (!query) {
        closeResults();
        return;
      }
      debounceTimer = window.setTimeout(function () {
        loadSearchIndex().then(function (data) {
          var terms = query.toLowerCase().split(/\s+/).filter(Boolean);
          var scored = data
            .map(function (entry) {
              return { entry: entry, score: scoreEntry(entry, terms) };
            })
            .filter(function (s) {
              return s.score > 0;
            })
            .sort(function (a, b) {
              return b.score - a.score;
            })
            .map(function (s) {
              return s.entry;
            });
          renderResults(scored, query);
        });
      }, 150);
    });

    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        closeResults();
        input.blur();
      } else if (e.key === "Enter") {
        var firstLink = results.querySelector("a");
        if (firstLink) {
          window.location.href = firstLink.href;
        }
      }
    });

    document.addEventListener("click", function (e) {
      if (!wrap.contains(e.target)) closeResults();
    });

    wrap.appendChild(input);
    wrap.appendChild(results);
    return wrap;
  }

  function currentThemeLabel() {
    var t = document.documentElement.getAttribute("data-theme");
    if (t === "dark") return "🌙 ダーク";
    if (t === "light") return "☀️ ライト";
    return "🌓 自動";
  }

  function toggleTheme() {
    var current = document.documentElement.getAttribute("data-theme");
    var next = current === "dark" ? "light" : current === "light" ? null : "dark";
    if (next) {
      document.documentElement.setAttribute("data-theme", next);
      window.localStorage.setItem("kyoyo.theme", next);
    } else {
      document.documentElement.removeAttribute("data-theme");
      window.localStorage.removeItem("kyoyo.theme");
    }
  }

  function restoreTheme() {
    try {
      var saved = window.localStorage.getItem("kyoyo.theme");
      if (saved) document.documentElement.setAttribute("data-theme", saved);
    } catch (e) {
      /* localStorage無効時は既定のprefers-color-schemeに委ねる（技術基本設計12番§5.17） */
    }
  }

  restoreTheme();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", injectHeader);
  } else {
    injectHeader();
  }

  window.KYOYO_BASE = BASE;
})();
