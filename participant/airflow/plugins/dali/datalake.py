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

import os
import time

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


@task
def download_dataset_edc() -> str:
    """
    Pull a dataset from this participant's own EDC connector (a
    self-transfer: the same connector plays both provider and consumer)
    into the "dataops" RustFS bucket, and return its content as a string.

    Required params:
        asset_id    Asset ID registered on your own connector
        dest_key    Destination key in the dataops bucket
                    (default: "<asset_id>.csv")
    """
    params = get_current_context()["params"]
    asset_id = params["asset_id"]
    dest_key = params["dest_key"] or f"{asset_id}.csv"

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
    return obj["Body"].read().decode("utf-8")
