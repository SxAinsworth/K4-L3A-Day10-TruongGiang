# Member Role Report - Day 10: Data Pipeline & Data Observability

## 1. Thong tin ca nhan

| Thong tin | Noi dung |
|---|---|
| Ho va ten | Ta Quang Dung |
| MSSV | 2A202602588 |
| Khoa/Lop | K4-L3A |
| Ten nhom | TruongGiang |
| Vai tro chinh | RAG & Agent Specialist; ho tro tich hop pipeline |
| Repository | https://github.com/SxAinsworth/K4-L3A-Day10-TruongGiang |
| Ngay hoan thanh | 2026-09-25 |

## 2. Vai tro va pham vi cong viec

### Phan viec so huu

| Module/deliverable | File/h ham phu trach | Input | Output | Trang thai |
|---|---|---|---|---|
| Vector index | `src/retrieval/index.py` | Clean dataframe, MiniLM embeddings | ChromaDB `papers-baseline`, embedding manifest | Hoan thanh |
| Retrieval smoke test | `src/retrieval/embeddings.py`, `src/retrieval/qa.py` | Query va vector index | SearchResult, QA context | Hoan thanh mot phan |
| Pipeline integration | `src/pipelines/phase1.py` | Raw records, clean data, evaluation set | Baseline metrics va report | Hoan thanh |
| Data foundation support | `src/ingestion/crossref.py`, `cleaning.py`, `observability/quality.py`, `evaluation/testset.py`, `ingestion/corruption.py` | Crossref snapshot, clean dataframe | Raw/clean artifacts, quality report, benchmark va corruption log | Hoan thanh mot phan |

### Viec ho tro ngoai pham vi chinh

| Hoat dong | Module duoc ho tro | Ket qua |
|---|---|---|
| Kiem tra va sua integration contract | Ingestion, cleaning, quality, evaluation | Cac module ket noi duoc voi Phase 1 |
| Xu ly loi moi truong Python | Toan pipeline | Xac dinh terminal dang dung system Python thay vi `venv` |

## 3. Ket qua theo vai tro

| Nhiem vu | File/artifact | Ket qua | Cach xac minh |
|---|---|---|---|
| Build vector index tu clean data | `src/retrieval/index.py`, `data/chroma/` | 24 documents trong collection `papers-baseline` | Smoke test semantic search tra ve 2 ket qua |
| Hoan thien API retrieval | `LocalEmbeddingIndex` | Them `build_from_clean()` va `semantic_search()` | `python script/run_phase1.py` exit code 0 |
| Chay baseline pipeline | `src/pipelines/phase1.py` | 24 clean rows, retrieval hit rate 1.0 | `data/results/baseline_metrics.json` |
| Hoan thien benchmark/quality/corruption support | `src/evaluation/testset.py`, `quality.py`, `corruption.py` | Test set 10 mau, quality pass, log 6 scenarios | Cac artifact trong `data/eval/`, `data/quality/`, `data/results/` |

Output chinh: [data/embeddings/papers_embeddings.json](../data/embeddings/papers_embeddings.json) ghi nhan collection `papers-baseline` voi 24 documents.

## 4. Giai thich phan ky thuat

### Van de can giai quyet

Pipeline can chuyen clean dataframe thanh vector index co the truy van semantic, sau do dung cung evaluation set de do chat luong retrieval va cau tra loi. Cac module starter co nhieu stub nen can noi lai contract giua ingestion, cleaning, quality, evaluation va retrieval.

### Cach trien khai

`LocalEmbeddingIndex.build()` tao document payload tu `text_for_embedding`, sinh embedding bang `sentence-transformers/all-MiniLM-L6-v2`, L2-normalize vector va nap vao ChromaDB voi cosine distance. `build_from_clean()` doc `papers_clean.json` va tao collection baseline. `semantic_search()` la alias tuong thich cho `search()` de smoke test tai lieu co the goi theo API trong tai lieu.

Phase 1 doc raw records, lam sach, ghi CSV/JSON, chay GX Quality Gate va Freshness, build Chroma index, tao/load test set, evaluate va ghi report Markdown.

### Input, output va contract

| Thanh phan | Mo ta |
|---|---|
| Input | `data/raw/crossref_records.json` va `data/clean/papers_clean.json` |
| Output | Chroma collection, embedding manifest, metrics, answers va report |
| Module phu thuoc | `core.config`, `ingestion.cleaning`, `retrieval.embeddings`, `evaluation.metrics` |
| Module su dung output | QA agent va baseline/corruption evaluation |
| Dieu kien loi | Sai Python interpreter, thieu clean artifact, thieu dependency hoac model chua duoc cache |

### Cach xac minh

```powershell
$env:PYTHONPATH="src"
& ".\venv\Scripts\python.exe" script/run_phase1.py
```

