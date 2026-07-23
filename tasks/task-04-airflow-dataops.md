# Task 4 — Airflow DataOps DAGs

Run the same pull → process → publish lifecycle as Task 3, but as repeatable, triggerable Airflow DAGs instead of one-off scripts — column enrichment, row augmentation by interpolation, and a DAG that runs automated Great Expectations quality checks against a dataset.

**Tool:** `http://<MY_HOST>:21006` (Airflow UI, login `airflow` / `airflow`)

## Prerequisites

- Participant stack running (`docker compose up -d`)
- Task 2 completed (an asset registered — `tr02_s1_register.py` prints its id)
- First startup after a fresh `docker compose up` takes a little longer than usual: the `airflow` service installs `pandas` and `great_expectations` via `_PIP_ADDITIONAL_REQUIREMENTS` before it comes up healthy

## DAGs

| DAG | File | Trigger `conf` |
|-----|------|-----------------|
| `hackfest_pull_to_dataops` | `airflow/dags/hackfest_pull_to_dataops.py` | `{"asset_id": "<uuid>"}` |
| `hackfest_enrich_dataset` | `airflow/dags/hackfest_enrich_dataset.py` | `{"asset_id": "<uuid>"}` |
| `hackfest_augment_dataset` | `airflow/dags/hackfest_augment_dataset.py` | `{"asset_id": "<uuid>"}` |
| `hackfest_validate_dataset` | `airflow/dags/hackfest_validate_dataset.py` | `{"asset_id": "<uuid>", "expectations": [...]}` (expectations optional) |

All four pull data the same way: a **self-transfer** against your own connector (`dali.datalake.download_dataset_edc`, in `airflow/plugins/dali/`) — the same connector plays both provider and consumer, so no second participant is needed to try these out.

### `hackfest_pull_to_dataops`

The simplest of the three: pulls the dataset, loads it into a pandas DataFrame, and prints it to the task logs. No data operation, no output artifact — a smoke test for the pull step and a template for writing your own DAG.

### `hackfest_enrich_dataset`

The Airflow equivalent of Task 3's `tr02_s5_pull_process_push.py` — the same pull → augment → publish flow, as a repeatable DAG.

1. Pulls the dataset (`download_dataset_edc`)
2. Derives the same four columns as the script (`cpu_utilisation_pct`, `ram_usage_mb`, `tail_latency_ratio`, `lat50_delta_us`) from the benchmark's `cpu_usage`/`cpu_limit`/`ram_usage`/`lat50`/`lat99` columns, and raises a clear error if the dataset lacks them
3. Uploads the augmented CSV to `my-datasets` under a fresh random-UUID filename
4. Registers it as a new derived asset (a fresh random UUID) on your own connector, with `prov:wasDerivedFrom` recorded **inside the asset's `semantic_description`** JSON-LD (the same shape the scripts and the Submission Portal use), which the Catalog UI reads to nest it under its source

Like the script, each run registers a new randomly-identified derived asset, so re-running the DAG builds a version history of derived datasets branching from the same source (visible in the Lineage tab).

### `hackfest_augment_dataset`

The row-augmentation counterpart to `hackfest_enrich_dataset`: instead of adding **columns** (feature engineering), it adds **rows** (up-sampling by interpolation).

1. Pulls the dataset (`download_dataset_edc`)
2. Inserts one **interpolated row between each pair of consecutive rows** — the linear midpoint of every numeric column, with non-numeric columns (e.g. a `500M` limit label) carrying the earlier row's value. An *n*-row dataset becomes *2n − 1* rows. Works on any numeric CSV, so no fixed schema is required
3. Uploads the up-sampled CSV to `my-datasets` under a fresh random-UUID filename
4. Registers it as a new derived asset (fresh random UUID) with `prov:wasDerivedFrom` inside its `semantic_description`, so the Catalog UI nests it under the source

This is *true* data augmentation (more samples), as opposed to `hackfest_enrich_dataset`'s feature derivation (more columns) — the same pull → transform → publish-with-provenance loop, different transform.

### `hackfest_validate_dataset`

Runs a configurable Great Expectations suite against a pulled dataset:

1. Pulls the dataset and checks its content actually matches its own format (a proper CSV loadable into a DataFrame)
2. Runs the GX suite from the `expectations` param — if omitted, expectations are **auto-generated from `schema.variableMeasured`**, read directly off the asset's own registered properties (there's no piveau catalogue in this hackfest to fetch it from, unlike the production DataOps DAG this one is cloned from)
3. Writes the JSON report **next to the original file** — same bucket and credentials as the source asset's own `dataAddress`, named `<original-basename>_<timestamp>.gx.json` — not into a separate staging bucket
4. Logs a pass/fail summary (no piveau `dqv:QualityMeasurement` publish step — there's no catalogue record to attach it to)

## Viewing validation results

Two ways to see a validation report without digging through RustFS manually:

**From the terminal:**

```bash
cd participant/scripts
python tr03_view_validation_report.py <ASSET_ID>          # latest report
python tr03_view_validation_report.py <ASSET_ID> --all    # every report on file
```

Renders a pass/fail summary with a progress bar and a per-expectation table, reading the report(s) straight out of the source asset's own bucket.

**From the Catalog UI:** open `http://<MY_HOST>:21000/api/catalog` and each asset row now has three buttons instead of one:

| Button | What it does |
|--------|--------------|
| **Validation** | Opens a modal showing the latest `hackfest_validate_dataset` report for this asset — pass/fail badge, progress bar, per-expectation results |
| **Preview** | Opens a modal showing the first part of the asset's own file — a table for CSV, pretty-printed for JSON/JSONL, raw text otherwise |
| **Download** | Unchanged — downloads the full file |

Both new buttons fetch on click only (no background polling), so browsing a large asset list stays fast.

## Verify

After running the DAGs against the same asset:

1. Open the **Catalog UI** — the original asset, its derived asset (a fresh UUID), and (once validated) a Validation report should all be visible
2. Click **Validation** on the original asset to see the Great Expectations results
3. Click **Preview** on either asset to check the actual column data
4. Re-run `hackfest_enrich_dataset` a second time and confirm a **new** derived asset appears (a fresh UUID), nested under the same source (check RustFS UI — a new object, not an overwrite)

## What to try next

- Pass an explicit `expectations` list to `hackfest_validate_dataset` instead of relying on auto-generation, and compare the report
- Chain the DAGs: trigger `hackfest_enrich_dataset`, then run `hackfest_validate_dataset` against the resulting derived asset's id (shown in the DAG logs / Catalog UI) to validate the derived data too
- Write your own DAG in `airflow/dags/` using `dali.datalake.download_dataset_edc` and `dali.datalake.register_derived_asset` as building blocks (see Task 5)
