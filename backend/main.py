"""面接評価支援システムのバックエンドAPI。"""

from __future__ import annotations

import re
from datetime import date
from enum import Enum
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, model_validator

from llm import analyze_transcript

from excel import create_excel_filename, create_interview_excel
from storage import (
    EVALUATIONS,
    EVALUATION_ITEM_IDS,
    INTERVIEWS,
    QUESTION_ANSWERS,
    InterviewNotFoundError,
    StorageError,
    insert,
    select,
    select_max,
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


class EvaluationItemId(str, Enum):
    LOGICAL_THINKING = "logical_thinking"
    COMMUNICATION = "communication"
    COLLABORATION = "collaboration"
    ENTHUSIASM = "enthusiasm"


class EvaluationResult(CamelModel):
    evaluation_item_id: EvaluationItemId
    score: int = Field(ge=1, le=5)
    reason: str | None = None


class AnalyzeRequest(CamelModel):
    transcript: str


class AnalyzeResponse(CamelModel):
    question_answers: list[QuestionAnswer]


class SaveInterviewRequest(CamelModel):
    interview_date: date
    candidate_name: str = Field(min_length=1)
    question_answers: list[QuestionAnswer] = Field(min_length=1)
    evaluation_results: list[EvaluationResult] = Field(min_length=4, max_length=4)
    overall_comment: str | None = None

    @model_validator(mode="after")
    def validate_numbering_and_evaluations(self) -> SaveInterviewRequest:
        question_numbers = [item.question_no for item in self.question_answers]
        expected_numbers = list(range(1, len(self.question_answers) + 1))
        if question_numbers != expected_numbers:
            raise ValueError("questionNoは1から始まる連番にしてください")

        item_ids = {item.evaluation_item_id.value for item in self.evaluation_results}
        if item_ids != set(EVALUATION_ITEM_IDS):
            raise ValueError("4つの評価項目を重複なく指定してください")

        return self


class SaveInterviewResponse(CamelModel):
    interview_id: str
    save_status: bool


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    """保存APIの入力エラーをAPI仕様どおり400で返す。"""

    if request.url.path != "/api/interviews":
        return await request_validation_exception_handler(request, error)

    return JSONResponse(
        status_code=400,
        content={"detail": "入力内容を確認してください"},
    )


@app.post("/api/analyze", response_model=AnalyzeResponse, response_model_by_alias=True)
def analyze(req: AnalyzeRequest):
    """
    文字起こしをOllamaへ渡し、質問・回答へ分割して回答を要約する。
    この時点では保存しない（仕様書 5章）。
    """
    question_answers = analyze_transcript(req.transcript)
    return AnalyzeResponse(question_answers=question_answers)


def _interview_id_number(interview_id: str) -> int:
    """INT-0001形式のIDから採番用の数値を取り出す。"""

    match = re.fullmatch(r"INT-(\d+)", interview_id)
    return int(match.group(1)) if match else 0


def _next_interview_id() -> str:
    """既存IDの最大番号に1を足して新しい面接IDを発行する。"""

    latest_id = select_max(
        INTERVIEWS,
        "interview_id",
        key=_interview_id_number,
    )
    maximum = _interview_id_number(latest_id) if latest_id else 0
    return f"INT-{maximum + 1:04d}"


@app.post(
    "/api/interviews",
    response_model=SaveInterviewResponse,
    response_model_by_alias=True,
)
def save_interview(req: SaveInterviewRequest) -> SaveInterviewResponse:
    """面接内容と評価内容をCSVへ保存する。"""

    try:
        interview_id = _next_interview_id()
        interview = req.model_dump(mode="json")

        insert(
            INTERVIEWS,
            {
                "interview_id": interview_id,
                "interview_date": interview["interview_date"],
                "candidate_name": interview["candidate_name"],
                "overall_comment": interview["overall_comment"] or "",
            },
        )
        insert(
            QUESTION_ANSWERS,
            [
                {
                    "interview_id": interview_id,
                    "question_no": item["question_no"],
                    "question": item["question"],
                    "answer": item["answer"],
                    "answer_summary": item["answer_summary"],
                }
                for item in interview["question_answers"]
            ],
        )
        insert(
            EVALUATIONS,
            [
                {
                    "interview_id": interview_id,
                    "evaluation_item_id": item["evaluation_item_id"],
                    "score": item["score"],
                    "reason": item["reason"] or "",
                }
                for item in interview["evaluation_results"]
            ],
        )
    except (StorageError, KeyError, TypeError, ValueError) as error:
        raise HTTPException(
            status_code=500,
            detail="面接記録の保存に失敗しました",
        ) from error

    return SaveInterviewResponse(interview_id=interview_id, save_status=True)


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
