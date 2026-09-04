"""DBとして使用するCSVのテーブル定義と読み書きを担当する。"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


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

# フロントエンドとAPIで共通して使用する評価観点ID。
EVALUATION_ITEM_IDS = (
    "communication",
    "problem_solving",
    "logical_thinking",
    "initiative",
    "collaboration",
)


class StorageError(Exception):
    """CSVの読み書きに失敗した。"""


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


def insert(
    table: Table,
    rows: Mapping[str, Any] | Iterable[Mapping[str, Any]],
) -> None:
    """指定したテーブルへ行を追加する。SQLのINSERTにあたる。"""

    if isinstance(rows, Mapping):
        rows_to_insert = [rows]
    else:
        rows_to_insert = list(rows)

    if not rows_to_insert:
        return

    expected_columns = set(table.columns)
    for row in rows_to_insert:
        actual_columns = set(row)
        if actual_columns != expected_columns:
            missing = expected_columns - actual_columns
            extra = actual_columns - expected_columns
            details = []
            if missing:
                details.append(f"不足: {', '.join(sorted(missing))}")
            if extra:
                details.append(f"余分: {', '.join(sorted(extra))}")
            raise StorageError(f"CSVの列が一致しません（{' / '.join(details)}）")

    try:
        _ensure_table(table)
        with table.path.open("a", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(
                file,
                fieldnames=table.columns,
                quoting=csv.QUOTE_MINIMAL,
            )
            writer.writerows(rows_to_insert)
    except (OSError, csv.Error, TypeError, ValueError) as error:
        raise StorageError("面接記録の保存に失敗しました") from error


def select_max(
    table: Table,
    column: str,
    *,
    key: Callable[[str], Any] | None = None,
) -> str | None:
    """指定した列の最大値を返す。行がない場合はNoneを返す。"""

    values = [row[column] for row in select(table, column)]
    if not values:
        return None

    try:
        return max(values, key=key)
    except (TypeError, ValueError) as error:
        raise StorageError("最大値の取得に失敗しました") from error


def _ensure_table(table: Table) -> None:
    """CSVが存在しない場合にヘッダー付きの空テーブルを作成する。"""

    table.path.parent.mkdir(parents=True, exist_ok=True)
    if table.path.exists() and table.path.stat().st_size > 0:
        return
    with table.path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=table.columns,
            quoting=csv.QUOTE_MINIMAL,
        )
        writer.writeheader()
