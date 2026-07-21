# Task 7 — Airflow DataOps DAGs

Run the same pull → process → publish lifecycle as Task 2, but as repeatable, triggerable Airflow DAGs instead of one-off scripts — plus a new DAG that runs automated Great Expectations quality checks against a dataset.

**Tool:** `http://<MY_HOST>:21006` (Airflow UI, login `airflow` / `airflow`)

## Prerequisites

- Participant stack running (`docker compose up -d`)
- Task 1 completed (an asset registered — `tr02_s1_register.py` prints its id)
- First startup after a fresh `docker compose up` takes a little longer than usual: the `airflow` service installs `pandas` and `great_expectations` via `_PIP_ADDITIONAL_REQUIREMENTS` before it comes up healthy

## DAGs

| DAG | File | Trigger `conf` |
|-----|------|-----------------|
| `hackfest_pull_to_dataops` | `airflow/dags/hackfest_pull_to_dataops.py` | `{"asset_id": "<uuid>"}` |
| `hackfest_process_dataset` | `airflow/dags/hackfest_process_dataset.py` | `{"asset_id": "<uuid>"}` |
| `hackfest_validate_dataset` | `airflow/dags/hackfest_validate_dataset.py` | `{"asset_id": "<uuid>", "expectations": [...]}` (expectations optional) |

All three pull data the same way: a **self-transfer** against your own connector (`dali.datalake.download_dataset_edc`, in `airflow/plugins/dali/`) — the same connector plays both provider and consumer, so no second participant is needed to try these out.

### `hackfest_pull_to_dataops`

The simplest of the three: pulls the dataset, loads it into a pandas DataFrame, and prints it to the task logs. No data operation, no output artifact — a smoke test for the pull step and a template for writing your own DAG.

### `hackfest_process_dataset`

The Airflow equivalent of Task 2's `task_local_02-pull-process-push.py`, with one deliberate difference: **the derived asset id is fixed, not timestamped.**

1. Pulls the dataset (`download_dataset_edc`)
2. Derives the same four columns as the script (`throughput_category`, `latency_category`, `efficiency_score`, `throughput_delta_mbps`) — resolves the throughput column by name (`throughput_mbps` or `throughput_dl_mbps`, matching either the Track 2 sample data or the central connector's seed data) and raises a clear error if neither is present
3. Uploads the augmented CSV to `my-datasets` as `<asset_id>-augmented.csv` (no run timestamp)
4. Registers it as a new asset with id `<asset_id>-augmented` on your own connector, with `prov.wasDerivedFrom` pointing back at the source

Because the id and S3 key are fixed, re-running the DAG **overwrites the same derived asset** rather than creating a new one each time — one derived dataset per source, with lineage carried entirely by the `prov.*` metadata. (Task 2's script instead timestamps every run, so re-running it produces a new derived asset each time — pick whichever behaviour fits what you're building.)

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

After running all three DAGs against the same asset:

1. Open the **Catalog UI** — the original asset, its `<asset_id>-augmented` derived asset, and (once validated) a Validation report should all be visible
2. Click **Validation** on the original asset to see the Great Expectations results
3. Click **Preview** on either asset to check the actual column data
4. Re-run `hackfest_process_dataset` a second time and confirm the derived asset's id/key stay the same (check RustFS UI — the object is overwritten, not duplicated)

## What to try next

- Pass an explicit `expectations` list to `hackfest_validate_dataset` instead of relying on auto-generation, and compare the report
- Chain the DAGs: trigger `hackfest_process_dataset`, then run `hackfest_validate_dataset` against the resulting `<asset_id>-augmented` id to validate the derived data too
- Write your own DAG in `airflow/dags/` using `dali.datalake.download_dataset_edc` and `dali.datalake.register_derived_asset` as building blocks (see Task 6)
