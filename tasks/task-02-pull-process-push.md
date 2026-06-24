# Task 2 — Pull, Process, and Push

Pull a dataset from your own connector, augment it with derived columns, upload the result, and register it as a new derived asset with provenance metadata.

**Script:** `participant/scripts/task_local_02-pull-process-push.py`

## Prerequisites

- Task 1 completed (asset `my-measurement` registered)
- `.env` configured

## Run

```bash
cd participant/scripts
python task_local_02-pull-process-push.py
```

## What happens

### Step 1: Negotiate contract

The script queries your connector's catalogue for the `my-measurement` asset, finds the contract offer, and negotiates an agreement. This demonstrates the full DSP contract negotiation flow — even when provider and consumer are the same connector.

### Step 2: Generate presigned URL

A presigned PUT URL is generated on your local RustFS for the `received` bucket. This URL allows the EDC to upload the file without sharing S3 credentials.

### Step 3: Transfer dataset

The EDC initiates an `HttpData-PUSH` transfer. The provider side reads the file from RustFS using the `MinioAssetDataSource` and PUTs it to the presigned URL via the `PresignedHttpData` sink.

### Step 4: Augment the data

The transferred CSV is read and augmented with four new columns:

| New Column | Logic |
|------------|-------|
| `throughput_category` | `high` (>=150 Mbps), `medium` (>=100), `low` (<100) |
| `latency_category` | `good` (<=10ms), `acceptable` (<=20ms), `poor` (>20ms) |
| `efficiency_score` | throughput / latency ratio |
| `throughput_delta_mbps` | change from previous measurement |

A preview of the augmented data is printed to the console.

### Step 5: Upload augmented dataset

The augmented CSV is uploaded to the `my-datasets` bucket with a timestamped filename:

```
my-datasets/my-measurement-augmented-20260624T143022Z.csv
```

### Step 6: Register derived asset

The augmented file is registered as a new EDC asset with:

**DCAT-AP metadata** — description, issued date, license, keywords, version (set to the run timestamp)

**Provenance (PROV-O):**
- `prov.wasDerivedFrom` — links back to the source asset `my-measurement`
- `prov.wasGeneratedBy` — names the augmentation pipeline
- `prov.wasAttributedTo` — names the participant

**6G-DALI MAP:** — project name, compliance flags, measured variables (original + augmented)

Each run creates a uniquely-named asset (timestamped), so the script can be run multiple times to produce a version history.

## Verify

After running:

1. Open the **Catalog UI** at `http://<MY_HOST>:28180/api/catalog`
2. Both the original and augmented assets should appear in the **Assets** tab
3. Click the augmented asset to see its provenance metadata
4. Check the **Lineage** tab — the tree shows `my-measurement` as the root with the augmented asset(s) as derived children
5. Open the **RustFS UI** — the augmented CSV is in the `my-datasets` bucket
6. Click **Download** on the augmented asset to verify the additional columns

## Re-running

Each run creates a new timestamped asset and file. Previous versions remain in the catalogue and storage. The Lineage tab will show multiple derived assets branching from the same source.
