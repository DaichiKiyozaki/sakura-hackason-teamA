# 面接評価支援システム

新卒採用の一次面接を対象に、文字起こしの整理、回答要約、Excel出力を支援するMVPです。AIは面接内容の整理と要約に使用し、評価や合否は自動で決定しません。

## 現在の実装

- 面接日、候補者名、面接官名、文字起こしの入力画面
- 発言内容から面接官と応募者を推定
- 面接官の質問と応募者の回答への分割
- 応募者の回答の要約
- 分割・要約結果の画面表示
- 入力内容からExcelを直接生成するバックエンドAPI

入力内容はCSVやデータベースへ保存しません。Excelはリクエストごとにメモリ上で生成します。

フロントエンドにはExcel出力リクエストが実装されていますが、返されたファイルを `Blob` としてダウンロードする処理は未実装です。また、画面上の評価点と評価プロセスは現在のExcel出力APIには含まれません。

## 使用技術

| 分類 | 技術 |
| --- | --- |
| フロントエンド | Next.js 16 / React 19 / TypeScript / Tailwind CSS 4 |
| バックエンド | Python / FastAPI |
| ローカルLLM | Ollama |
| 使用モデル | Qwen2.5 3B Instruct（`qwen2.5:3b-instruct`） |
| Excel生成 | pandas / openpyxl |

## システム構成

```text
ブラウザ（localhost:3000）
        ↓ /api/*
Next.js
        ↓ リクエストを転送
FastAPI（localhost:8000）
        ├─ Ollama / qwen2.5:3b-instruct
        │      └─ 質問・回答の分割と回答要約
        └─ 入力内容からExcelをメモリ上で生成・返却
```

現行のExcel出力APIは入力内容をDBへ保存せず、Excel生成後もサーバー上へファイルを残しません。将来の再利用に備えて、CSVへのDB保存処理自体はバックエンド内に保持しています。

## セットアップ

Node.js、Python、Ollamaが必要です。以下はWindows PowerShellでの手順です。

### 1. Python環境

リポジトリのルートで実行します。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
```

### 2. Ollamaモデル

Ollamaを起動してからモデルを取得します。

```powershell
ollama pull qwen2.5:3b-instruct
```

### 3. バックエンド

```powershell
.\.venv\Scripts\Activate.ps1
cd backend
uvicorn main:app --reload
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ヘルスチェック: `http://localhost:8000/health`

### 4. フロントエンド

別のPowerShellで起動します。

```powershell
cd frontend
npm install
npm run dev
```

画面は `http://localhost:3000` で開きます。`/api/*` はNext.jsからFastAPIへ転送されるため、フロントエンドとバックエンドを同時に起動してください。

## API

| メソッド | パス | 内容 |
| --- | --- | --- |
| `POST` | `/api/analyze` | 文字起こしを質問・回答へ分割し、回答を要約 |
| `POST` | `/api/interviews` | 入力内容を保存せず、Excelファイルを返却 |
| `GET` | `/health` | バックエンドの稼働確認 |

`POST /api/interviews` の入力項目：

- `interviewDate`
- `candidateName`
- `interviewerName`
- `questionAnswers`
- `overallComment`（任意）

既存フロントとの互換性のため、`overallcomment` も受け付けます。詳しい入出力は [MVPインターフェース仕様書](docs/mvp-interface-spec.md) を参照してください。

## Excel出力

入力された面接記録を、1リクエストにつき1つのExcelファイルとして返します。

- 拡張子：`.xlsx`
- シート名：`面接記録`
- 出力内容：面接日、候補者名、面接官名、全体所感、質問、回答要約
- ファイル名例：`面接記録_応募者A_20260903.xlsx`

回答全文、評価点、評価理由はExcelへ出力しません。

## データの扱い

- CSVやデータベースへの保存は行いません。
- 入力内容はExcel生成中だけメモリ上で扱います。
- 生成したExcelは `BytesIO` からHTTPレスポンスとして返します。
- 過去記録の一覧・検索・比較は行いません。
- `backend/storage.py` と `data/*.csv` は旧CSV処理であり、現行APIからは参照しません。

## テストデータ

`test_data/` に手動確認用データを用意しています。

| ファイル | 用途 |
| --- | --- |
| `analyze_transcript.txt` | `面接官:`・`応募者:` 形式の文字起こし |
| `analyze_transcript_zoom.txt` | 時刻と参加者名だけを含むZoom形式の文字起こし |
| `export_interview_request.json` | Excel出力APIのリクエスト例 |

DB保存処理とサンプルCSVは将来の再利用に備えて残していますが、現行APIの動作には使用しません。

## ディレクトリ構成

```text
sakura-hackathon-teamA/
├── frontend/                 # Next.jsフロントエンド
├── backend/
│   ├── main.py               # 分析API、Excel出力API
│   ├── llm.py                # Ollamaによる分割・要約
│   ├── excel.py              # メモリ上でのExcel生成
│   ├── storage.py            # CSVによるDB処理（現行APIから未使用）
│   └── requirements.txt
├── data/                     # CSVデータ（現行APIから未使用）
├── test_data/                # 手動確認用データ
├── docs/
│   └── mvp-interface-spec.md
└── README.md
```

## 確認

バックエンドAPIはSwagger UI（`http://localhost:8000/docs`）から確認できます。フロントエンドの静的チェックは次のコマンドで実行します。

```powershell
cd frontend
npm run lint
```

現在、自動テストスイートはありません。
