# Task 3 — Pull a Dataset

Move a dataset across the data space and into your local storage. The same
Dataspace Protocol flow — **browse a catalogue → negotiate a contract →
transfer the file** — works regardless of who the provider is: the central EDC,
another participant, or your own connector. This task covers all three, plus the
full **pull → process → push** DataOps lifecycle built on top of them.

**Scripts:** `participant/scripts/tr02_s2_pull_central.py`,
`tr02_s3_pull_peer.py`, `tr02_s4_pull_local.py`,
`tr02_s5_pull_process_push.py`

## Prerequisites

- Participant stack running, `.env` configured (`MY_HOST`, `PARTICIPANT_NAME`)
- For the central pull: `CENTRAL_HOST` set and the central EDC running with assets
- For the peer pull: a neighbour's stack running with an asset registered
- For the local / process-push flows: at least one asset registered on your own
  connector (run Task 2 — `tr02_s1_register.py` prints its id, a fresh UUID each run)

---

## From the central EDC

Discover datasets in the central hackfest catalogue, negotiate access, and
transfer one to your local RustFS.

```bash
cd participant/scripts
python tr02_s2_pull_central.py            # defaults to the central RabbitMQ sample
```

**What happens**

1. **Browse the central catalogue** — your connector's Management API queries the
   central EDC's catalogue over DSP and lists the available datasets. This is
   **cross-connector catalogue discovery**: your connector reaches the central
   DSP endpoint and receives a `dcat:Catalog` response.
2. **Negotiate a contract** — for the chosen asset (default: the RabbitMQ sample
   `cfdedca2-998e-46f9-b860-1bbf2aeb6a2f`). Your connector sends a
   `ContractRequest`, the central EDC evaluates it against its access policy, and
   both sides reach a `FINALIZED` agreement.
3. **Generate a presigned URL** on your local RustFS →
   `received/from-central/<asset-id>.csv`.
4. **Transfer** — the central EDC (provider) reads the file from its RustFS with
   `MinioAssetDataSource` and PUTs it to your presigned URL via the
   `PresignedHttpData` sink. A **cross-network transfer** with no S3 credentials
   shared.

**Verify**

1. Your **Catalog UI** (`http://<MY_HOST>:21000/api/catalog`) → **Negotiations**
   tab shows a `FINALIZED` negotiation with `hackfest-central` as counter party.
2. **Transfers** tab shows `COMPLETED`.
3. **RustFS UI** (`http://<MY_HOST>:21005`) → the file is in `received/from-central/`.
4. The central **Catalog UI** (`http://<CENTRAL_HOST>:20000/api/catalog`) shows the
   same negotiation from the provider side.

Pass a different asset id (`python tr02_s2_pull_central.py <asset-id>`) to pull
another dataset; run with no argument first to list what the central offers.

---

## From a peer

Pull directly from another participant's connector — the **federated topology**
where every participant is both provider and consumer.

Set the peer's details in `participant/.env` (ask them for both):

```
PEER_HOST=<the other participant's machine IP>
PEER_ASSET_ID=<the asset id they registered>
```

The asset id is printed by their `tr02_s1_register.py` run and shown in their
Catalog UI. Then:

```bash
cd participant/scripts
python tr02_s3_pull_peer.py
```

If either value is missing, the script tells you exactly what to add to `.env`.

**What happens**

1. **Browse the peer's catalogue** — same DSP discovery as above, but pointed at
   the peer's connector instead of the central one. The peer's connector id is
   auto-detected from the catalogue it returns (no extra config needed).
2. **Select and negotiate** — the script picks the dataset matching your
   `PEER_ASSET_ID` (listing what's available and stopping if it isn't there) and
   negotiates against the same open-access policy.
3. **Transfer** — the peer's EDC reads the dataset from their RustFS and PUTs it
   to a presigned URL on yours; the data lands in `received/from-peer/`.

**Verify**

1. Your **Catalog UI** → Negotiations tab shows the peer-to-peer negotiation.
2. Your **RustFS UI** → the file is in `received/from-peer/`.
3. The peer's **Catalog UI** shows the same negotiation from the provider side.

After several participants complete this, the venue has a live federated data space:

