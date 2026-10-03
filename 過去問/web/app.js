(() => {
  // 設問番号だけでは年度・部を区別できないため、ページ名を含むキーにする。
  // 旧v1の番号だけの状態は年度を特定できないので引き継がない。
  const storageKey = "kakomon-explanation-progress-v2";
  // 通常ページ（kyoyo.js）と同じキーを使い、サイト全体で配色設定を共有する。
  const themeKey = "kyoyo.theme";
  const progress = JSON.parse(localStorage.getItem(storageKey) || "{}");
  const root = document.documentElement;
  const body = document.body;
  const isProblemPage = body.dataset.pageType === "questions";
  const progressScope = body.dataset.current || "unknown-page";
  const questionProgressKey = (card) => `${progressScope}#q${card.dataset.question}`;

  const saveProgress = () => localStorage.setItem(storageKey, JSON.stringify(progress));

  const applyTheme = (theme) => {
    if (theme) {
      root.dataset.theme = theme;
      localStorage.setItem(themeKey, theme);
    } else {
      root.removeAttribute("data-theme");
      localStorage.removeItem(themeKey);
    }
    const button = document.querySelector("#theme-toggle");
    if (button) button.textContent = theme === "dark" ? "☀" : theme === "light" ? "◐" : "🌓";
  };

  const savedTheme = localStorage.getItem(themeKey) || localStorage.getItem("kakomon-explanation-theme") || "";
  applyTheme(savedTheme);
  document.querySelector("#theme-toggle")?.addEventListener("click", () => {
    applyTheme(root.dataset.theme === "dark" ? "light" : "dark");
  });

  const questionCards = [...document.querySelectorAll(".question-card")];

  // 本文中に続けて記載されている注記は、注記の開始位置で改行する。
  const addFootnoteBreaks = () => {
    document.querySelectorAll(".document p").forEach((paragraph) => {
      const walker = document.createTreeWalker(paragraph, NodeFilter.SHOW_TEXT);
      const textNodes = [];
      while (walker.nextNode()) textNodes.push(walker.currentNode);
      textNodes.forEach((node) => {
        const match = node.nodeValue.match(/[（(]注[）)]/);
        if (!match || match.index === 0) return;
        const fragment = document.createDocumentFragment();
        fragment.append(node.nodeValue.slice(0, match.index), document.createElement("br"), node.nodeValue.slice(match.index));
        node.replaceWith(fragment);
      });
    });
  };
  addFootnoteBreaks();

  const updateQuestionButton = (card) => {
    const id = questionProgressKey(card);
    const button = card.querySelector("[data-question-done]");
    const done = Boolean(progress[id]);
    card.classList.toggle("is-done", done);
    if (button) {
      button.textContent = done ? "復習済み ✓" : "未復習";
      button.setAttribute("aria-pressed", String(done));
    }
  };
  questionCards.forEach((card) => {
    updateQuestionButton(card);
    card.querySelector("[data-question-done]")?.addEventListener("click", () => {
      const id = questionProgressKey(card);
      progress[id] = !progress[id];
      if (!progress[id]) delete progress[id];
      updateQuestionButton(card);
      saveProgress();
      updateProgressPanel();
    });
  });

  function updateProgressPanel() {
    const panel = document.querySelector("#progress-panel");
    if (!panel) return;
    if (isProblemPage) {
      panel.innerHTML = `<small>問題を解いたら、解説ページへ進んで復習を記録できます。</small>`;
      return;
    }
    const done = Object.keys(progress).length;
    const total = 162;
    const percent = Math.min(100, Math.round((done / total) * 100));
    panel.innerHTML = `<div class="progress-label"><span>全体の復習進捗</span><strong>${done}/${total}</strong></div><div class="progress-bar"><span style="width:${percent}%"></span></div><small>${percent}%　問題カードの「復習済み」で記録できます</small>`;
  }
  updateProgressPanel();

  const search = document.querySelector("#site-search");
  const empty = document.querySelector("#search-empty");
  const searchable = [...document.querySelectorAll("[data-searchable]")];
  const filter = () => {
    const query = (search?.value || "").trim().toLocaleLowerCase("ja");
    if (!query) {
      searchable.forEach((item) => item.removeAttribute("hidden"));
      questionCards.forEach((item) => item.removeAttribute("hidden"));
      if (empty) empty.hidden = true;
      return;
    }
    const matches = (item) => (item.dataset.searchable || item.textContent).toLocaleLowerCase("ja").includes(query);
    let visible = 0;
    searchable.forEach((item) => {
      const show = matches(item);
      item.toggleAttribute("hidden", !show);
      if (show) visible += 1;
    });
    questionCards.forEach((item) => {
      const show = matches(item);
      item.toggleAttribute("hidden", !show);
      if (show) visible += 1;
    });
    if (empty) empty.hidden = visible !== 0;
  };
  search?.addEventListener("input", filter);
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && document.activeElement !== search && !["INPUT", "TEXTAREA"].includes(document.activeElement?.tagName)) {
      event.preventDefault();
      search?.focus();
    }
    if (event.key === "Escape" && document.activeElement === search) {
      search.value = "";
      filter();
      search.blur();
    }
  });

  const menuButton = document.querySelector("#mobile-menu");
  const sidebar = document.querySelector("#sidebar");
  const sidebarStorageKey = "kakomon-sidebar-collapsed-v1";
  const isMobileLayout = () => window.matchMedia("(max-width: 700px)").matches;
  const updateSidebarToggle = () => {
    if (!menuButton || !sidebar) return;
    const mobile = isMobileLayout();
    const open = mobile ? sidebar.classList.contains("is-open") : !document.body.classList.contains("sidebar-collapsed");
    const label = mobile
      ? (open ? "サイドバーを閉じる" : "サイドバーを開く")
      : (open ? "サイドバーを格納" : "サイドバーを表示");
    sidebar.setAttribute("aria-hidden", String(!open));
    menuButton.setAttribute("aria-expanded", String(open));
    menuButton.setAttribute("aria-label", label);
    menuButton.title = label;
    menuButton.textContent = mobile && open ? "×" : "☰";
  };
  if (sidebar && localStorage.getItem(sidebarStorageKey) === "true") {
    document.body.classList.add("sidebar-collapsed");
  }
  menuButton?.addEventListener("click", () => {
    if (isMobileLayout()) {
      sidebar?.classList.toggle("is-open");
    } else {
      const collapsed = document.body.classList.toggle("sidebar-collapsed");
      localStorage.setItem(sidebarStorageKey, String(collapsed));
    }
    updateSidebarToggle();
  });
  sidebar?.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => {
    if (isMobileLayout()) {
      sidebar.classList.remove("is-open");
      updateSidebarToggle();
    }
  }));
  window.addEventListener("resize", updateSidebarToggle);
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isMobileLayout() && sidebar?.classList.contains("is-open")) {
      sidebar.classList.remove("is-open");
      updateSidebarToggle();
    }
  });
  updateSidebarToggle();

  document.querySelectorAll("a[href^='#q']").forEach((link) => {
    link.addEventListener("click", () => {
      const target = document.querySelector(link.getAttribute("href"));
      target?.classList.add("flash-target");
      window.setTimeout(() => target?.classList.remove("flash-target"), 1200);
    });
  });
})();
