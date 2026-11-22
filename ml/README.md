# ML Detection Engine

## Models
- Random Forest (supervised)
- SVM / LinearSVC + calibration (supervised)
- Isolation Forest (unsupervised anomaly → attack mapping)

## Features
Shared schema in `backend/app/ml/features.py` used for both training and inference.

## Datasets
- **Synthetic Flow Baseline** (`datasets/synthetic_flow_baseline.csv`) — local labelled flows for offline demos. Clearly not CICIDS2017.
- **CSV import** via API/UI — place compatible labelled CSVs under this folder.
- **CICIDS2017** — not auto-downloaded (disk policy). Import manually when available.

## Artifacts
Saved under `saved_models/*.joblib` with companion `*_metrics.json`.

## Note on metrics
Synthetic baseline is intentionally separable, so RF/SVM may show very high test scores. Those values are measured on the hold-out split, not fabricated. Isolation Forest typically scores lower. Real CICIDS imports produce more realistic operational metrics.
