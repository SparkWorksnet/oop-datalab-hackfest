# Task 3 — Bring Your Own Data

Submit your own dataset to the data space using the Dataset Submission Portal.

**Tool:** The Dataset Submission Portal, built into the EDC Catalog UI.

## Prerequisites

- Participant stack running (`docker compose up -d`)
- A data file to submit (CSV, TSV, Parquet, or a URL to one)

## Run

Open the submission portal from the Catalog UI:

1. Go to your Catalog UI at `http://<MY_HOST>:28180/api/catalog`
2. Click the **"+ Submit Dataset"** button in the header
3. Or navigate directly to `http://<MY_HOST>:28180/api/catalog/submit`

## What happens

The submission portal guides you through a 4-step wizard:

### Step 1: Metadata

Fill in the dataset description following the 6G-DALI MAP:

- **Basic Information** (mandatory) — title, description, publisher, contact, licence, keywords
- **Dataset Details** (recommended) — temporal coverage, network technology, frequency band, collection method, column names, provenance
- **Additional Information** (optional) — existing DOI, access rights, related publications, contributors

### Step 2: Data

Choose how to provide your data:

- **Upload files** — drag and drop or browse for CSV/TSV/Parquet files. The file is uploaded directly to your local RustFS (`my-datasets` bucket).
- **Provide a link** — enter a URL where the dataset can be retrieved. The EDC will store a reference to this URL as an `HttpData` asset.

### Step 3: Quality Checks

Select which data quality rules to enforce. These are based on Great Expectations:

- `ExpectColumnValuesToNotBeNull` (compulsory)
- `ExpectColumnToExist`
- `ExpectTableRowCountToBeBetween`
- `ExpectColumnValuesToBeOfType`
- `ExpectColumnValuesToBeBetween`
- `ExpectColumnValuesToBeDateutilParseable`

Quality check parameters from this step can be used later to configure a DataOps validation pipeline.

### Step 4: Review and Submit

Review all metadata, data, and quality check selections. On submit, the portal:

1. Uploads the file to RustFS (if file upload was selected)
2. Registers the dataset as an EDC asset with all MAP metadata
3. Creates an open-access policy and contract definition (if not already present)
4. Shows a confirmation with the asset ID

## Verify

After submission:

1. Open the **Catalog UI** at `http://<MY_HOST>:28180/api/catalog`
2. Your dataset should appear in the Assets tab
3. Click to expand its metadata — all fields from the submission form are stored as EDC properties
4. Check the **RustFS UI** at `http://<MY_HOST>:9001` — the file is in `my-datasets`
5. Ask another participant to discover your dataset from their connector

## What to try next

- Submit multiple datasets and see them all in the Catalog UI
- Run Task 4 (pull from central) or Task 5 (peer exchange) to pull someone else's dataset
- Use the augmentation pipeline from Task 2 on your own data — register the result as a derived asset
