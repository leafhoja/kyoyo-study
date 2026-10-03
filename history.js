/* 国家総合職〈教養区分〉学習サイト 学習履歴（ブラウザ内保存）
 * スキーマは docs/技術設計/13_データ設計.md §5.5 に準拠。
 * 保存キーは localStorage の "kyoyo.history"。schemaVersion を持たせ、
 * 将来の仕様変更でも既存データを破棄しない（00_調査結果.md §3.4④の運用哲学を踏襲）。
 */
(function (global) {
  "use strict";

  var STORAGE_KEY = "kyoyo.history";
  var CURRENT_SCHEMA_VERSION = 1;

  function emptyHistory() {
    return {
      schemaVersion: CURRENT_SCHEMA_VERSION,
      questionRecords: {},
      chapterProgress: {},
      reflectionNotes: {}
    };
  }

  // 将来のスキーマ変更時、ここに v1→v2 等の変換関数を追加する（13番§5.7）。
  // 既存フィールドの削除・上書きはせず、フィールド追加とデフォルト値補完のみで対応する。
  var MIGRATIONS = {
    // 1: function (data) { ...v1からv2への変換... return data; }
  };

  function migrate(data) {
    var version = data.schemaVersion || 1;
    while (version < CURRENT_SCHEMA_VERSION) {
      var step = MIGRATIONS[version];
      if (!step) break;
      data = step(data);
      version += 1;
    }
    data.schemaVersion = CURRENT_SCHEMA_VERSION;
    return data;
  }

  function load() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return emptyHistory();
      var data = JSON.parse(raw);
      if (!data || typeof data !== "object") return emptyHistory();
      data.questionRecords = data.questionRecords || {};
      data.chapterProgress = data.chapterProgress || {};
      data.reflectionNotes = data.reflectionNotes || {};
      return migrate(data);
    } catch (e) {
      // 破損データでサイト全体を止めない（12番§5.17）。利用者に分かる形で警告し、空履歴を返す。
      console.warn("[history.js] 学習履歴の読み込みに失敗したため、初期状態として扱います。", e);
      return emptyHistory();
    }
  }

  function save(data) {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
    } catch (e) {
      console.warn("[history.js] 学習履歴の保存に失敗しました（ストレージ容量等）。", e);
    }
  }

  function getHistory() {
    return load();
  }

  /**
   * 問題1問の解答結果を記録する。
   * @param {string} questionId
   * @param {object} opts { result: "correct"|"incorrect"|"partial"|"needsReview"|"deferred",
   *                        detail: 自己評価コード（10番§5.2）, sawAnswer: boolean }
   */
  function recordAnswer(questionId, opts) {
    var data = load();
    var rec = data.questionRecords[questionId] || {
      attempts: 0,
      correctCount: 0,
      incorrectCount: 0,
      lastResult: null,
      lastResultDetail: null,
      sawAnswer: false,
      lastAttemptedAt: null,
      flaggedForReview: false,
      memo: ""
    };
    rec.attempts += 1;
    if (opts.result === "correct") rec.correctCount += 1;
    if (opts.result === "incorrect") rec.incorrectCount += 1;
    rec.lastResult = opts.result || rec.lastResult;
    rec.lastResultDetail = opts.detail || rec.lastResultDetail;
    if (opts.sawAnswer) rec.sawAnswer = true;
    // 誤答・要復習系の自己評価は自動的に復習対象へ（10番§5.5）
    if (
      opts.result === "incorrect" ||
      ["misunderstoodIncorrect", "carelessMistake", "luckyCorrect"].indexOf(opts.detail) !== -1
    ) {
      rec.flaggedForReview = true;
    }
    rec.lastAttemptedAt = new Date().toISOString();
    data.questionRecords[questionId] = rec;
    save(data);
    return rec;
  }

  function toggleReviewFlag(questionId, flagged) {
    var data = load();
    var rec = data.questionRecords[questionId];
    if (!rec) return;
    rec.flaggedForReview = !!flagged;
    save(data);
  }

  function getQuestionRecord(questionId) {
    return load().questionRecords[questionId] || null;
  }

  /**
   * 章の閲覧完了フラグを立てる。
   */
  function markChapterViewed(chapterId) {
    var data = load();
    var prog = data.chapterProgress[chapterId] || { viewedCompleted: false, levelReached: 0, levelStats: {} };
    prog.viewedCompleted = true;
    data.chapterProgress[chapterId] = prog;
    save(data);
  }

  /**
   * 指定した問題群（同一章・同一Level）の集計をchapterProgressへ反映する。
   * Level到達の閾値は 10_学習履歴進捗設計.md §5.3.1（2026-07-31確定）:
   *   Level0: 取り組んだことのみ / Level1-2: 自力正解率60%以上 / Level3-5: 70%以上
   */
  function recomputeLevelStats(chapterId, level, questionIds) {
    var data = load();
    var prog = data.chapterProgress[chapterId] || { viewedCompleted: false, levelReached: 0, levelStats: {} };
    var attempted = 0;
    var correct = 0;
    var selfCorrect = 0; // ヒント未使用での正解（簡易版：sawAnswer=falseかつcorrectを自力正解とみなす）
    questionIds.forEach(function (qid) {
      var rec = data.questionRecords[qid];
      if (!rec || rec.attempts === 0) return;
      attempted += 1;
      if (rec.lastResult === "correct") {
        correct += 1;
        if (!rec.sawAnswer) selfCorrect += 1;
      }
    });
    prog.levelStats[level] = { attempted: attempted, correct: correct, selfCorrect: selfCorrect };

    var threshold = level <= 0 ? 0 : level <= 2 ? 0.6 : 0.7;
    var rate = attempted > 0 ? selfCorrect / attempted : 0;
    var reached = level === 0 ? attempted > 0 : attempted > 0 && rate >= threshold;
    if (reached && level >= (prog.levelReached || 0)) {
      prog.levelReached = level;
    }
    data.chapterProgress[chapterId] = prog;
    save(data);
    return prog;
  }

  function getChapterProgress(chapterId) {
    return load().chapterProgress[chapterId] || { viewedCompleted: false, levelReached: 0, levelStats: {} };
  }

  function saveReflectionNote(key, text) {
    var data = load();
    data.reflectionNotes[key] = text;
    save(data);
  }

  function exportHistoryAsJSON() {
    return JSON.stringify(load(), null, 2);
  }

  function importHistoryFromJSON(jsonText) {
    try {
      var parsed = JSON.parse(jsonText);
      save(migrate(parsed));
      return { ok: true };
    } catch (e) {
      return { ok: false, error: String(e) };
    }
  }

  function resetAll() {
    window.localStorage.removeItem(STORAGE_KEY);
  }

  function resetQuestion(questionId) {
    var data = load();
    delete data.questionRecords[questionId];
    save(data);
  }

  global.KyoyoHistory = {
    getHistory: getHistory,
    recordAnswer: recordAnswer,
    toggleReviewFlag: toggleReviewFlag,
    getQuestionRecord: getQuestionRecord,
    markChapterViewed: markChapterViewed,
    recomputeLevelStats: recomputeLevelStats,
    getChapterProgress: getChapterProgress,
    saveReflectionNote: saveReflectionNote,
    exportHistoryAsJSON: exportHistoryAsJSON,
    importHistoryFromJSON: importHistoryFromJSON,
    resetAll: resetAll,
    resetQuestion: resetQuestion
  };
})(window);
