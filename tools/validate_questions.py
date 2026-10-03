#!/usr/bin/env python3
"""問題データ（過去問・練習問題・予想問題）の構造検証。

docs/技術設計/15_テスト品質保証設計.md §5.4 で定義した validate-questions.py を実装したもの。
- 問題IDの一意性
- 必須フィールドの欠落
- type ごとの拡張フィールドの整合性
- 参照先ID（related/prerequisite）が同一コーパス内に実在するか（警告のみ）

使い方: python3 tools/validate_questions.py
"""
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS_DIR = ROOT / "data" / "questions"

REQUIRED_COMMON_FIELDS = [
    "questionId",
    "type",
    "field",
    "chapterId",
    "difficultyLevel",
    "questionText",
    "choices",
    "correctAnswer",
    "explanation",
]

TYPE_SPECIFIC_REQUIRED = {
    "pastExam": ["examYear", "examStage", "copyrightStatus"],
    "forecast": ["forecastId", "likelihoodLabel", "reviewStatus"],
    "practice": [],
}

VALID_COPYRIGHT_STATUS = {"officiallyReproducible", "urlReferenceOnly", "summaryOnly", "commentaryOnly"}
VALID_LIKELIHOOD = {"高い", "中程度", "低いが備える価値あり"}
VALID_REVIEW_STATUS = {"未レビュー", "レビュー済み", "確定版"}


def load_all_questions():
    questions = []
    if not QUESTIONS_DIR.exists():
        print(f"ERROR: {QUESTIONS_DIR} が存在しません")
        sys.exit(1)
    for path in sorted(QUESTIONS_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"ERROR: {path.name} のJSON解析に失敗: {e}")
            sys.exit(1)
        if not isinstance(data, list):
            print(f"ERROR: {path.name} はトップレベルが配列ではありません")
            sys.exit(1)
        for q in data:
            q["_sourceFile"] = path.name
            questions.append(q)
    return questions


def validate(questions):
    errors = []
    warnings = []
    seen_ids = {}

    for q in questions:
        qid = q.get("questionId", "<不明>")
        src = q.get("_sourceFile", "?")

        # 必須共通フィールド
        for field in REQUIRED_COMMON_FIELDS:
            if field not in q:
                errors.append(f"[{src}] {qid}: 必須フィールド '{field}' が欠落しています")

        # ID一意性
        if qid in seen_ids:
            errors.append(f"[{src}] questionId '{qid}' が {seen_ids[qid]} と重複しています")
        else:
            seen_ids[qid] = src

        # correctAnswer が choices の範囲内か
        if "choices" in q and "correctAnswer" in q:
            choices = q["choices"]
            ca = q["correctAnswer"]
            if not isinstance(ca, int) or not (0 <= ca < len(choices)):
                errors.append(f"[{src}] {qid}: correctAnswer({ca}) が choices の範囲外です")

        # difficultyLevel の範囲
        if "difficultyLevel" in q and not (0 <= q["difficultyLevel"] <= 5):
            errors.append(f"[{src}] {qid}: difficultyLevel は0〜5である必要があります")

        # type固有フィールド
        qtype = q.get("type")
        if qtype in TYPE_SPECIFIC_REQUIRED:
            for field in TYPE_SPECIFIC_REQUIRED[qtype]:
                if field not in q:
                    errors.append(f"[{src}] {qid}: type={qtype} に必須の '{field}' が欠落しています")
        elif qtype is not None:
            warnings.append(f"[{src}] {qid}: 未知のtype '{qtype}' です")

        if qtype == "pastExam" and "copyrightStatus" in q:
            if q["copyrightStatus"] not in VALID_COPYRIGHT_STATUS:
                errors.append(f"[{src}] {qid}: copyrightStatus '{q['copyrightStatus']}' は不正な値です")

        if qtype == "forecast":
            if q.get("likelihoodLabel") not in VALID_LIKELIHOOD:
                errors.append(f"[{src}] {qid}: likelihoodLabel は{VALID_LIKELIHOOD}のいずれかである必要があります")
            if q.get("reviewStatus") not in VALID_REVIEW_STATUS:
                errors.append(f"[{src}] {qid}: reviewStatus は{VALID_REVIEW_STATUS}のいずれかである必要があります")
            if q.get("reviewStatus") == "未レビュー":
                errors.append(f"[{src}] {qid}: 未レビューの予想を出題可能性付きで公開できません")
            if not q.get("sources") or not str(q.get("basisDescription", "")).strip():
                errors.append(f"[{src}] {qid}: 予想には具体的な確認資料と根拠説明が必要です")
            if "pastExamTrend" in q.get("forecastBasis", []) and not q.get("relatedPastExamIds"):
                errors.append(f"[{src}] {qid}: 過去問傾向を根拠にする場合は対応する過去問のIDが必要です")

        sources = q.get("sources", [])
        if not isinstance(sources, list):
            errors.append(f"[{src}] {qid}: sources は配列である必要があります")
            sources = []
        for source in sources:
            if not isinstance(source, dict):
                errors.append(f"[{src}] {qid}: 確認資料はオブジェクトで指定してください")
                continue
            url = source.get("url")
            parts = urlsplit(url) if isinstance(url, str) else None
            if not str(source.get("title", "")).strip() or not parts or parts.scheme not in {"http", "https"} or not parts.netloc:
                errors.append(f"[{src}] {qid}: 確認資料の資料名・HTTP(S) URLが不正です")
            try:
                date.fromisoformat(source.get("confirmedDate", ""))
            except (ValueError, TypeError):
                errors.append(f"[{src}] {qid}: 確認資料には実際の確認日（YYYY-MM-DD）が必要です")

    # 参照整合性（警告のみ：MVP段階では参照先が未作成の場合があるため）
    for q in questions:
        qid = q.get("questionId", "<不明>")
        for ref_field in ("relatedQuestionIds", "prerequisiteQuestionIds", "similarQuestionIds"):
            for ref_id in q.get(ref_field, []) or []:
                if ref_id not in seen_ids:
                    warnings.append(f"{qid}: {ref_field} が参照する '{ref_id}' が見つかりません")

    return errors, warnings


def main():
    questions = load_all_questions()
    print(f"読み込んだ問題数: {len(questions)}（{QUESTIONS_DIR.relative_to(ROOT)} 配下）")
    errors, warnings = validate(questions)

    if warnings:
        print(f"\n--- 警告 {len(warnings)}件 ---")
        for w in warnings:
            print(f"  WARN: {w}")

    if errors:
        print(f"\n--- エラー {len(errors)}件 ---")
        for e in errors:
            print(f"  ERROR: {e}")
        print("\nFAIL")
        sys.exit(1)

    print("\nPASS: 問題データの構造・出典メタデータを確認（内容の真偽は別途照合が必要）")
    sys.exit(0)


if __name__ == "__main__":
    main()
