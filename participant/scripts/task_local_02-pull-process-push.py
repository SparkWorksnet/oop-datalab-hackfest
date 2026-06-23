#!/usr/bin/env python3
"""
Task 2 — Pull a dataset from your own connector, process it, and push the results back.

Usage: python task_local_02-pull-process-push.py

Configure MY_HOST and other settings in .env before running.
Run task_local_01-register.py first to register the asset.

Steps:
  1. Negotiate a contract for the asset on your own connector
  2. Generate a presigned URL for the destination bucket
  3. Transfer the file via the EDC
  4. Read and process the transferred data
  5. Upload the processed results to RustFS
  6. Register the results as a new derived asset on the EDC
"""

import csv
import io
import json
from datetime import datetime, timezone

import boto3
from botocore.client import Config

from config import (
    MY_MGMT, MY_PROTOCOL, PARTICIPANT_NAME,
    S3_ENDPOINT, S3_INTERNAL, S3_ACCESS, S3_SECRET,
)
from helpers import EdcClient

DEST_BUCKET = "received"
ASSET_ID = "my-measurement"
DEST_KEY = "my-measurement.csv"

RUN_TS = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

# ── Step 1: Negotiate contract ──────────────────────────────────────────────
print("=== Step 1: Negotiate contract ===")
edc = EdcClient(MY_MGMT)

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

augmented_rows = []
for i, row in enumerate(rows):
    throughput = float(row["throughput_mbps"])
    latency = float(row["latency_ms"])

    row["throughput_category"] = "high" if throughput >= 150 else "medium" if throughput >= 100 else "low"
    row["latency_category"] = "good" if latency <= 10 else "acceptable" if latency <= 20 else "poor"
    row["efficiency_score"] = round(throughput / latency, 2)

    if i > 0:
        prev_throughput = float(rows[i - 1]["throughput_mbps"])
        row["throughput_delta_mbps"] = round(throughput - prev_throughput, 1)
    else:
        row["throughput_delta_mbps"] = 0.0

    augmented_rows.append(row)

new_columns = list(augmented_rows[0].keys())
print(f"  Augmented columns: {new_columns}")
print(f"\n  --- Augmentation Preview ---")
for row in augmented_rows[:3]:
    print(f"    {row['timestamp']}  tput={row['throughput_mbps']}({row['throughput_category']})  "
          f"lat={row['latency_ms']}({row['latency_category']})  "
          f"eff={row['efficiency_score']}  delta={row['throughput_delta_mbps']}")

# ── Step 5: Upload augmented dataset to RustFS ─────────────────────────────
print("\n=== Step 5: Upload augmented dataset to RustFS ===")
RESULTS_BUCKET = "my-datasets"
RESULTS_KEY = f"my-measurement-augmented-{RUN_TS}.csv"
DERIVED_ASSET_ID = f"my-measurement-augmented-{RUN_TS}"

output = io.StringIO()
writer = csv.DictWriter(output, fieldnames=new_columns)
writer.writeheader()
writer.writerows(augmented_rows)
augmented_csv = output.getvalue()

s3.put_object(Bucket=RESULTS_BUCKET, Key=RESULTS_KEY, Body=augmented_csv.encode())
print(f"  Uploaded {RESULTS_KEY} to {RESULTS_BUCKET} ({len(augmented_csv)} bytes)")

# ── Step 6: Register as a new derived asset on EDC ─────────────────────────
print("\n=== Step 6: Register derived asset on EDC ===")

result = edc.create_asset(
    asset_id=DERIVED_ASSET_ID,
    name=f"My 5G Measurement (augmented {RUN_TS})",
    content_type="text/csv",
    data_address={
        "type": "MinioAsset",
        "endpoint": S3_INTERNAL,
        "bucketName": RESULTS_BUCKET,
        "accessKey": S3_ACCESS,
        "secretKey": S3_SECRET,
        "prefix": RESULTS_KEY,
    },
    metadata={
        # ── DCAT-AP core ────────────────────────────────────────────────
        "dct.description": "Augmented 5G NR dataset with derived throughput/latency categories and efficiency scores",
        "dct.issued": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "dct.publisher": "Hackfest Team",
        "dct.license": "https://creativecommons.org/licenses/by/4.0/",
        "dct.accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC",
        "dcat.keyword": "5G, NR, augmented, throughput, latency, efficiency, derived",
        "adms.version": RUN_TS,
        # ── Provenance (PROV-O) ─────────────────────────────────────────
        "prov.wasDerivedFrom": ASSET_ID,
        "prov.wasGeneratedBy": "hackfest-augmentation-pipeline",
        "prov.wasAttributedTo": PARTICIPANT_NAME,
        # ── 6G-DALI MAP ────────────────────────────────────────────────
        "dali.snsProjectName": "6G-DALI",
        "dali.gdprCompliant": "true",
        "dali.fairCompliant": "true",
        "schema.variableMeasured": "Throughput (Mbps), Latency (ms), throughput_category, latency_category, efficiency_score, throughput_delta_mbps",
    },
)
print(f"  Derived asset registered: {result}")

print("\n=== Task 2 complete! ===")
print(f"  Original asset:  {ASSET_ID} (3 columns, {len(rows)} rows)")
print(f"  Derived asset:   {DERIVED_ASSET_ID} ({len(new_columns)} columns, {len(augmented_rows)} rows)")
print(f"  Added columns:   throughput_category, latency_category, efficiency_score, throughput_delta_mbps")
print(f"  Check the Catalog UI — both assets should be visible.")
