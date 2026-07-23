#!/usr/bin/env python3
"""
Track 2 · Step 2 — Pull a dataset from the central EDC into your local RustFS.

Programmatic access: discover the central catalogue, negotiate a contract,
transfer a dataset to your local storage, and verify it locally.

Usage:
    python tr02_s2_pull_central.py [ASSET_ID]

    ASSET_ID  Optional. The dataset to pull from the central catalogue.
              Defaults to the central RabbitMQ sample
              ('cfdedca2-998e-46f9-b860-1bbf2aeb6a2f'). Run without an argument
              first to see what the central connector is offering.

Configure CENTRAL_HOST and MY_HOST in .env before running.

Steps:
    1. Browse the central EDC catalogue from your connector
    2. Negotiate a contract for the chosen dataset
    3. Generate a presigned PUT URL on your local RustFS
    4. Transfer the dataset from the central EDC to your local storage
    5. Verify the file landed in your local 'received' bucket
"""

import argparse
import mimetypes
import sys

import boto3
from botocore.client import Config

from config import (
    MY_MGMT, MY_HOST, EDC_MGMT_PORT,
    CENTRAL_HOST, CENTRAL_PROTOCOL, CENTRAL_PARTICIPANT_ID,
    S3_ENDPOINT, S3_ACCESS, S3_SECRET,
)
from helpers import EdcClient

# Central RabbitMQ sample (see central-edc/setup-assets.sh)
DEFAULT_ASSET_ID = "cfdedca2-998e-46f9-b860-1bbf2aeb6a2f"
DEST_BUCKET = "received"
DEST_PREFIX = "from-central"

# Content types whose extension mimetypes can't reliably guess.
_CONTENT_TYPE_EXT = {
    "text/csv": ".csv",
    "text/tab-separated-values": ".tsv",
    "application/json": ".json",
    "application/x-parquet": ".parquet",
}


def _find_prop(dataset, suffix):
    """Find a string property on a JSON-LD dataset regardless of its prefix.

    Catalogue entries may key properties as 'name', 'edc:name', or a full IRI;
    this matches on the local part (the bit after the last ':' or '/')."""
    suffix = suffix.lower()
    for key, value in dataset.items():
        local = key.lower().split(":")[-1].split("/")[-1]
        if local == suffix and isinstance(value, str):
            return value
    return None


def guess_extension(dataset, asset_id):
    """Derive a sensible file extension from the dataset's name or content type."""
    name = _find_prop(dataset, "name")
    if name and "." in name.rsplit("/", 1)[-1]:
        return "." + name.rsplit(".", 1)[-1]

    content_type = _find_prop(dataset, "contenttype")
    if content_type:
        content_type = content_type.split(";")[0].strip()
        if content_type in _CONTENT_TYPE_EXT:
            return _CONTENT_TYPE_EXT[content_type]
        ext = mimetypes.guess_extension(content_type)
        if ext:
            return ext

    return ".csv"


def main():
    parser = argparse.ArgumentParser(
        description="Pull a dataset from the central EDC into your local RustFS."
    )
    parser.add_argument(
        "asset_id", nargs="?", default=DEFAULT_ASSET_ID,
        help=f"Dataset to pull (default: {DEFAULT_ASSET_ID})",
    )
    args = parser.parse_args()
    asset_id = args.asset_id

    edc = EdcClient(MY_MGMT)

    # ── Step 1: Browse the central catalogue ────────────────────────────────
    print(f"=== Step 1: Browse central EDC catalogue at {CENTRAL_HOST} ===")
    catalog = edc.request_catalogue(CENTRAL_PROTOCOL)
    datasets = catalog.get("dcat:dataset", [])
    if isinstance(datasets, dict):
        datasets = [datasets]
    print(f"  Found {len(datasets)} dataset(s) in the central catalogue:")
    for ds in datasets:
        print(f"    - {ds.get('@id', '?')}")

    available = {ds.get("@id") for ds in datasets}
    if asset_id not in available:
        print(f"\n  [ERROR] Asset '{asset_id}' is not in the central catalogue.")
        print("  Pass one of the IDs listed above as an argument, e.g.:")
        print(f"    python {sys.argv[0]} <asset-id>")
        sys.exit(1)

    # ── Step 2: Request the chosen asset and negotiate ──────────────────────
    print(f"\n=== Step 2: Negotiate contract for '{asset_id}' ===")
    dataset = edc.request_asset(asset_id, CENTRAL_PROTOCOL)
    offer = dataset["odrl:hasPolicy"]
    if isinstance(offer, list):
        offer = offer[0]
    offer_id = offer["@id"]
    print(f"  Found offer: {offer_id}")

    neg = edc.negotiate_contract(offer_id, asset_id, CENTRAL_PROTOCOL, CENTRAL_PARTICIPANT_ID)
    neg_id = neg["@id"]
    print(f"  Negotiation started: {neg_id}")
    agreement_id = edc.wait_for_negotiation(neg_id)
    print(f"  Agreement: {agreement_id}")

    # ── Step 3: Generate a presigned PUT URL on the local RustFS ────────────
    print("\n=== Step 3: Generate presigned URL on local RustFS ===")
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )

    ext = guess_extension(dataset, asset_id)
    dest_key = f"{DEST_PREFIX}/{asset_id}{ext}"
    presigned_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": DEST_BUCKET, "Key": dest_key},
        ExpiresIn=300,
    )
    print(f"  Presigned PUT URL ready for {DEST_BUCKET}/{dest_key}")

    # ── Step 4: Start the transfer ──────────────────────────────────────────
    print("\n=== Step 4: Transfer dataset ===")
    xfer = edc.start_transfer(
        agreement_id, asset_id, CENTRAL_PROTOCOL, CENTRAL_PARTICIPANT_ID, presigned_url
    )
    xfer_id = xfer["@id"]
    print(f"  Transfer started: {xfer_id}")
    edc.wait_for_transfer(xfer_id)

    # ── Step 5: Verify ──────────────────────────────────────────────────────
    print("\n=== Step 5: Verify ===")
    obj = s3.get_object(Bucket=DEST_BUCKET, Key=dest_key)
    content = obj["Body"].read()
    print(f"  Received {len(content)} bytes in '{DEST_BUCKET}/{dest_key}'")
    try:
        preview = content[:300].decode()
        print(f"  Preview:\n{preview}")
    except UnicodeDecodeError:
        print("  (binary content — skipping preview)")

    catalog_ui = MY_MGMT.replace(f":{EDC_MGMT_PORT}", ":21000")
    print("\n=== Track 1 pull complete! ===")
    print(f"  The dataset is now in your local '{DEST_BUCKET}' bucket.")
    print(f"  Browse your connector at {catalog_ui}/api/catalog")


if __name__ == "__main__":
    main()
