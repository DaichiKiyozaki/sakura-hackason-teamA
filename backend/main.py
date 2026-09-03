"""面接評価支援システムのバックエンドAPI。"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from excel import create_excel_filename, create_interview_excel
from storage import (
    INTERVIEWS,
    QUESTION_ANSWERS,
    InterviewNotFoundError,
    StorageError,
    select,
)


# FastAPIアプリ本体。起動後は /docs からAPIを手動確認できる。
app = FastAPI(title="面接評価支援システム API", version="0.1.0")

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
