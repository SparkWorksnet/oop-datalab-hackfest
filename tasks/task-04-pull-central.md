# Task 3 — Pull a Dataset from the Central EDC

Discover datasets in the central hackfest EDC catalogue, negotiate access, and transfer a dataset to your local RustFS storage.

**Script:** `participant/scripts/tr02_s2_pull_central.py`

## Prerequisites

- Participant stack running
- `.env` configured with both `MY_HOST` and `CENTRAL_HOST`
- Central EDC running with assets registered

## Run

```bash
cd participant/scripts
python tr02_s2_pull_central.py
```

## What happens

### Step 1: Browse the central catalogue

The script uses your local connector's Management API to query the central EDC's catalogue via the DSP protocol. All available datasets are listed.

This demonstrates **cross-connector catalogue discovery** — your connector reaches out to the central connector's DSP endpoint and receives a `dcat:Catalog` response.

### Step 2: Negotiate contract

A contract is negotiated with the central connector for the `hackfest-sample-001` asset. The negotiation follows the Dataspace Protocol:

1. Your connector sends a `ContractRequest` to the central connector
2. The central connector evaluates the request against its access policy
3. If approved, both sides reach a `FINALIZED` agreement

### Step 3: Generate presigned URL

A presigned PUT URL is generated on your local RustFS pointing to:

```
received/from-central/hackfest-sample-001.csv
```

### Step 4: Transfer dataset

The transfer is initiated via your connector's Management API:

1. Your connector (consumer) sends a `TransferRequest` to the central connector (provider)
2. The central EDC reads the file from its RustFS using `MinioAssetDataSource`
3. The central EDC PUTs the file to your presigned URL via `PresignedHttpData` sink
4. The file lands in your local RustFS `received` bucket

This is a **cross-network transfer** — the central EDC pushes data directly to your storage without you sharing any S3 credentials.

## Verify

After running:

1. Open your **Catalog UI** at `http://<MY_HOST>:21000/api/catalog`
2. Check the **Negotiations** tab — you should see a `FINALIZED` negotiation with `hackfest-central` as the counter party
3. Check the **Transfers** tab — the transfer should show `COMPLETED`
4. Open the **RustFS UI** at `http://<MY_HOST>:21005` — the file is in `received/from-central/`
5. Open the central **Catalog UI** at `http://<CENTRAL_HOST>:18180/api/catalog` — the Negotiations tab shows the same negotiation from the provider side

## What to try next

- Change `ASSET_ID` in the script to pull a different dataset from the central catalogue
- Run Task 2 on the dataset you just pulled — augment it and register the derived version
- Browse another participant's catalogue by changing `CENTRAL_PROTOCOL` to their DSP address (`http://<THEIR_IP>:21002/protocol`)
