# Task 2 — Register a Dataset

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

A sample CSV — the Golang web-server distribution of the EURECOM cloud-native
microservice benchmark (`participant/scripts/seed-data/file-4.csv`) — is
uploaded to your local RustFS storage in the `my-datasets` bucket.

```
my-datasets/file-4.csv
```

| Column | Description |
|--------|-------------|
| time | Unix timestamp of the measurement |
| ram_limit / cpu_limit | Configured container memory / CPU limits |
| ram_usage / cpu_usage | Observed memory (bytes) / CPU usage |
| n / c | Request count / concurrency level |
| lat50 … lat100 | Response-latency percentiles in µs (p50, p66, p75, p80, p90, p95, p98, p99, p100) |

### Step 2: Register asset on EDC

The file is registered as an EDC asset with type `MinioAsset`. Rather than many
flat `dct.*`/`dali.*` properties, its metadata is a single structured
`semantic_description` property — a DCAT-AP / GAIA-X / 6G-DALI MAP JSON-LD
document (the same shape the Track 1 Submission Portal produces), built by
`helpers.build_semantic_description`. It carries:

**DCAT-AP core:** title, description, `dct:issued`, `dct:publisher` (EURECOM) and
`dct:creator` (Nassima Toumi) as `foaf` nodes, `dct:license` (CC BY 4.0),
`dct:accessRights` (public), `dcat:keyword`, `adms:version`, and `dct:source` /
`adms:identifier` referencing the source DOI (`10.5281/zenodo.6907619`).

**6G-DALI MAP:** `dali:snsProjectName`, `dali:gdprCompliant` / `dali:fairCompliant`,
and testbed context (e.g. `dali:environment`) describing the benchmark setup.

**Distribution:** a `dcat:distribution` node with the file's format, byte size,
SHA-256 checksum, and `schema:variableMeasured` (the CSV column names).

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
