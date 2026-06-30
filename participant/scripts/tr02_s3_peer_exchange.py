#!/usr/bin/env python3
"""
Track 2 · Step 3 — Discover and pull a dataset from another participant's connector.

Usage: python tr02_s3_peer_exchange.py <PEER_IP>

Configure MY_HOST in .env before running.
"""

import sys

import boto3
from botocore.client import Config

from config import MY_MGMT, S3_ENDPOINT, S3_ACCESS, S3_SECRET
from helpers import EdcClient

if len(sys.argv) < 2:
    print("Usage: python tr02_s3_peer_exchange.py <PEER_IP>")
    print("  PEER_IP: IP address of another participant's machine")
    sys.exit(1)

PEER_HOST = sys.argv[1]
PEER_PROTOCOL = f"http://{PEER_HOST}:21002/protocol"
PEER_PARTICIPANT_ID = sys.argv[2] if len(sys.argv) > 2 else "participant"
DEST_BUCKET = "received"

# ── Step 1: Browse the peer's catalogue ─────────────────────────────────────
print(f"=== Step 1: Browse peer catalogue at {PEER_HOST} ===")
edc = EdcClient(MY_MGMT)

catalog = edc.request_catalogue(PEER_PROTOCOL)
datasets = catalog.get("dcat:dataset", [])
if isinstance(datasets, dict):
    datasets = [datasets]

if not datasets:
    print("  No datasets found in peer catalogue.")
    print("  Make sure the peer has run Task 1 (register) and has a contract definition.")
    sys.exit(1)

print(f"  Found {len(datasets)} dataset(s):")
for ds in datasets:
    ds_id = ds.get("@id", "?")
    print(f"    - {ds_id}")

# ── Step 2: Select first asset and negotiate ────────────────────────────────
target = datasets[0]
asset_id = target["@id"]
print(f"\n=== Step 2: Negotiate contract for '{asset_id}' ===")

offer = target["odrl:hasPolicy"]
if isinstance(offer, list):
    offer = offer[0]
offer_id = offer["@id"]
print(f"  Found offer: {offer_id}")

neg = edc.negotiate_contract(offer_id, asset_id, PEER_PROTOCOL, PEER_PARTICIPANT_ID)
neg_id = neg["@id"]
print(f"  Negotiation started: {neg_id}")
agreement_id = edc.wait_for_negotiation(neg_id)
print(f"  Agreement: {agreement_id}")

# ── Step 3: Generate presigned URL and transfer ─────────────────────────────
print("\n=== Step 3: Transfer dataset ===")
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS,
    aws_secret_access_key=S3_SECRET,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)

safe_name = asset_id.replace("/", "_")
dest_key = f"from-peer/{PEER_HOST}/{safe_name}"
presigned_url = s3.generate_presigned_url(
    "put_object",
    Params={"Bucket": DEST_BUCKET, "Key": dest_key},
    ExpiresIn=300,
)
print(f"  Destination: {DEST_BUCKET}/{dest_key}")

xfer = edc.start_transfer(agreement_id, asset_id, PEER_PROTOCOL, PEER_PARTICIPANT_ID, presigned_url)
xfer_id = xfer["@id"]
print(f"  Transfer started: {xfer_id}")
edc.wait_for_transfer(xfer_id)

# ── Verify ──────────────────────────────────────────────────────────────────
print("\n=== Verify ===")
obj = s3.get_object(Bucket=DEST_BUCKET, Key=dest_key)
content = obj["Body"].read().decode()
print(f"  Received {len(content)} bytes in '{DEST_BUCKET}/{dest_key}'")
print(f"  Preview: {content[:300]}")
print(f"\n=== Track 2 peer exchange complete! ===")
print(f"  Pulled '{asset_id}' from peer at {PEER_HOST}")
