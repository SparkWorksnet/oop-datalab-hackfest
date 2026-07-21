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

import boto3
from botocore.client import Config

from config import (
    MY_MGMT, MY_PROTOCOL,
    S3_ENDPOINT, S3_INTERNAL, S3_ACCESS, S3_SECRET,
)
from helpers import EdcClient

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

sample_csv = "timestamp,throughput_mbps,latency_ms\n2024-01-01T00:00:00Z,150.5,12.3\n2024-01-01T00:01:00Z,148.2,13.1\n2024-01-01T00:02:00Z,152.0,11.8\n"
s3.put_object(Bucket=SOURCE_BUCKET, Key="my-measurement.csv", Body=sample_csv.encode())
print(f"  Uploaded my-measurement.csv to {SOURCE_BUCKET}")

# ── Step 2: Register the asset on your EDC ──────────────────────────────────
print("\n=== Step 2: Register asset on EDC ===")
edc = EdcClient(MY_MGMT)

result = edc.create_asset(
    asset_id=ASSET_ID,
    name="Some Measurement",
    content_type="text/csv",
    data_address={
        "type": "MinioAsset",
        "endpoint": S3_INTERNAL,
        "bucketName": SOURCE_BUCKET,
        "accessKey": S3_ACCESS,
        "secretKey": S3_SECRET,
        "prefix": "my-measurement.csv",
    },
    metadata={
        # ── DCAT-AP core fields ─────────────────────────────────────────
        "dct.description": "5G NR throughput and latency measurements from a controlled lab environment",
        "dct.issued": "2024-06-01",
        "dct.publisher": "Hackfest Team",
        "dct.license": "https://creativecommons.org/licenses/by/4.0/",
        "dct.accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC",
        "dcat.keyword": "5G, NR, throughput, latency, measurement",
        "dct.language": "http://publications.europa.eu/resource/authority/language/ENG",
        "adms.version": "1.0",
        # ── 6G-DALI MAP: project identity ───────────────────────────────
        "dali.snsProjectName": "6G-DALI",
        "dali.gdprCompliant": "true",
        "dali.fairCompliant": "true",
        # ── 6G-DALI MAP: testbed context ────────────────────────────────
        "dali.environment": "indoors",
        "dali.networkDomain": "RAN",
        "dali.ran3gppRelease": "Release 17",
        "dali.ranNewRadioType": "NR-SA",
        "dali.ranSplit": "No-Split",
        "dali.ranFocusedTechnology": "O-RAN",
        "dali.ranCoverageType": "Single_Micro",
        "dali.ranFrequencyBand": "n78",
        "dali.ranBandwidthMHz": "100",
        "dali.ranMaxEndDevices": "10",
        "dali.ranMobilityModel": "static",
        "dali.coreRelease": "Release 17",
        "dali.coreSolution": "OpenSource",
        "dali.transportType": "fiber_optics",
        "dali.computeOrchestratorType": "Kubernetes",
        "dali.computeGpuUse": "false",
        "dali.computeVirtualizationType": "Docker",
        # ── 6G-DALI MAP: experimentation ────────────────────────────────
        "dali.observationPointHorizontal": "End device to Access",
        "dali.observationPointVertical": "Radio Level",
        "dali.measurementFamily": "DRB",
        "dali.measurementTool": "Prometheus exporter",
        "schema.variableMeasured": "Throughput (Mbps), Latency (ms)",
    },
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
print(f"    python task_local_02-pull-process-push.py {ASSET_ID}")
