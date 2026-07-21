"""
Hackfest clone of 6G-DALI's dali.datalake plugin: reusable Airflow tasks
for pulling datasets via EDC connector-to-connector transfer, shared across
DAGs (mirrors how the production DataOps stack keeps download_dataset_edc
in airflow/plugins/dali/datalake.py rather than inlined in each DAG).

Unlike the production plugin (separate provider/consumer EDC connectors,
S3 via an Airflow Connection), this hackfest stack has a single participant
EDC connector acting as both provider and consumer (a self-transfer), and
talks to RustFS directly with boto3 instead of an Airflow S3 Connection.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

import boto3
import requests
from airflow.decorators import task
from airflow.sdk import get_current_context
from botocore.client import Config

EDC_MGMT_URL     = os.getenv("EDC_MGMT_URL", "http://edc:21001")
EDC_PROTOCOL_URL = os.getenv("EDC_PROTOCOL_URL", "http://edc:21002/protocol")
PARTICIPANT_ID   = os.getenv("PARTICIPANT_ID", os.getenv("PARTICIPANT_NAME", "participant"))

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "http://rustfs:9000")
S3_ACCESS   = os.getenv("S3_ACCESS", "participant-admin")
S3_SECRET   = os.getenv("S3_SECRET", "participant-secret-2024")
DEST_BUCKET = os.getenv("DEST_BUCKET", "dataops")

EDC_POLL_INTERVAL = int(os.getenv("EDC_POLL_INTERVAL", "3"))
EDC_POLL_TIMEOUT  = int(os.getenv("EDC_POLL_TIMEOUT", "120"))


@task(multiple_outputs=True)
def download_dataset_edc() -> dict:
    """
    Pull a dataset from this participant's own EDC connector (a
    self-transfer: the same connector plays both provider and consumer)
    into the "dataops" RustFS bucket, and return its content.

    Required params:
        asset_id    Asset ID registered on your own connector

    The destination key in the dataops bucket is always "<asset_id>.csv" —
    it's just an internal staging name for the transferred file (this task
    reads it back), not something a caller needs to control.

    Returns {"content": ..., "asset_title": ...} — the same shape as the
    production DataOps stack's dali.datalake.download_dataset (see
    6gdali-dataops/airflow/plugins/dali/datalake.py), so downstream tasks
    written against that shape (e.g. a format-check/dataframe-parsing step)
    work unchanged here too.
    """
    params = get_current_context()["params"]
    asset_id = params["asset_id"]
    dest_key = f"{asset_id}.csv"

    headers = {"Content-Type": "application/json"}

    # ── 1. Catalogue lookup ──────────────────────────────────────────────
    print(f"[hackfest] requesting offer for asset '{asset_id}'")
    cat_resp = requests.post(
        f"{EDC_MGMT_URL}/management/v3/catalog/request",
        headers=headers,
        json={
            "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
            "counterPartyAddress": EDC_PROTOCOL_URL,
            "protocol": "dataspace-protocol-http",
            "querySpec": {
                "filterExpression": [{
                    "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
                    "operator": "=",
                    "operandRight": asset_id,
                }]
            },
        },
        timeout=30,
    )
    cat_resp.raise_for_status()
    catalog = cat_resp.json()

    datasets = catalog.get("dcat:dataset", [])
    if isinstance(datasets, dict):
        datasets = [datasets]
    if not datasets:
        raise RuntimeError(f"[hackfest] asset '{asset_id}' not found in your own catalogue")

    offer = datasets[0].get("odrl:hasPolicy", [])
    if isinstance(offer, list):
        offer = offer[0]
    offer_id = offer["@id"]
    print(f"[hackfest] found offer {offer_id}")

    # ── 2. Contract negotiation ──────────────────────────────────────────
    neg_resp = requests.post(
        f"{EDC_MGMT_URL}/management/v3/contractnegotiations",
        headers=headers,
        json={
            "@context": {
                "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
                "odrl":   "http://www.w3.org/ns/odrl/2/",
            },
            "@type":              "ContractRequest",
            "counterPartyAddress": EDC_PROTOCOL_URL,
            "providerId":          PARTICIPANT_ID,
            "protocol":            "dataspace-protocol-http",
            "policy": {
                "@id":              offer_id,
                "@type":            "http://www.w3.org/ns/odrl/2/Offer",
                "odrl:permission":  offer.get("odrl:permission", []),
                "odrl:prohibition": offer.get("odrl:prohibition", []),
                "odrl:obligation":  offer.get("odrl:obligation", []),
                "odrl:target":      {"@id": asset_id},
                "odrl:assigner":    {"@id": PARTICIPANT_ID},
            },
        },
        timeout=30,
    )
    neg_resp.raise_for_status()
    neg_id = neg_resp.json()["@id"]
    print(f"[hackfest] negotiation started: {neg_id}")

    agreement_id = None
    deadline = time.time() + EDC_POLL_TIMEOUT
    while time.time() < deadline:
        state_resp = requests.get(f"{EDC_MGMT_URL}/management/v3/contractnegotiations/{neg_id}", timeout=10)
        state_resp.raise_for_status()
        state = state_resp.json()
        neg_state = state.get("state", state.get("edc:state", ""))
        print(f"[hackfest] negotiation state: {neg_state}")
        if neg_state == "FINALIZED":
            agreement_id = state.get("contractAgreementId") or state.get("edc:contractAgreementId")
            print(f"[hackfest] agreement: {agreement_id}")
            break
        if neg_state in ("TERMINATED", "ERROR"):
            raise RuntimeError(f"[hackfest] negotiation failed with state: {neg_state}")
        time.sleep(EDC_POLL_INTERVAL)
    else:
        raise TimeoutError(f"[hackfest] negotiation did not complete within {EDC_POLL_TIMEOUT}s")

    # ── 3. Presigned PUT URL for the dataops bucket ──────────────────────
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    presigned_put_url = s3.generate_presigned_url(
        "put_object",
        Params={"Bucket": DEST_BUCKET, "Key": dest_key},
        ExpiresIn=EDC_POLL_TIMEOUT * 2,
    )
    print(f"[hackfest] presigned PUT URL generated for s3://{DEST_BUCKET}/{dest_key}")

    # ── 4. Transfer — your own connector PUTs to the presigned URL ───────
    xfer_resp = requests.post(
        f"{EDC_MGMT_URL}/management/v3/transferprocesses",
        headers=headers,
        json={
            "@context":            {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
            "@type":               "TransferRequest",
            "counterPartyAddress": EDC_PROTOCOL_URL,
            "connectorId":         PARTICIPANT_ID,
            "protocol":            "dataspace-protocol-http",
            "contractId":          agreement_id,
            "assetId":             asset_id,
            "transferType":        "PresignedHttpData-PUSH",
            "dataDestination": {
                "type":    "PresignedHttpData",
                "baseUrl": presigned_put_url,
                "method":  "PUT",
            },
        },
        timeout=30,
    )
    xfer_resp.raise_for_status()
    xfer_id = xfer_resp.json()["@id"]
    print(f"[hackfest] transfer started: {xfer_id}")

    # ── 5. Poll until transfer is COMPLETED ──────────────────────────────
    deadline = time.time() + EDC_POLL_TIMEOUT
    while time.time() < deadline:
        xstate_resp = requests.get(f"{EDC_MGMT_URL}/management/v3/transferprocesses/{xfer_id}", timeout=10)
        xstate_resp.raise_for_status()
        xfer_state = xstate_resp.json().get("state", xstate_resp.json().get("edc:state", ""))
        print(f"[hackfest] transfer state: {xfer_state}")
        if xfer_state == "COMPLETED":
            break
        if xfer_state in ("TERMINATED", "ERROR"):
            raise RuntimeError(f"[hackfest] transfer failed with state: {xfer_state}")
        time.sleep(EDC_POLL_INTERVAL)
    else:
        raise TimeoutError(f"[hackfest] transfer did not complete within {EDC_POLL_TIMEOUT}s")

    # ── 6. Retrieve the transferred file from RustFS ─────────────────────
    print(f"[hackfest] retrieving {dest_key} from bucket {DEST_BUCKET}")
    obj = s3.get_object(Bucket=DEST_BUCKET, Key=dest_key)
    content = obj["Body"].read().decode("utf-8")
    return {"content": content, "asset_title": dest_key}


def fetch_columns_from_asset(asset_id: str) -> list[str]:
    """Auto-generate expectations from schema.variableMeasured, read directly
    off this connector's own asset properties (see tr02_s1_register.py's
    metadata dict) — the hackfest's no-piveau equivalent of the production
    dali.utils.fetch_columns_from_piveau (there's no catalogue record here,
    just the asset registered on your own connector). A plain function, not
    a @task — it's called from inside dali.validation.run_expectations'
    task body, not wired into the DAG's task graph."""
    resp = requests.get(f"{EDC_MGMT_URL}/management/v3/assets/{asset_id}", timeout=10)
    resp.raise_for_status()
    props = resp.json().get("properties", {})
    raw = props.get("schema.variableMeasured", "")
    return [c.strip() for c in raw.split(",") if c.strip()]


