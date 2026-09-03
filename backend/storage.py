"""DBとして使用するCSVのテーブル定義と読み込みを担当する。"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


# -----------------------------------------------------------------------------
# テーブル定義
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class Table:
    """CSV1つ分の置き場所と列構成。SQLのテーブル定義にあたる。

    保存先と列名は必ずセットで使うため、1つの値にまとめて持ち回る。
    """

    path: Path
    columns: tuple[str, ...]


INTERVIEWS = Table(
    DATA_DIR / "interviews.csv",
    (
        "interview_id",
        "interview_date",
        "candidate_name",
        "overall_comment",
    ),
)
QUESTION_ANSWERS = Table(
    DATA_DIR / "question_answers.csv",
    (
        "interview_id",
        "question_no",
        "question",
        "answer",
        "answer_summary",
    ),
)
EVALUATIONS = Table(
    DATA_DIR / "evaluations.csv",
    (
        "interview_id",
        "evaluation_item_id",
        "score",
        "reason",
    ),
)


class StorageError(Exception):
    """CSVの読み込みに失敗した。"""


class InterviewNotFoundError(StorageError):
    """指定された面接IDがDBに存在しない。"""


# -----------------------------------------------------------------------------
# CSVをSQLのように読み込む最小限の操作
# -----------------------------------------------------------------------------

def select(
    table: Table,
    columns: str | Iterable[str] | None = None,
    **conditions: Any,
) -> list[dict[str, str]]:
    """指定した列から、条件に一致する行だけを取り出す。

    SQLの SELECT 列 FROM テーブル WHERE 列 = 値 にあたる。
    例：select(QUESTION_ANSWERS, ("question",), interview_id="INT-0001")
    columnsを省略した場合は全列、条件を省略した場合は全行を返す。
    """

    if isinstance(columns, str):
        selected_columns = (columns,)
    elif columns is None:
        selected_columns = table.columns
    else:
        selected_columns = tuple(columns)
    unknown_columns = (set(selected_columns) | set(conditions)) - set(table.columns)
    if unknown_columns:
        names = ", ".join(sorted(unknown_columns))
        raise StorageError(f"存在しない列が指定されました: {names}")

    try:
        if not table.path.exists() or table.path.stat().st_size == 0:
            return []
        with table.path.open("r", encoding="utf-8", newline="") as file:
            rows = (
                row
                for row in csv.DictReader(file)
                if all(
                    row.get(column) == str(value)
                    for column, value in conditions.items()
                )
            )
            return [
                {column: row[column] for column in selected_columns}
                for row in rows
            ]
    except (OSError, csv.Error, KeyError, TypeError, ValueError) as error:
        raise StorageError("面接記録の読み込みに失敗しました") from error
