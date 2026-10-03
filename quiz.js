/* 国家総合職〈教養区分〉学習サイト 問題演習UI
 * 挙動は docs/内容設計/09_解答解説設計.md §5.1〜5.2、
 * 実装方式は docs/技術設計/11_UI_UX設計.md §5.1〜5.2（details/summary基本＋JSハイブリッド）に準拠。
 * 現在は、多肢選択式・正誤問題を対象とする（記述式・面接系の評価観点チェックリストUIは別実装）。
 */
(function (global) {
  "use strict";

  var LEVEL_LABELS = {
    0: "はじめの一歩",
    1: "基礎確認",
    2: "基本",
    3: "標準",
    4: "実戦",
    5: "高難度"
  };

  var RESULT_BUTTONS = [
    { code: "correct", label: "正解" },
    { code: "incorrect", label: "不正解" },
    { code: "partial", label: "一部正解" },
    { code: "needsReview", label: "要復習" },
    { code: "deferred", label: "判断保留" }
  ];

  function el(tag, attrs, children) {
    var node = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      if (k === "text") node.textContent = attrs[k];
      else node.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) {
      if (c) node.appendChild(c);
    });
    return node;
  }

  function renderQuestion(q, levelGroups) {
    var isForecast = q.type === "forecast";
    var isPastExam = q.type === "pastExam";
    var wrapperClass = "question";
    if (isForecast) wrapperClass += " question-forecast";
    if (isPastExam) wrapperClass += " question-pastexam";
    var wrapper = el("section", {
      class: wrapperClass,
      id: "q-" + q.questionId
    });

    var levelBadge = el("span", {
      class: "lv lv-" + q.difficultyLevel,
      text: "Level" + q.difficultyLevel + "　" + (LEVEL_LABELS[q.difficultyLevel] || "")
    });
    var fieldBadge = el("span", { text: q.field || "" });
    var headChildren = [levelBadge, fieldBadge];
    if (isForecast) {
      headChildren.push(
        el("span", {
          class: "forecast-badge",
          text: "予想問題（出題可能性：" + (q.likelihoodLabel || "中程度") + "）"
        })
      );
    }
    if (q.type === "pastExam") {
      headChildren.push(
        el("span", {
          class: "pastexam-badge",
          text: "過去問（" + (q.examYear || "") + " " + (q.examSubject || "") + " " + (q.questionNumber || "") + "）"
        })
      );
    }
    wrapper.appendChild(el("div", { class: "question-head" }, headChildren));

    var body = el("div", { class: "question-body" });
    body.appendChild(el("p", { text: q.questionText }));

    if (isForecast) {
      var forecastBox = el("div", { class: "box-forecast" });
      forecastBox.appendChild(el("div", { class: "box-head", text: "予想根拠（制作者による予想であり、公式に確定した出題内容ではありません）" }));
      var forecastBody = el("div", { class: "box-body" });
      if (q.basisDescription) {
        forecastBody.appendChild(el("p", { text: q.basisDescription }));
      }
      if (q.targetExamYear) {
        forecastBody.appendChild(el("p", { text: "想定対象：" + q.targetExamYear }));
      }
      forecastBox.appendChild(forecastBody);
      body.appendChild(forecastBox);
    }

    if (q.difficultyLevel === 0) {
      body.appendChild(
        el("p", {
          class: "question-note",
          text: "Level0：正解することより、形式に慣れることを重視してください。ヒントはいつでも見て構いません。"
        })
      );
    } else {
      body.appendChild(
        el("p", { class: "question-note", text: "自分の考えを選んでから「解答・解説を見る」を開いてください。" })
      );
    }

    var choicesList = el("ul", { class: "choices" });
    var radioName = "choice-" + q.questionId;
    q.choices.forEach(function (choiceText, idx) {
      var input = el("input", { type: "radio", name: radioName, value: String(idx) });
      var label = el("label", { class: "choice-label" }, [input, el("span", { text: choiceText })]);
      choicesList.appendChild(el("li", {}, [label]));
    });
    body.appendChild(choicesList);

    var details = el("details", { class: "answer-details" });
    var summary = el("summary", { class: "answer-toggle", text: "解答・解説を見る" });
    details.appendChild(summary);

    var panel = el("div", { class: "answer-panel" });
    panel.appendChild(
      el("p", {}, [
        el("strong", { text: "正解： " }),
        el("span", { text: q.choices[q.correctAnswer] })
      ])
    );
    panel.appendChild(el("p", { text: q.explanation }));

    if (q.hints && q.hints.length) {
      q.hints.forEach(function (hintText, i) {
        var hd = el("details", { class: "hint-stage" });
        hd.appendChild(el("summary", { text: "ヒント" + (i + 1) }));
        hd.appendChild(el("p", { text: hintText }));
        panel.appendChild(hd);
      });
    }

    var selfRecord = el("div", { class: "self-record" });
    var resultBadge = el("span", { class: "result-badge", "aria-live": "polite" });

    RESULT_BUTTONS.forEach(function (btn) {
      var button = el("button", {
        type: "button",
        class: "record-btn",
        "aria-pressed": "false",
        "data-code": btn.code,
        text: btn.label
      });
      button.addEventListener("click", function () {
        Array.prototype.forEach.call(selfRecord.querySelectorAll(".record-btn"), function (b) {
          b.setAttribute("aria-pressed", "false");
        });
        button.setAttribute("aria-pressed", "true");
        var sawAnswer = details.hasAttribute("open") || details.open;
        global.KyoyoHistory.recordAnswer(q.questionId, { result: btn.code, sawAnswer: sawAnswer });
        resultBadge.textContent = btn.code === "correct" ? "記録：正解" : btn.code === "incorrect" ? "記録：不正解" : "記録：" + btn.label;
        resultBadge.className =
          "result-badge " + (btn.code === "correct" ? "is-correct" : btn.code === "incorrect" ? "is-incorrect" : "");
        // Level別集計（10_学習履歴進捗設計.md§5.3）を、同じ章・同じLevelの全問題IDで再計算する。
        if (levelGroups) {
          var key = q.chapterId + "|" + q.difficultyLevel;
          var ids = levelGroups[key];
          if (ids) {
            global.KyoyoHistory.recomputeLevelStats(q.chapterId, q.difficultyLevel, ids);
          }
        }
      });
      selfRecord.appendChild(button);
    });
    panel.appendChild(selfRecord);
    panel.appendChild(resultBadge);

    details.appendChild(panel);

    // 開いた時点で「解答を見た」として学習履歴のsawAnswer判定に使えるよう記録する。
    // ただし自己採点ボタンを押すまでは questionRecords 自体は作らない（09番§5.1の流れ：
    // 回答→解答閲覧→正誤自己記録、の順を尊重し、閲覧のみでの誤カウントを避ける）。
    details.addEventListener("toggle", function () {
      if (details.open) {
        wrapper.dataset.answerViewed = "true";
      }
    });

    body.appendChild(details);
    wrapper.appendChild(body);
    return wrapper;
  }

  function buildLevelGroups(questions) {
    var groups = {};
    questions.forEach(function (q) {
      var key = q.chapterId + "|" + q.difficultyLevel;
      if (!groups[key]) groups[key] = [];
      groups[key].push(q.questionId);
    });
    return groups;
  }

  function renderQuizSet(container, questions) {
    container.innerHTML = "";
    var levelGroups = buildLevelGroups(questions);
    questions.forEach(function (q) {
      container.appendChild(renderQuestion(q, levelGroups));
    });
  }

  function loadAndRender(container, jsonUrl) {
    fetch(jsonUrl)
      .then(function (res) {
        if (!res.ok) throw new Error("問題データの取得に失敗しました: " + res.status);
        return res.json();
      })
      .then(function (questions) {
        renderQuizSet(container, questions);
      })
      .catch(function (err) {
        container.innerHTML = "";
        container.appendChild(
          el("p", { class: "question-note", text: "問題を読み込めませんでした。時間をおいて再度お試しください。" })
        );
        console.error("[quiz.js]", err);
      });
  }

  global.KyoyoQuiz = {
    renderQuizSet: renderQuizSet,
    loadAndRender: loadAndRender
  };
})(window);