- Ket qua mong doi: Phase 1 exit code 0 va sinh du artifact.
- Ket qua thuc te: 24 clean rows, retrieval hit rate `1.000`.
- Artifact: `data/chroma/`, `data/embeddings/papers_embeddings.json`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md`.

## 5. Mot quyet dinh ky thuat quan trong

- **Boi canh:** Smoke test trong tai lieu goi `LocalEmbeddingIndex(settings, collection_name)`, `build_from_clean()` va `semantic_search()`, trong khi starter class yeu cau them tham so noi bo va chi co `search()`.
- **Phuong an:** Sua tat ca call site theo constructor noi bo; hoac bo sung API tuong thich trong class.
- **Phuong an da chon:** Bo sung default cho `documents/persist_path`, them `build_from_clean()` va alias `semantic_search()`.
- **Ly do:** Giu public API hien co cua `build()`/`load()`, giam thay doi downstream va lam smoke test tai lieu chay duoc.
- **Bang chung:** Smoke test query `machine learning` tra ve 2 tai lieu; manifest ghi 24 documents.

## 6. Mot loi hoac blocker da xu ly

- **Trieu chung:** `NotImplementedError` khi chay `python script/run_phase1.py`; ve sau terminal bao thieu file clean hoac thieu dependency.
- **Nguyen nhan goc:** Cac ham starter chua duoc implement va terminal `python` dang tro vao system interpreter thay vi `venv` cua project.
- **Cach xu ly:** Hoan thien Phase 1, tao clean artifacts, cai dependency can thiet va chay bang `& ".\venv\Scripts\python.exe"` voi `PYTHONPATH=src`.
- **Cach xac minh:** Phase 1 chay exit code 0; Quality Gate `True`; retrieval smoke test tra ve 2 ket qua.
- **Dieu hoc duoc:** Can xac minh `Get-Command python` va duong dan interpreter truoc khi ket luan loi thuoc ve code.

Phase 2 corruption flow (`src/pipelines/corruption_flow.py`) van chua duoc orchestration end-to-end. Hien tai moi co corruption function va [data/results/corruption_log.json](../data/results/corruption_log.json) voi du 6 scenario; chua co corrupted/repaired metrics de ket luan ve muc suy giam va phuc hoi.

## 7. Hieu biet ve luong end-to-end

1. Crossref response duoc parse thanh `PaperRecord`, sau do cleaning chuan hoa text, deduplicate theo DOI, tinh `age_days` va tao `text_for_embedding`. MiniLM embed text nay va ChromaDB luu vector cung metadata.
2. Evaluation set chua cau hoi, ground truth va DOI muc tieu. Retrieval hit duoc tinh neu mot DOI ground truth xuat hien trong top-k ket qua; Token F1 va judge do chat luong cau tra loi.
3. Quality checks kiem tra schema, volume, null, unique va do dai summary. Freshness rieng do ty le `age_days > 180`; chi can vuot 25% la `is_fresh=False`.
4. Cung test set giup baseline, corrupted va repaired chi khac nhau o chat luong du lieu/index, tu do so sanh co y nghia.
5. Repair thanh cong khi raw/clean artifact, quality/freshness va metrics sau repair phuc hoi; hien chua du bang chung repaired metrics trong workspace.

## 8. Phan tich ket qua

### Metrics chinh

| Metric/signal | Baseline | Corrupted | Repaired | Nhan xet |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0000 | Chua chay | Chua chay | Baseline hit 10/10 theo metrics artifact |
| `mean_token_f1` | 0.8538 | Chua chay | Chua chay | Ket qua thuc te tu `baseline_metrics.json` |
| `judge_accuracy` | 0.8000 | Chua chay | Chua chay | 8/10 cau duoc heuristic/LLM judge danh gia dung |
| `mean_judge_score` | 4.20 | Chua chay | Chua chay | Ragas duoc skip mac dinh |
| Quality checks | Pass | Chua chay | Chua chay | Baseline 24 rows, expectation suite pass |
| Freshness status | True | Chua chay | Chua chay | 1/24 stale, ratio 4.17% < 25% |

### Ket luan tu so lieu

1. Baseline clean data -> Quality Gate pass va freshness `True` -> retrieval hit rate `1.0`, Token F1 `0.8538`.
2. Corruption log da xac nhan du 6 phep bien doi -> can chay `corruption_flow.py` de do quality/metrics; chua duoc ket luan repaired vi chua co artifact sau repair.

Corruption hien co anh huong ro nhat ve mat quality la `blank_summary`, `stale_date` va `duplicate_rows` vi lan luot gay summary-length fail, freshness warning va unique-key fail. Anh huong dinh luong len agent chua duoc do trong workspace.

Ket qua can luu y: snapshot baseline co 1 stale row nhung van pass freshness vi stale ratio chi `0.0417`, khong phai 0%.

## 9. Dieu hoc duoc va huong cai thien

### Ba dieu quan trong nhat

1. Vector index can giu document ID va metadata nhat quan voi clean schema de evaluation doi chieu duoc.
2. Quality Gate va freshness la hai tin hieu khac nhau: du lieu co the hop le schema nhung van qua cu.
3. Cac loi silent trong summary, title, date va duplicate co the lam retrieval/QA suy giam ma khong tao exception runtime.

### Neu co them thoi gian

Hoan thien `src/pipelines/corruption_flow.py` de luu corrupted/repaired clean data, build hai collection rieng, chay cung test set va tao bang so sanh 3 trang thai. Sau do bo sung regression test cho 6 corruption scenarios va test retry/fallback cua Crossref.

## 10. Cam ket cua thanh vien

- [x] Noi dung bao cao phan anh phan viec va artifact da xac minh.
- [x] Co the giai thich luong end-to-end va phan retrieval/index.
- [x] Cac ket luan ve baseline co artifact doi chieu.
- [x] Khong ghi da chay thanh cong cho corrupted/repaired flow chua duoc kiem chung.
- [x] Bao cao khong chua `.env`, API key, token hoac secret.
- [x] Bao cao nay khong sao chep nguyen van bao cao nhom.

**Ho va ten:** Ta Quang Dung  
**Ngay xac nhan:** 2026-09-25
