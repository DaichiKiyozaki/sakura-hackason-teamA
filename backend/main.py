"""
main.py（抜粋：/api/analyze エンドポイント）

storage.py, excel.py の担当者が実装するエンドポイントは
このファイルに合流させる想定（仕様書 9章のディレクトリ構成）。
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from llm import analyze_transcript

from urllib.parse import quote

from excel import create_excel_filename, create_interview_excel
from storage import (
    INTERVIEWS,
    QUESTION_ANSWERS,
    InterviewNotFoundError,
    StorageError,
    select,
)

app = FastAPI(title="面接評価支援システム")


# ------------------------------------------------------------
# 仕様書 4章の型定義（TypeScript）をPydanticに対応させたもの
# APIキーはcamelCase、Python内部はsnake_caseに変換（仕様書5章）
# ------------------------------------------------------------
def to_camel(snake_str: str) -> str:
    parts = snake_str.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


class CamelModel(BaseModel):
    class Config:
        alias_generator = to_camel
        populate_by_name = True


class QuestionAnswer(CamelModel):
    question_no: int
    question: str
    answer: str
    answer_summary: str


class AnalyzeRequest(CamelModel):
    transcript: str


class AnalyzeResponse(CamelModel):
    question_answers: list[QuestionAnswer]


@app.post("/api/analyze", response_model=AnalyzeResponse, response_model_by_alias=True)
def analyze(req: AnalyzeRequest):
    """
    文字起こしをOllamaへ渡し、質問・回答へ分割して回答を要約する。
    この時点では保存しない（仕様書 5章）。
    """
    question_answers = analyze_transcript(req.transcript)
    return AnalyzeResponse(question_answers=question_answers)


@app.get("/health")
def health():
    return {"status": "ok"}

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@app.get("/api/interviews/{interview_id}/excel")
def download_interview_excel(interview_id: str) -> StreamingResponse:
    """保存済みの面接記録をExcelに変換して返す。"""

    try:
        interviews = select(
            INTERVIEWS,
            ("interview_date", "candidate_name", "overall_comment"),
            interview_id=interview_id,
        )
        if not interviews:
            raise InterviewNotFoundError(interview_id)

        question_answers = select(
            QUESTION_ANSWERS,
            ("question_no", "question", "answer_summary"),
            interview_id=interview_id,
        )
        question_answers.sort(key=lambda item: int(item["question_no"]))

        interview = {
            **interviews[0],
            "question_answers": question_answers,
        }
        # Excelはディスクへ保存せず、メモリ上のBytesIOとして受け取る。
        excel_file = create_interview_excel(interview)
    except InterviewNotFoundError as error:
        raise HTTPException(status_code=404, detail="面接記録が見つかりません") from error
    except (StorageError, OSError, KeyError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Excel出力に失敗しました") from error

    # 日本語ファイル名をHTTPヘッダーで安全に返せるようURLエンコードする。
    filename = create_excel_filename(
        interview["candidate_name"],
        interview["interview_date"],
    )
    encoded_filename = quote(filename, safe="")
    return StreamingResponse(
        excel_file,
        media_type=EXCEL_MEDIA_TYPE,
        headers={
            # filename*= を使うことで、日本語を含むファイル名を扱える。
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
        },
    )
