# Data Corruption and Idempotent Repair Report

## Baseline vs. corrupted vs. repaired

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| Retrieval Hit Rate | 1.0000 | 0.8000 | 1.0000 |
| Mean Token F1 | 1.0000 | 0.6979 | 1.0000 |
| Judge Accuracy | 1.0000 | 0.8000 | 1.0000 |
| Mean Judge Score | 5.00 | 3.60 | 5.00 |

## Quality and freshness signals

| Signal | Corrupted | Repaired |
|---|---:|---:|
| Quality gate success | False | True |
| Failed expectations | 2 | 0 |
| Freshness SLA | False | True |
| Stale rows | 10 / 22 | 0 / 24 |
| Stale ratio | 45.45% | 0.00% |

## Conclusion

The corrupted run demonstrates silent quality degradation while the application remains executable. The repaired run rebuilds clean data and a separate vector collection from preserved raw records, making the recovery idempotent and reproducible.
