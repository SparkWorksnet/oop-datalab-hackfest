#!/usr/bin/env python3
"""
Task 2 — Pull a dataset from your own connector, process it, and push the results back.

Usage:
    python tr02_s5_pull_process_push.py [ASSET_ID]

    ASSET_ID  The asset to pull from your own connector's catalogue — the UUID
              that tr02_s1_register.py printed when you registered it (there is
              no fixed default, since that id is freshly generated each run).
              Run with no argument to list your catalogue's ids, then pass one:
                  python tr02_s5_pull_process_push.py <uuid-from-step-1>

Configure MY_HOST and other settings in .env before running.
Run tr02_s1_register.py first to register the asset.

Steps:
  1. Negotiate a contract for the asset on your own connector
  2. Generate a presigned URL for the destination bucket
  3. Transfer the file via the EDC
  4. Read and process the transferred data
  5. Upload the processed results to RustFS
  6. Register the results as a new derived asset on the EDC
"""

import argparse
import csv
import io
import json
import sys
import uuid
from datetime import datetime, timezone

import boto3
from botocore.client import Config

from config import (
    MY_MGMT, MY_PROTOCOL, PARTICIPANT_NAME,
    S3_ENDPOINT, S3_INTERNAL, S3_ACCESS, S3_SECRET,
)
from helpers import EdcClient, build_semantic_description

parser = argparse.ArgumentParser(
    description="Pull a dataset from your own connector, process it, and push the results back."
)
parser.add_argument(
    "asset_id", nargs="?", default=None,
    help="Asset to pull from your own catalogue (the UUID tr02_s1_register.py "
         "printed); run with no argument to list your catalogue's ids",
)
args = parser.parse_args()

DEST_BUCKET = "received"
ASSET_ID = args.asset_id
RUN_TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

edc = EdcClient(MY_MGMT)

# No fixed default: tr02_s1_register.py assigns a fresh UUID per run, so the
# asset to process must be given explicitly. With no argument, list your own
# catalogue and exit so you can copy the id it printed.
if ASSET_ID is None:
    print("=== Your catalogue ===")
    catalog = edc.request_catalogue(MY_PROTOCOL)
    datasets = catalog.get("dcat:dataset", [])
    if isinstance(datasets, dict):
        datasets = [datasets]
    if datasets:
        print(f"  Found {len(datasets)} asset(s):")
        for ds in datasets:
            print(f"    - {ds.get('@id', '?')}")
    else:
        print("  Your catalogue is empty — run tr02_s1_register.py first.")
    print("\n  Pass the asset id that tr02_s1_register.py printed, e.g.:")
    print(f"    python {sys.argv[0]} <asset-id>")
    sys.exit(0)

DEST_KEY = f"{ASSET_ID}.csv"

# ── Step 1: Negotiate contract ──────────────────────────────────────────────
print("=== Step 1: Negotiate contract ===")

dataset = edc.request_asset(ASSET_ID, MY_PROTOCOL)
offer = dataset["odrl:hasPolicy"]
if isinstance(offer, list):
    offer = offer[0]
offer_id = offer["@id"]
print(f"  Found offer: {offer_id}")

neg = edc.negotiate_contract(offer_id, ASSET_ID, MY_PROTOCOL, PARTICIPANT_NAME)
neg_id = neg["@id"]
print(f"  Negotiation started: {neg_id}")
agreement_id = edc.wait_for_negotiation(neg_id)
print(f"  Agreement: {agreement_id}")

# ── Step 2: Generate presigned URL ──────────────────────────────────────────
print("\n=== Step 2: Generate presigned URL ===")
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS,
    aws_secret_access_key=S3_SECRET,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)

presigned_url = s3.generate_presigned_url(
    "put_object",
    Params={"Bucket": DEST_BUCKET, "Key": DEST_KEY},
    ExpiresIn=300,
)
print(f"  Presigned URL ready for {DEST_BUCKET}/{DEST_KEY}")

# ── Step 3: Transfer ────────────────────────────────────────────────────────
print("\n=== Step 3: Transfer dataset ===")
xfer = edc.start_transfer(agreement_id, ASSET_ID, MY_PROTOCOL, PARTICIPANT_NAME, presigned_url)
xfer_id = xfer["@id"]
print(f"  Transfer started: {xfer_id}")
edc.wait_for_transfer(xfer_id)

# ── Step 4: Read and augment the data ──────────────────────────────────────
print("\n=== Step 4: Augment the data ===")
obj = s3.get_object(Bucket=DEST_BUCKET, Key=DEST_KEY)
content = obj["Body"].read().decode()
print(f"  Received {len(content)} bytes")

reader = csv.DictReader(io.StringIO(content))
rows = list(reader)
print(f"  Original rows: {len(rows)}, columns: {rows[0].keys() if rows else 'N/A'}")

# Derive four columns from the microservice-benchmark measurements: CPU
# utilisation against the configured limit, memory usage in MB, the tail-latency
# inflation ratio (p99/p50), and the per-row change in median latency. These use
# only columns present in every distribution of the dataset (cpu_usage,
# cpu_limit, ram_usage, lat50, lat99).
original_columns = list(rows[0].keys()) if rows else []
required = ["cpu_usage", "cpu_limit", "ram_usage", "lat50", "lat99"]
missing = [c for c in required if c not in original_columns]
if missing:
    raise KeyError(
        f"augmentation expects columns {required}; missing {missing} in "
        f"{original_columns}. Adjust the logic below for your dataset's schema."
    )

