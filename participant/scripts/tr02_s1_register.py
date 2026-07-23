#!/usr/bin/env python3
"""
Track 2 · Step 1 — Register a dataset programmatically on your own connector.

The programmatic counterpart to the web-UI registration in Track 1: uploads
data, creates an asset with metadata, sets up access policies, then verifies
the asset in the Catalog UI.

Usage: python tr02_s1_register.py

Configure MY_HOST and other settings in .env before running.

Steps:
  1. Upload a CSV file to your local RustFS
  2. Register it as an asset on your EDC connector
  3. Create a policy and contract definition
  4. Query your own catalogue to verify the asset appears
"""

import uuid
from pathlib import Path

import boto3
from botocore.client import Config

from config import (
    MY_MGMT, MY_PROTOCOL,
    S3_ENDPOINT, S3_INTERNAL, S3_ACCESS, S3_SECRET,
)
from helpers import EdcClient, build_semantic_description

SOURCE_BUCKET = "my-datasets"

# A fresh id per run, rather than a fixed "my-measurement" — avoids clashing
# with an asset from a previous run (create_asset would just skip on a 409)
# and mirrors how the production DataOps stack assigns each distribution its
# own asset id instead of reusing one fixed value.
ASSET_ID = str(uuid.uuid4())

# ── Step 1: Upload a sample CSV to RustFS ───────────────────────────────────
print("=== Step 1: Upload sample data to RustFS ===")
s3 = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id=S3_ACCESS,
    aws_secret_access_key=S3_SECRET,
    config=Config(signature_version="s3v4"),
    region_name="us-east-1",
)

# Load the sample from the bundled seed-data instead of an inline literal,
# resolved relative to this script so it runs from any working directory.
CSV_PATH = Path(__file__).resolve().parent / "seed-data" / "file-4.csv"
OBJECT_KEY = "file-4.csv"

csv_bytes = CSV_PATH.read_bytes()
s3.put_object(Bucket=SOURCE_BUCKET, Key=OBJECT_KEY, Body=csv_bytes)
print(f"  Uploaded {OBJECT_KEY} to {SOURCE_BUCKET}")

# Measured variables = the CSV header, kept in sync with the data itself
# rather than hand-typed, so the validation DAG auto-generates a check per
# real column.
columns = csv_bytes.decode().splitlines()[0].split(",")

# ── Step 2: Register the asset on your EDC ──────────────────────────────────
print("\n=== Step 2: Register asset on EDC ===")
edc = EdcClient(MY_MGMT)

# Register the metadata the same way the Track 1 Dataset Submission Portal
# does: a full DCAT-AP / GAIA-X / 6G-DALI MAP JSON-LD document serialized into
# a single 'semantic_description' string property (with schema:variableMeasured
# nested on the distribution), instead of many flat dct.*/dali.* EDC properties.
# This is the shape dali.datalake.fetch_columns_from_asset parses.
catalog_base = MY_MGMT.replace(":21001", ":21000")
semantic_description = build_semantic_description(
    asset_id=ASSET_ID,
    name="Golang Web Server Performance Measurements",
    csv_bytes=csv_bytes,
    columns=columns,
    protocol_url=MY_PROTOCOL,
    catalog_base=catalog_base,
    description="CPU and memory consumption measurements for the Golang web server microservice under varying workloads and configurations, generated on the EURECOM 5G testbed to benchmark cloud-native microservice performance.",
    keywords=["Kafka", "NGINX", "microservices", "CPU consumption", "cloud-native",
              "AMF", "containerisation", "network function virtualisation",
              "performance", "workload", "InfluxDB", "NFV", "memory consumption",
              "5G core", "benchmarking"],
    issued="2022-07-19",
    version="1.0",
    # This is the Golang distribution of the EURECOM cloud-native benchmarking
    # dataset (CC BY 4.0, DOI 10.5281/zenodo.6907619), so record its real
    # publisher/creator/source rather than deriving them from the asset name.
    extra_dataset={
        "dct:publisher": {"@type": "foaf:Organization", "foaf:name": "EURECOM",
                          "foaf:homepage": "https://www.eurecom.fr"},
        "dct:creator": {"@type": "foaf:Person", "foaf:name": "Nassima Toumi"},
        "dct:source": "https://doi.org/10.5281/zenodo.6907619",
        "adms:identifier": "10.5281/zenodo.6907619",
    },
)

result = edc.create_asset(
    asset_id=ASSET_ID,
    name="Golang Web Server Performance Measurements",
    content_type="text/csv",
    data_address={
        "type": "MinioAsset",
        "endpoint": S3_INTERNAL,
        "bucketName": SOURCE_BUCKET,
        "accessKey": S3_ACCESS,
        "secretKey": S3_SECRET,
        "prefix": OBJECT_KEY,
    },
    metadata={"semantic_description": semantic_description},
)
print(f"  Asset created: {result}")
print(f"  Asset ID: {ASSET_ID}  (copy this for later steps/tasks)")

# ── Step 3: Create policy + contract definition ────────────────────────────
print("\n=== Step 3: Create policy + contract ===")
edc.create_open_policy()
edc.create_contract_definition()
print("  Policy and contract definition created")

# ── Step 4: Query your own catalogue to verify ─────────────────────────────
print("\n=== Step 4: Query catalogue ===")
dataset = edc.request_asset(ASSET_ID, MY_PROTOCOL)
offer = dataset["odrl:hasPolicy"]
if isinstance(offer, list):
    offer = offer[0]
offer_id = offer["@id"]
print(f"  Found asset with offer: {offer_id}")

print("\n=== Track 2 registration complete! ===")
print(f"  Your asset '{ASSET_ID}' is registered and visible in the catalogue.")
print(f"  Check the Catalog UI at {MY_MGMT.replace(':21001', ':21000')}/api/catalog")
print(f"  Use this asset id in later steps/tasks, e.g. Track 3's pull-process-push:")
print(f"    python tr02_s5_pull_process_push.py {ASSET_ID}")
