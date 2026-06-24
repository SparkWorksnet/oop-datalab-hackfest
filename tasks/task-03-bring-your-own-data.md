# Task 3 — Bring Your Own Data

Submit your own dataset to the data space using the Dataset Submission Portal built into the EDC Catalog UI.

**Tool:** `http://<MY_HOST>:28180/api/catalog/submit` (click **"+ Submit Dataset"** from the Catalog UI header)

## Prerequisites

- Participant stack running (`docker compose up -d`)
- A CSV or TSV file to submit

## Run

1. Open your Catalog UI at `http://<MY_HOST>:28180/api/catalog`
2. Click the **"+ Submit Dataset"** button in the header
3. Follow the 4-step wizard

## What happens

### Step 1: Metadata

Fill in the dataset description:

- **Basic Information** (mandatory) — title, description, publisher, contact, licence, keywords
- **Dataset Details** (recommended) — temporal coverage, network technology, frequency band, collection method, column names, provenance
- **Additional Information** (optional) — existing DOI, access rights, related publications, contributors

All metadata fields are stored as EDC asset properties following the 6G-DALI MAP naming convention (e.g., `dali.networkDomain`, `dct.description`).

### Step 2: Data

Choose how to provide your data:

- **Upload files** — browse or drag-and-drop a CSV/TSV file. The portal auto-detects columns and shows a preview with the first 5 rows. The file is uploaded to RustFS (`my-datasets` bucket) through the EDC's built-in upload proxy.
- **Provide a link** — enter a URL where the dataset can be retrieved. The EDC stores a reference to this URL as an `HttpData` asset.

When a CSV/TSV file is selected:
- Column names are extracted from the header row
- Column types are guessed from the first data row (str, float, int, date)
- The "Dataset Columns" field on Step 1 is auto-filled
- Quality check fields on Step 3 are auto-populated

### Step 3: Quality Checks

Three sections of data quality rules (based on Great Expectations):

**Table-Level Checks:**
- `ExpectTableRowCountToBeBetween` — min/max row count (default min: 1)
- `ExpectTableColumnsToMatchOrderedList` — columns appear in the detected order

**Per-Column Checks** (auto-generated for every detected column):
- `ExpectColumnToExist` — column must be present
- `ExpectColumnValuesToNotBeNull` — no null values
- `ExpectColumnValuesToBeOfType` — type dropdown (auto-detected as str/float/int/date)

All per-column checks are enabled by default. Toggle individual checks per column using the checkboxes. Add new columns manually and click Apply.

**Additional Column Checks** (user-added, duplicable):
- Select a check type, pick a column, configure parameters, click **"+ Add"**
- Available: `ExpectColumnValuesToBeBetween`, `ExpectColumnValuesToBeDateutilParseable`, `ExpectColumnValuesToBeInSet`, `ExpectColumnValuesToNotBeInSet`, `ExpectColumnValuesToBeNull`
- Add multiple instances of the same check for different columns

### Step 4: Review and Submit

Review all metadata, data, and quality check selections. On submit, the portal:

1. Uploads the file to RustFS via the EDC upload proxy (no CORS issues)
2. Registers the dataset as an EDC asset with all MAP metadata
3. Creates an open-access policy and contract definition (if not already present)
4. Shows a confirmation with the asset ID and a link to the Catalog UI

You can navigate between steps freely by clicking the progress bar.

## Verify

After submission:

1. Open the **Catalog UI** at `http://<MY_HOST>:28180/api/catalog`
2. Your dataset should appear in the Assets tab
3. Click the asset row to expand its metadata — all fields from the submission form are visible, organised by DCAT-AP, 6G-DALI MAP, and Provenance sections
4. Check the **RustFS UI** at `http://<MY_HOST>:9001` — the file is in `my-datasets`
5. Ask another participant to discover your dataset from their connector (Task 5)

## What to try next

- Submit multiple datasets and see them all in the Catalog UI
- Run Task 4 (pull from central) or Task 5 (peer exchange) to pull someone else's dataset
- Use the augmentation pipeline from Task 2 on your own data — register the result as a derived asset with provenance linking back to your submission
- Check the **Lineage** tab after running Task 2 on your data — the tree will show your original dataset as a source node