def register_derived_asset(asset_id: str, name: str, content_type: str, bucket: str, key: str, metadata: dict | None = None) -> dict:
    """Register a new asset on this connector, pointing at a file already
    uploaded to RustFS — the hackfest's plain-function equivalent of
    scripts/helpers.py's EdcClient.create_asset (see tr02_s1_register.py and
    task_local_02-pull-process-push.py's Step 6), reused here so a DAG can
    register its own derived output the same way a Track 2/3 script would.
    A plain function, not a @task — called from inside a DAG task body."""
    properties = {"name": name, "contenttype": content_type}
    if metadata:
        properties.update(metadata)
    resp = requests.post(
        f"{EDC_MGMT_URL}/management/v3/assets",
        headers={"Content-Type": "application/json"},
        json={
            "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
            "@id": asset_id,
            "properties": properties,
            "dataAddress": {
                "type": "MinioAsset",
                "endpoint": S3_ENDPOINT,
                "bucketName": bucket,
                "accessKey": S3_ACCESS,
                "secretKey": S3_SECRET,
                "prefix": key,
            },
        },
        timeout=30,
    )
    if resp.status_code == 409:
        print(f"[hackfest] asset '{asset_id}' already exists, skipping registration")
        return {"@id": asset_id, "status": "already_exists"}
    resp.raise_for_status()
    return resp.json() if resp.text else {"@id": asset_id, "status": resp.status_code}


