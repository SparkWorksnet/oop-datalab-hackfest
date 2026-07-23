#!/usr/bin/env python3
"""
Track 2 · Step 3 — Discover and pull a dataset from another participant's connector.

Usage: python tr02_s3_pull_peer.py

Configure MY_HOST, PEER_HOST and PEER_ASSET_ID in .env before running:
    PEER_HOST      the other participant's machine IP
    PEER_ASSET_ID  the asset id they registered (see their tr02_s1_register.py
                   output, or their Catalog UI)
"""

import sys

from config import (
    MY_MGMT, EDC_PROTOCOL_PORT,
    PEER_HOST, PEER_ASSET_ID, PEER_PARTICIPANT_ID,
    S3_ENDPOINT, S3_ACCESS, S3_SECRET,
)


def _missing(value):
    """A value is 'not configured' if it is empty or still a template placeholder."""
    if not value:
        return True
    v = value.strip()
    return not v or "XXX" in v or v.startswith("<")


def _catalog_participant_id(catalog):
    """The provider's own participant id, advertised at the catalogue root.

    The contract negotiation must address the peer by its real connector id
    (its PARTICIPANT_NAME / EDC_PARTICIPANT_ID), not a fixed guess — EDC rejects
    the offer otherwise. The peer's catalogue response carries it, keyed as
    'participantId', 'dspace:participantId', or a full IRI depending on prefix."""
    for key, value in catalog.items():
        local = key.lower().split(":")[-1].split("/")[-1]
        if local == "participantid" and isinstance(value, str):
            return value
    return None


# ── Check required .env config (before importing heavy deps) ────────────────
missing = [name for name, val in
           (("PEER_HOST", PEER_HOST), ("PEER_ASSET_ID", PEER_ASSET_ID))
           if _missing(val)]
if missing:
    print("  [ERROR] Missing required configuration: " + ", ".join(missing))
    print()
    print("  This step pulls a dataset from another participant. Add the following")
    print("  to your .env file (participant/.env) and run again:")
    print()
    print("    PEER_HOST=<the other participant's machine IP>")
    print("    PEER_ASSET_ID=<the asset id they registered>")
    print()
    print("  Ask your peer for their IP and asset id — the asset id is printed by")
    print("  their tr02_s1_register.py run and shown in their Catalog UI.")
    sys.exit(1)

import boto3
from botocore.client import Config

from helpers import EdcClient

PEER_PROTOCOL = f"http://{PEER_HOST}:{EDC_PROTOCOL_PORT}/protocol"
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

# The peer's connector id, needed to address negotiation/transfer to them.
# Prefer what their catalogue advertises; fall back to PEER_PARTICIPANT_ID from
# .env (an optional override for the rare case the catalogue omits it).
peer_participant_id = _catalog_participant_id(catalog) or PEER_PARTICIPANT_ID
print(f"  Peer participant id: {peer_participant_id}")

# ── Step 2: Select the configured asset and negotiate ───────────────────────
target = next((ds for ds in datasets if ds.get("@id") == PEER_ASSET_ID), None)
if target is None:
    print(f"\n  [ERROR] Asset '{PEER_ASSET_ID}' is not in the peer's catalogue.")
    print("  Set PEER_ASSET_ID in .env to one of the ids listed above.")
    sys.exit(1)
asset_id = target["@id"]
print(f"\n=== Step 2: Negotiate contract for '{asset_id}' ===")

offer = target["odrl:hasPolicy"]
if isinstance(offer, list):
    offer = offer[0]
offer_id = offer["@id"]
print(f"  Found offer: {offer_id}")

neg = edc.negotiate_contract(offer_id, asset_id, PEER_PROTOCOL, peer_participant_id)
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

xfer = edc.start_transfer(agreement_id, asset_id, PEER_PROTOCOL, peer_participant_id, presigned_url)
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
