#!/usr/bin/env python3
"""
Exercise 3 — Pull a dataset from the central EDC into your local RustFS.

Usage: python exercise3_central.py

Configure CENTRAL_HOST and MY_HOST in .env before running.

Steps:
  1. Browse the central EDC catalogue from your connector
  2. Negotiate a contract for a dataset
  3. Generate a presigned URL on your local RustFS
  4. Transfer the dataset from the central EDC to your local storage
"""

import boto3
from botocore.client import Config

from config import (
    MY_MGMT, CENTRAL_HOST, CENTRAL_PROTOCOL, CENTRAL_PARTICIPANT_ID,
    S3_ENDPOINT, S3_INTERNAL, S3_ACCESS, S3_SECRET,
)
from helpers import EdcClient

DEST_BUCKET = "received"
ASSET_ID = "hackfest-sample-001"

# ── Step 1: Browse the central catalogue ────────────────────────────────────
print(f"=== Step 1: Browse central EDC catalogue at {CENTRAL_HOST} ===")
edc = EdcClient(MY_MGMT)

catalog = edc.request_catalogue(CENTRAL_PROTOCOL)
datasets = catalog.get("dcat:dataset", [])
if isinstance(datasets, dict):
    datasets = [datasets]
print(f"  Found {len(datasets)} dataset(s) in the central catalogue:")
for ds in datasets:
    ds_id = ds.get("@id", "?")
    print(f"    - {ds_id}")

# ── Step 2: Request specific asset and negotiate ───────────────────────────
print(f"\n=== Step 2: Negotiate contract for '{ASSET_ID}' ===")
dataset = edc.request_asset(ASSET_ID, CENTRAL_PROTOCOL)
offer = dataset["odrl:hasPolicy"]
if isinstance(offer, list):
    offer = offer[0]
offer_id = offer["@id"]
print(f"  Found offer: {offer_id}")

neg = edc.negotiate_contract(offer_id, ASSET_ID, CENTRAL_PROTOCOL, CENTRAL_PARTICIPANT_ID)
neg_id = neg["@id"]
print(f"  Negotiation started: {neg_id}")
agreement_id = edc.wait_for_negotiation(neg_id)
print(f"  Agreement: {agreement_id}")

# ── Step 3: Generate presigned URL on local RustFS ──────────────────────────
print("\n=== Step 3: Generate presigned URL ===")
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS,
    aws_secret_access_key=S3_SECRET,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)

dest_key = f"from-central/{ASSET_ID}.csv"
presigned_url = s3.generate_presigned_url(
    "put_object",
    Params={"Bucket": DEST_BUCKET, "Key": dest_key},
    ExpiresIn=300,
)
print(f"  Presigned URL ready for {DEST_BUCKET}/{dest_key}")

# ── Step 4: Start the transfer ──────────────────────────────────────────────
print("\n=== Step 4: Transfer dataset ===")
xfer = edc.start_transfer(agreement_id, ASSET_ID, CENTRAL_PROTOCOL, CENTRAL_PARTICIPANT_ID, presigned_url)
xfer_id = xfer["@id"]
print(f"  Transfer started: {xfer_id}")
edc.wait_for_transfer(xfer_id)

# ── Verify ──────────────────────────────────────────────────────────────────
print("\n=== Verify ===")
obj = s3.get_object(Bucket=DEST_BUCKET, Key=dest_key)
content = obj["Body"].read().decode()
print(f"  Received {len(content)} bytes in '{DEST_BUCKET}/{dest_key}'")
print(f"  Preview: {content[:300]}")
print("\n=== Exercise 2 complete! ===")
