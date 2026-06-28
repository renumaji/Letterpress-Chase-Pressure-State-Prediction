# Letterpress Chase Pressure State Prediction Dataset

## Overview

This synthetic from-scratch dataset contains deterministic letterpress chase lockup traces for an eight-zone printing forme. Each row represents one protocol trace. The goal is to reconstruct the final measured state of a requested target zone by executing the trace from left to right and correcting systematic measurement calibration effects visible in the public training rows.

The raw data was generated locally using the included `generate_raw.py` script with a fixed random seed. Public columns contain only the nominal trace and public context; target values include systematic effects tied to paper stock, humidity, forme orientation, repeated operation patterns, and target-zone position.

## File Structure

| File | Description |
|---|---|
| `data.csv` | Raw generated source table. It contains public input columns, target columns, operation-count helper columns, and private grouping columns used by the prepare script. |
| `generate_raw.py` | Deterministic generator script that creates the raw source table. |

The prepare script creates these public/private files:

| Prepared File | Description |
|---|---|
| `public/train.csv` | Labeled training traces with public inputs and target columns. |
| `public/test.csv` | Unlabeled test traces with public inputs only. |
| `public/sample_submission.csv` | Example submission with the required columns. |
| `private/answers.csv` | Hidden target values and hidden group labels for test rows. |

## Raw Columns

| Column | Type | Description |
|---|---|---|
| `case_id` | string | Raw trace identifier; remapped by `prepare.py` before public release. |
| `target_zone` | string | Requested chase zone (`Z0` to `Z7`). |
| `lockup_trace` | string | Semicolon-separated operation program. |
| `operation_count` | int | Number of operations in the trace. |
| `paper_stock` | categorical | One of `rag`, `cotton`, `newsprint`, or `vellum`. |
| `humidity_band` | categorical | One of `dry`, `steady`, or `damp`. |
| `forme_orientation` | categorical | One of `north`, `east`, `south`, or `west`. |
| `impression_force` | float | Target measured force for the requested zone. |
| `ink_spread_pct` | float | Target ink-spread percentage for the requested zone. |
| `paper_lift_pct` | float | Target paper-lift percentage for the requested zone. |
| `slip_risk_pct` | float | Target slip-risk percentage for the requested zone. |
| `count_shift`, `count_split`, `count_tighten`, `count_relief`, `count_swell`, `count_smear`, `count_clamp`, `count_rotate` | int | Raw helper counts not included in public prepared data. |
| `operation_bin_private` | categorical | Hidden operation-length group for robust grading. |
| `force_bin_private` | categorical | Hidden target-force group for robust grading. |
| `structure_private` | categorical | Hidden dominant-structure group for robust grading. |

## Data Characteristics

- The trace grammar includes `PLACE`, `SHIFT`, `SPLIT`, `TIGHTEN`, `RELIEF`, `SWELL`, `SMEAR`, `CLAMP`, and `ROTATE`.
- Programs contain roughly 31 to 53 operations and must be executed in order.
- The same operation multiset can produce different targets depending on operation order and target zone.
- A literal interpreter is not sufficient because target measurements include calibration effects from paper stock, humidity, orientation, and operation patterns.
- Public IDs are hashed and rows are shuffled during preparation to avoid exposing raw generation order.
