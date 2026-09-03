"""
main.py（抜粋：/api/analyze エンドポイント）

storage.py, excel.py の担当者が実装するエンドポイントは
このファイルに合流させる想定（仕様書 9章のディレクトリ構成）。
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from llm import analyze_transcript

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
