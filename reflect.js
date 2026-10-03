/* 記述式・面接系科目（総合論文・企画提案・討議・面接）向けの振り返りツール。
 * 09_解答解説設計.md §5.5：模範解答の代わりに「評価観点チェックリスト」＋「振り返りメモ」を提供する。
 * 「これは人事院の公式採点基準ではなく、学習用の自己点検ツールである」旨を必ず併記すること。
 */
(function (global) {
  "use strict";

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

  /**
   * @param {HTMLElement} container
   * @param {object} opts { exerciseId: string, checklistItems: string[], notePlaceholder: string }
   */
  function renderReflectionTool(container, opts) {
    var storageKey = "reflect." + opts.exerciseId;
    var saved = null;
    try {
      var raw = window.localStorage.getItem(storageKey);
      saved = raw ? JSON.parse(raw) : null;
    } catch (e) {
      saved = null;
    }
    saved = saved || { checked: [], note: "" };

    container.innerHTML = "";
    var box = el("div", { class: "box box-imp" });
    box.appendChild(
      el("div", { class: "box-head" }, [
        el("span", { class: "box-tag", text: "自己点検" }),
        document.createTextNode("評価観点チェックリスト（人事院の公式採点基準ではありません）")
      ])
    );
    var body = el("div", { class: "box-body" });

    var list = el("ul", { style: "list-style:none; padding:0;" });
    opts.checklistItems.forEach(function (item, idx) {
      var checked = saved.checked.indexOf(idx) !== -1;
      var input = el("input", { type: "checkbox", id: storageKey + "-" + idx });
      if (checked) input.setAttribute("checked", "checked");
      var label = el("label", { for: storageKey + "-" + idx, style: "display:flex; gap:0.5rem; align-items:flex-start; min-height:44px; cursor:pointer;" }, [
        input,
        el("span", { text: item })
      ]);
      input.addEventListener("change", function () {
        save();
      });
      list.appendChild(el("li", {}, [label]));
    });
    body.appendChild(list);

    var noteLabel = el("label", { style: "display:block; margin-top:0.8rem; font-weight:700;", text: "振り返りメモ" });
    var textarea = el("textarea", {
      rows: "4",
      style: "width:100%; margin-top:0.4rem; font-family:inherit; font-size:1rem; padding:0.5rem;",
      placeholder: opts.notePlaceholder || "気づいたこと・次回への改善点を自由に書いてください。"
    });
    textarea.value = saved.note || "";
    textarea.addEventListener("input", function () {
      save();
    });

    var status = el("p", { class: "question-note", text: "" });

    function save() {
      var checkedIdx = [];
      Array.prototype.forEach.call(list.querySelectorAll("input[type=checkbox]"), function (cb, i) {
        if (cb.checked) checkedIdx.push(i);
      });
      var data = { checked: checkedIdx, note: textarea.value };
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(data));
        if (global.KyoyoHistory) {
          global.KyoyoHistory.saveReflectionNote(opts.exerciseId, textarea.value);
        }
        status.textContent = "保存しました（" + checkedIdx.length + "/" + opts.checklistItems.length + "項目チェック済み）";
      } catch (e) {
        status.textContent = "保存に失敗しました。";
      }
    }

    body.appendChild(noteLabel);
    body.appendChild(textarea);
    body.appendChild(status);
    box.appendChild(body);
    container.appendChild(box);
  }

  global.KyoyoReflect = { renderReflectionTool: renderReflectionTool };
})(window);
