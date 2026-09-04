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
from pydantic import AliasChoices, BaseModel, Field, model_validator

from llm import analyze_transcript

from excel import create_excel_filename, create_interview_excel
from storage import (
    EVALUATIONS,
    EVALUATION_ITEM_IDS,
    INTERVIEWS,
    QUESTION_ANSWERS,
    StorageError,
    insert,
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
    COMMUNICATION = "communication"
    PROBLEM_SOLVING = "problem_solving"
    LOGICAL_THINKING = "logical_thinking"
    INITIATIVE = "initiative"
    COLLABORATION = "collaboration"


class EvaluationResult(CamelModel):
    evaluation_item_id: EvaluationItemId
    score: int = Field(ge=1, le=5)
    reason: str | None = None


class AnalyzeRequest(CamelModel):
    transcript: str


class AnalyzeResponse(CamelModel):
    question_answers: list[QuestionAnswer]


class ExportInterviewRequest(CamelModel):
    interview_date: date
    candidate_name: str = Field(min_length=1)
    interviewer_name: str = Field(min_length=1)
    question_answers: list[QuestionAnswer] = Field(min_length=1)
    overall_comment: str | None = Field(
        default=None,
        validation_alias=AliasChoices("overallComment", "overallcomment"),
    )

    @model_validator(mode="after")
    def validate_question_numbering(self) -> ExportInterviewRequest:
        question_numbers = [item.question_no for item in self.question_answers]
        expected_numbers = list(range(1, len(self.question_answers) + 1))
        if question_numbers != expected_numbers:
            raise ValueError("questionNoは1から始まる連番にしてください")

        return self


class SaveInterviewRequest(CamelModel):
    """将来DB保存を再びAPIへ組み込む場合に使用する入力モデル。"""

    interview_date: date
    candidate_name: str = Field(min_length=1)
    question_answers: list[QuestionAnswer] = Field(min_length=1)
    evaluation_results: list[EvaluationResult] = Field(min_length=5, max_length=5)
    overall_comment: str | None = None

    @model_validator(mode="after")
    def validate_numbering_and_evaluations(self) -> SaveInterviewRequest:
        question_numbers = [item.question_no for item in self.question_answers]
        expected_numbers = list(range(1, len(self.question_answers) + 1))
        if question_numbers != expected_numbers:
            raise ValueError("questionNoは1から始まる連番にしてください")

        item_ids = {item.evaluation_item_id.value for item in self.evaluation_results}
        if item_ids != set(EVALUATION_ITEM_IDS):
            raise ValueError("5つの評価項目を重複なく指定してください")

        return self


class SaveInterviewResponse(CamelModel):
    interview_id: str
    save_status: bool


@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(
    request: Request,
    error: RequestValidationError,
) -> JSONResponse:
    """Excel出力APIの入力エラーをAPI仕様どおり400で返す。"""

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


# 現行APIからは呼び出さないが、将来DB保存を再導入できるよう処理を保持する。
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


def save_interview_to_storage(req: SaveInterviewRequest) -> SaveInterviewResponse:
    """面接内容と評価内容をCSVへ保存する。現行APIからは未使用。"""

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
        raise StorageError("面接記録の保存に失敗しました") from error

    return SaveInterviewResponse(interview_id=interview_id, save_status=True)


@app.get("/health")
def health():
    return {"status": "ok"}


EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@app.post("/api/interviews")
def export_interview_excel(req: ExportInterviewRequest) -> StreamingResponse:
    """入力された面接記録を保存せず、Excelに変換して返す。"""

    try:
        interview = req.model_dump(mode="json")
        excel_file = create_interview_excel(interview)
    except (OSError, KeyError, TypeError, ValueError) as error:
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
