"""
llm.py

タスク1：質問・回答の分割・要約（担当：Hiro）

仕様書（mvp-interface-spec.md）4章・5章に準拠。
- Ollamaの format: json を使用
- 話者ラベル（面接官: / 応募者:）が両方存在しない場合は 400
- JSONとして読み取れない場合は1回だけ再実行、それでもダメなら 500
- タイムアウトは180秒
"""

import json
import re

import ollama
from fastapi import HTTPException

MODEL_NAME = "qwen3:4b"  # 検証済み：think=Falseで3問約1分、精度良好
TIMEOUT_SECONDS = 180

SYSTEM_PROMPT = """あなたは面接の文字起こしを分析するアシスタントです。

入力される文字起こしには、次の2パターンがあります。
1. 「面接官:」「応募者:」のような話者ラベルが付いている場合
   → ラベルに従って、面接官の発言を質問、応募者の発言を回答として扱ってください。
2. 話者ラベルが付いておらず、地の文として続いている場合
   → 文脈から「質問にあたる部分」と「それに対する回答にあたる部分」を推測して分割してください。
     疑問形の文（〜ですか、〜を教えてください、など）や、話題を切り替える発言は
     質問である可能性が高いです。判断に迷う場合は、話題のまとまりごとに1つの
     質問・回答ペアとして扱ってください。

分割した各ペアについて、回答を1〜2文・80文字以内で要約してください。

必ず次のJSON形式のみを出力してください。説明文や前置きは一切不要です。
以下は出力形式を示す例です。この例の値をそのまま使わず、必ず入力された文字起こしの内容から実際の質問・回答を抽出してください。

入力例（ラベルあり）:
面接官: チームで大変だった経験はありますか
応募者: 納期直前にメンバーが体調不良で離脱し、残りのメンバーでタスクを再分担して対応しました

出力例:
{
  "questionAnswers": [
    {
      "questionNo": 1,
      "question": "チームで大変だった経験はありますか",
      "answer": "納期直前にメンバーが体調不良で離脱し、残りのメンバーでタスクを再分担して対応しました",
      "answerSummary": "メンバー離脱時にタスクを再分担して対応した経験がある。"
    }
  ]
}

上記はあくまで形式の例です。実際の出力では、必ずこれから渡される文字起こしの内容のみを使ってください。
質問・回答のペアが1つも見つけられない場合は、questionAnswersを空配列 [] にしてください。
"""


def validate_transcript(transcript: str) -> None:
    """文字起こしが空でないかのチェック。

    話者ラベル（面接官:/応募者:）は必須ではなくなった。
    ラベルが付いている場合はLLMがそれを手がかりに使い、
    付いていない場合はLLMが文脈から質問・回答を推測する。
    """
    if not transcript.strip():
        raise HTTPException(
            status_code=400,
            detail="文字起こしが空です",
        )


def _extract_json(raw_text: str) -> dict:
    """LLM出力からJSON部分だけを取り出してパースする"""
    text = raw_text.strip()
    text = re.sub(r"^```json\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)


def _call_ollama(transcript: str) -> dict:
    response = ollama.chat(
        model=MODEL_NAME,
        format="json",
        think=False,  # 思考モードをオフにして高速化（CLIの/no_thinkより確実）
        options={"temperature": 0},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
    )
    raw_text = response["message"]["content"]
    return _extract_json(raw_text)


def analyze_transcript(transcript: str) -> list[dict]:
    """
    文字起こし全文を受け取り、questionAnswers の配列を返す。
    仕様書 5章 POST /api/analyze の処理本体。
    """
    validate_transcript(transcript)

    parsed = None
    last_error = None

    # 1回目 + 失敗時に1回だけ再実行（仕様書：JSONとして読み取れない場合は1回だけ再実行）
    for attempt in range(2):
        try:
            parsed = _call_ollama(transcript)
            break
        except (json.JSONDecodeError, KeyError) as e:
            last_error = e
            continue
        except Exception as e:
            # Ollama自体への接続エラーなど
            raise HTTPException(
                status_code=500,
                detail=f"Ollamaとの通信でエラーが発生しました: {e}",
            )

    if parsed is None:
        raise HTTPException(
            status_code=500,
            detail=f"LLMの出力をJSONとして解析できませんでした: {last_error}",
        )

    question_answers = parsed.get("questionAnswers", [])

    # questionNoの整合性を保証（1から始まる連番・昇順）
    # answerSummaryが80文字を超える場合は切り詰める（仕様書：80文字以内）
    for i, qa in enumerate(question_answers, start=1):
        qa["questionNo"] = i
        summary = qa.get("answerSummary", "")
        if len(summary) > 80:
            qa["answerSummary"] = summary[:79] + "…"

    return question_answers