augmented_rows = []
for i, row in enumerate(rows):
    cpu_usage = float(row["cpu_usage"])
    cpu_limit = float(row["cpu_limit"])
    ram_usage = float(row["ram_usage"])
    lat50 = float(row["lat50"])
    lat99 = float(row["lat99"])

    row["cpu_utilisation_pct"] = round(cpu_usage / cpu_limit * 100, 2) if cpu_limit else 0.0
    row["ram_usage_mb"] = round(ram_usage / 1048576, 1)
    row["tail_latency_ratio"] = round(lat99 / lat50, 2) if lat50 else 0.0

    if i > 0:
        prev_lat50 = float(rows[i - 1]["lat50"])
        row["lat50_delta_us"] = round(lat50 - prev_lat50, 1)
    else:
        row["lat50_delta_us"] = 0.0

    augmented_rows.append(row)

new_columns = list(augmented_rows[0].keys())
print(f"  Augmented columns: {new_columns}")
print(f"\n  --- Augmentation Preview ---")
for row in augmented_rows[:3]:
    print(f"    t={row['time']}  cpu%={row['cpu_utilisation_pct']}  ram_mb={row['ram_usage_mb']}  "
          f"tail(p99/p50)={row['tail_latency_ratio']}  d_lat50={row['lat50_delta_us']}")

# ── Step 5: Upload augmented dataset to RustFS ─────────────────────────────
print("\n=== Step 5: Upload augmented dataset to RustFS ===")
RESULTS_BUCKET = "my-datasets"
# A fresh random id for the derived asset (not built from the source id). Its
# link back to the source is carried by prov:wasDerivedFrom inside the
# semantic_description, which the Catalog UI reads to nest it under its source.
DERIVED_ASSET_ID = str(uuid.uuid4())
RESULTS_KEY = f"{DERIVED_ASSET_ID}.csv"

output = io.StringIO()
writer = csv.DictWriter(output, fieldnames=new_columns)
writer.writeheader()
writer.writerows(augmented_rows)
augmented_csv = output.getvalue()
augmented_bytes = augmented_csv.encode()

s3.put_object(Bucket=RESULTS_BUCKET, Key=RESULTS_KEY, Body=augmented_bytes)
print(f"  Uploaded {RESULTS_KEY} to {RESULTS_BUCKET} ({len(augmented_csv)} bytes)")

# ── Step 6: Register as a new derived asset on EDC ─────────────────────────
print("\n=== Step 6: Register derived asset on EDC ===")

# Register the derived asset the same way as the original (tr02_s1_register.py)
# and the Track 1 portal: a DCAT-AP / GAIA-X / 6G-DALI MAP JSON-LD document in
# a single 'semantic_description' property. schema:variableMeasured is the
# augmented CSV header (new_columns), and PROV-O provenance is attached via
# extra_dataset so the derived asset links back to its source.
catalog_base = MY_MGMT.replace(":21001", ":21000")
semantic_description = build_semantic_description(
    asset_id=DERIVED_ASSET_ID,
    name=f"Microservice benchmark (augmented {RUN_TS})",
    csv_bytes=augmented_bytes,
    columns=new_columns,
    protocol_url=MY_PROTOCOL,
    catalog_base=catalog_base,
    description="Augmented microservice benchmark with derived CPU utilisation, memory usage in MB, tail-latency ratio (p99/p50) and per-row median-latency delta.",
    keywords=["microservices", "cloud-native", "augmented", "cpu", "memory", "latency", "tail latency", "derived"],
    issued=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    version=RUN_TS,
    extra_dataset={
        "prov:wasDerivedFrom": f"urn:dataset:{ASSET_ID}",
        "prov:wasGeneratedBy": "tr02_s5_pull_process_push",
        "prov:wasAttributedTo": PARTICIPANT_NAME,
    },
)

result = edc.create_asset(
    asset_id=DERIVED_ASSET_ID,
    name=f"Microservice benchmark (augmented {RUN_TS})",
    content_type="text/csv",
    data_address={
        "type": "MinioAsset",
        "endpoint": S3_INTERNAL,
        "bucketName": RESULTS_BUCKET,
        "accessKey": S3_ACCESS,
        "secretKey": S3_SECRET,
        "prefix": RESULTS_KEY,
    },
    metadata={"semantic_description": semantic_description},
)
print(f"  Derived asset registered: {result}")

print("\n=== Task 2 complete! ===")
print(f"  Original asset:  {ASSET_ID} ({len(original_columns)} columns, {len(rows)} rows)")
print(f"  Derived asset:   {DERIVED_ASSET_ID} ({len(new_columns)} columns, {len(augmented_rows)} rows)")
print(f"  Added columns:   cpu_utilisation_pct, ram_usage_mb, tail_latency_ratio, lat50_delta_us")
print(f"  Check the Catalog UI — both assets should be visible.")