```
  Participant A                    Participant B
  ┌────────────┐                  ┌────────────┐
  │ my-data    │ ◄── negotiate ──►│ my-data    │
  │ augmented  │ ◄── transfer  ──►│ augmented  │
  │ from-peer/ │                  │ from-peer/ │
  └─────┬──────┘                  └──────┬─────┘
        │                                │
        └────── both discover ───────────┘
               Central EDC
          ┌──────────────────┐
          │ sample datasets  │
          └──────────────────┘
```

---

## From your own connector (local)

The local counterpart to the two above: a **self-transfer** where your connector
is both provider and consumer. Useful to exercise the full DSP flow — and the
basis for the DataOps pipeline in the next section.

```bash
cd participant/scripts
python tr02_s4_pull_local.py              # lists your catalogue's asset ids
python tr02_s4_pull_local.py <asset-id>   # pull one of them
```

Local assets get a fresh UUID per registration, so there's no fixed default —
run with no argument to list your own catalogue, then pass one of the ids.

**What happens**

1. **Browse your own catalogue** — your connector queries itself over DSP and
   lists your registered assets.
2. **Negotiate a contract with yourself** — provider and consumer are the same
   connector, so the provider id is your own `PARTICIPANT_NAME`. The negotiation
   still runs the complete DSP flow to a `FINALIZED` agreement.
3. **Transfer** — a presigned PUT URL on your RustFS receives the file at
   `received/from-local/<asset-id>.csv`.

**Verify**

1. Your **Catalog UI** → Negotiations/Transfers show a `FINALIZED` / `COMPLETED`
   self-transfer.
2. Your **RustFS UI** → the file is in `received/from-local/`.

---

## Pull, process & push (DataOps lifecycle)

Build on the local pull: augment the transferred data with derived columns,
upload the result, and register it as a new **derived asset with provenance** —
the full DataOps loop.

```bash
cd participant/scripts
python tr02_s5_pull_process_push.py <ASSET_ID_FROM_TASK_2>
# run with no argument to list your catalogue's asset ids
```

**What happens**

1. **Negotiate + transfer** — same self-transfer as the local pull above (queries
   your catalogue for the asset, negotiates, and PUSHes the file to a presigned
   URL on your `received` bucket via `HttpData-PUSH`).
2. **Augment the data** — the transferred CSV is read and extended with derived
   columns:

   | New Column | Logic |
   |------------|-------|
   | `cpu_utilisation_pct` | `cpu_usage / cpu_limit × 100` — CPU used vs the configured limit |
   | `ram_usage_mb` | `ram_usage / 1048576` — memory usage in MB |
   | `tail_latency_ratio` | `lat99 / lat50` — tail-latency inflation |
   | `lat50_delta_us` | change in median latency from the previous row |

3. **Upload** the augmented CSV to `my-datasets/` under a fresh random-UUID filename.
4. **Register a derived asset** with DCAT-AP metadata plus provenance (PROV-O):
   `prov.wasDerivedFrom` (the source asset id), `prov.wasGeneratedBy` (the
   pipeline), `prov.wasAttributedTo` (the participant), and 6G-DALI MAP fields
   (measured variables = original + augmented). Each run registers a new asset
   with a fresh random UUID, so repeated runs build a version history, and the
   derived asset nests under its source in the Catalog UI via the
   `prov:wasDerivedFrom` reference inside its `semantic_description`.

**Verify**

1. **Catalog UI** → both the original and augmented assets appear in **Assets**;
   the augmented ones nest as derived children under the source row.
2. Click an augmented asset to see its provenance metadata.
3. **RustFS UI** → the augmented CSV is in `my-datasets/`.
4. **Download** the augmented asset to confirm the extra columns.
5. The **Lineage** tab shows derived assets branching from the same source.

**Airflow equivalent:** [Task 4](task-04-airflow-dataops.md)'s
`hackfest_enrich_dataset` DAG does the same pull → augment → publish work,
triggered with `{"asset_id": "..."}` — including the same random-UUID derived
asset id and `semantic_description`-based provenance, so it behaves identically
to this script.

---

## What to try next

- Run the **process & push** flow on a dataset you pulled from the central EDC or
  a peer — augment it and register the derived version with provenance linking back.
- Register a dataset specifically for sharing, with custom MAP metadata describing
  your testbed, then have a neighbour pull it.
- Pull a dataset another participant *derived*, and inspect its provenance in the
  **Lineage** tab.
