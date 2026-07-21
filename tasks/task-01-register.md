# Task 1 — Register a Dataset

Register a dataset on your own EDC connector with 6G-DALI Metadata Application Profile (MAP) metadata.

**Script:** `participant/scripts/tr02_s1_register.py`

## Prerequisites

- Participant stack running (`docker compose up -d`)
- `.env` configured with your IP

## Run

```bash
cd participant/scripts
python tr02_s1_register.py
```

## What happens

### Step 1: Upload sample data to RustFS

A sample CSV file with 5G NR measurements is uploaded to your local RustFS storage in the `my-datasets` bucket.

```
my-datasets/my-measurement.csv
```

| Column | Description |
|--------|-------------|
| timestamp | ISO 8601 timestamp |
| throughput_mbps | Downlink throughput in Mbps |
| latency_ms | Round-trip latency in ms |

### Step 2: Register asset on EDC

The file is registered as an EDC asset with type `MinioAsset`. The asset includes rich metadata following the 6G-DALI MAP:

**DCAT-AP core fields:**
- `dct.description` — human-readable description
- `dct.issued` — publication date
- `dct.publisher` — publishing organisation
- `dct.license` — CC-BY-4.0
- `dct.accessRights` — public access
- `dcat.keyword` — searchable tags
- `adms.version` — version label

**6G-DALI MAP fields:**
- `dali.snsProjectName` — SNS-JU project name
- `dali.gdprCompliant` / `dali.fairCompliant` — compliance flags
- `dali.environment` — testbed environment (indoors/urban/rural)
- `dali.networkDomain` — RAN / Core / Transport
- `dali.ran3gppRelease` — 3GPP release version
- `dali.ranNewRadioType` — NR-SA / NR-NSA / LTE
- `dali.ranFrequencyBand` — frequency band (n78, etc.)
- `dali.ranBandwidthMHz` — channel bandwidth
- `dali.measurementFamily` — 3GPP TS 28.552 family (DRB, RRC, etc.)
- `dali.measurementTool` — tool used for measurement
- `schema.variableMeasured` — measured variables

### Step 3: Create policy and contract definition

An open-access policy and contract definition are created so the asset is discoverable and negotiable by other connectors.

### Step 4: Query catalogue

The script queries your own connector's catalogue via the DSP protocol to verify the asset appears with its contract offer.

## Verify

After running:

1. Open the **Catalog UI** at `http://<MY_HOST>:21000/api/catalog`
2. The asset should appear in the **Assets** table
3. Click the asset row to expand its 6G-DALI MAP metadata
4. The asset appears as a `source` node in the unified assets/lineage table
5. Open the **RustFS UI** at `http://<MY_HOST>:21005` — the file is in the `my-datasets` bucket

## Re-running

The asset id is a fresh UUID generated each time the script runs (printed at
the end — copy it for later steps/tasks), so re-running always registers a
new, distinct asset rather than colliding with a previous run's. The policy
and contract definition, by contrast, use fixed ids and are handled
gracefully — if they already exist, the script skips creation and continues.