@task
def upload_results(report: dict) -> str:
    """Write a validation report JSON back next to the original asset's own
    file — same bucket/credentials as its registered dataAddress (see
    tr02_s1_register.py), named after that file rather than staged in the
    "dataops" bucket. The hackfest's no-piveau equivalent of the production
    dali.datalake.upload_results: no piveau catalogue to publish
    dqv:QualityMeasurement nodes to afterward, but the report still lives
    alongside the data it describes, matching the Catalog UI's "Validation"
    view (which looks it up the same way — see CatalogUiController.
    getValidationReport)."""
    params = get_current_context()["params"]
    asset_id = params["asset_id"]

    asset_resp = requests.get(f"{EDC_MGMT_URL}/management/v3/assets/{asset_id}", timeout=10)
    asset_resp.raise_for_status()
    data_address = asset_resp.json().get("dataAddress", {})
    bucket = data_address.get("bucketName", DEST_BUCKET)
    endpoint = data_address.get("endpoint", S3_ENDPOINT)
    access_key = data_address.get("accessKey", S3_ACCESS)
    secret_key = data_address.get("secretKey", S3_SECRET)
    prefix = data_address.get("prefix", report["input_key"])

    base = os.path.splitext(prefix)[0]
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_key = f"{base}_{ts}.gx.json"

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    print(f"[hackfest] uploading validation report to s3://{bucket}/{output_key}")
    s3.put_object(
        Bucket=bucket,
        Key=output_key,
        Body=json.dumps(report, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    return output_key
