# Phase 1 Baseline Report

## Source and dataset

| Signal | Value |
|---|---:|
| Source | Crossref REST API |
| Raw records | 24 |
| Clean records | 24 |
| Indexed documents | 24 |
| Benchmark questions | 10 |

## Baseline evaluation

| Metric | Value |
|---|---:|
| Retrieval Hit Rate | 1.0000 |
| Mean Token F1 | 1.0000 |
| LLM Judge Accuracy | 1.0000 |
| Mean LLM Judge Score | 5.00 / 5 |
| Ragas | Set RUN_RAGAS=1 to enable the slower Ragas pass. |

## Data quality gate

| Signal | Value |
|---|---:|
| Overall success | True |
| Successful expectations | 6 |
| Failed expectations | 0 |

## Freshness SLA

| Signal | Value |
|---|---:|
| Latest publication | 2026-09-15 |
| Oldest publication | 2026-04-01 |
| Stale rows | 0 / 24 |
| Stale ratio | 0.00% |
| Is fresh | True |

## Reproducibility

Run `python script/run_phase1.py` from the project root with the project environment activated.
