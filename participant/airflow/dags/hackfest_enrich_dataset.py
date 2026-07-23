"""
DAG: hackfest_enrich_dataset

Hackfest clone of Track 3's tr02_s5_pull_process_push.py script,
turned into a repeatable Airflow DAG: pulls a dataset from your own EDC
connector (self-transfer, see dali.datalake.download_dataset_edc), derives a
few new columns from it (CPU utilisation, memory usage in MB, a tail-latency
ratio and the median-latency delta between consecutive rows — the actual data
operation, unlike hackfest_pull_to_dataops which just prints what it pulled),
uploads the augmented CSV to the "my-datasets" RustFS bucket, and registers
it as a new derived asset on your own connector (prov:wasDerivedFrom the
source asset) — so it shows up in the Catalog UI nested under the original
(see catalog.html's lineage tree).

Trigger via dag_run.conf:
{
    "asset_id": "<uuid printed by tr02_s1_register.py>"
}

Expects "cpu_usage", "cpu_limit", "ram_usage", "lat50" and "lat99" columns,
matching the EURECOM microservice-benchmark data — adjust augment_data() if
your own dataset uses different column names.

Configuration (from the environment, not DAG params — see dali.datalake for
defaults):
    EDC_MGMT_URL        Your EDC connector's management API
    EDC_PROTOCOL_URL    Your EDC connector's protocol (DSP) API — used as
                        counterPartyAddress for the self-transfer
    PARTICIPANT_ID      Connector ID asserted during negotiation/transfer
    S3_ENDPOINT         RustFS endpoint reachable from this container
    S3_ACCESS / S3_SECRET  RustFS credentials
"""

from __future__ import annotations

import io
import re
import uuid
from datetime import datetime, timezone

import pandas as pd
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.sdk import get_current_context

from dali.datalake import (
    EDC_MGMT_URL,
    EDC_PROTOCOL_URL,
    PARTICIPANT_ID,
    S3_ACCESS,
    S3_ENDPOINT,
    S3_SECRET,
    download_dataset_edc,
    register_derived_asset,
)
from dali.semantic import build_semantic_description


@task
def load_dataframe(csv_content: str) -> pd.DataFrame:
    """Parse the downloaded CSV content into a DataFrame."""
    return pd.read_csv(io.StringIO(csv_content))


@task
def augment_data(df: pd.DataFrame) -> pd.DataFrame:
    """Derive CPU utilisation, memory usage in MB, a tail-latency ratio
    (p99/p50) and the per-row change in median latency (see
    tr02_s5_pull_process_push.py's Step 4 for the script version this
    mirrors).

    Uses only columns present in every distribution of the EURECOM
    microservice-benchmark dataset (cpu_usage, cpu_limit, ram_usage, lat50,
    lat99); raises with a clear message if the dataset has a different
    schema so you know to adapt this function."""
    df = df.copy()

    required = ["cpu_usage", "cpu_limit", "ram_usage", "lat50", "lat99"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(
            f"augment_data expects columns {required}; missing {missing} in "
            f"{list(df.columns)}. Adjust augment_data() for your dataset's schema."
        )

    df["cpu_utilisation_pct"] = (df["cpu_usage"] / df["cpu_limit"] * 100).round(2)
    df["ram_usage_mb"] = (df["ram_usage"] / 1048576).round(1)
    df["tail_latency_ratio"] = (df["lat99"] / df["lat50"]).round(2)
    df["lat50_delta_us"] = df["lat50"].diff().fillna(0).round(1)
    print(f"[hackfest] augmented {len(df)} rows; added columns: "
          "cpu_utilisation_pct, ram_usage_mb, tail_latency_ratio, lat50_delta_us")
    return df


@task
def push_derived_asset(df: pd.DataFrame) -> str:
    """Upload the augmented CSV to the "my-datasets" bucket and register it
    as a new derived asset on your own connector — mirrors
    tr02_s5_pull_process_push.py's Steps 5-6, but as a repeatable DAG
    task instead of a one-off script.

    Each run registers a fresh, randomly-identified derived asset (like the
    script), so re-running builds a version history of derived datasets. The
    link back to the source is carried by prov:wasDerivedFrom *inside the
    asset's semantic_description* JSON-LD document — the same shape the Track 2/3
    scripts and the Submission Portal produce — which the Catalog UI reads to
    nest this asset under its source."""
    import boto3
    from botocore.client import Config

    params = get_current_context()["params"]
    asset_id = params["asset_id"]

    results_bucket = "my-datasets"
    derived_asset_id = str(uuid.uuid4())
    results_key = f"{derived_asset_id}.csv"

    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        aws_access_key_id=S3_ACCESS,
        aws_secret_access_key=S3_SECRET,
        config=Config(signature_version="s3v4"),
        region_name="us-east-1",
    )
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    s3.put_object(Bucket=results_bucket, Key=results_key, Body=csv_bytes)
    print(f"[hackfest] uploaded {results_key} to {results_bucket} ({len(csv_bytes)} bytes)")

    run_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Catalog UI base = management URL with the mgmt port mapped to the UI port.
    catalog_base = re.sub(r":(\d+)(?=/|$)", lambda m: f":{int(m.group(1)) - 1}", EDC_MGMT_URL)
    semantic_description = build_semantic_description(
        asset_id=derived_asset_id,
        name=f"Microservice benchmark (augmented {run_ts})",
        csv_bytes=csv_bytes,
        columns=list(df.columns),
        protocol_url=EDC_PROTOCOL_URL,
        catalog_base=catalog_base,
        description="Augmented microservice benchmark with derived CPU utilisation, memory usage in MB, tail-latency ratio (p99/p50) and per-row median-latency delta.",
        keywords=["microservices", "cloud-native", "augmented", "cpu", "memory", "latency", "tail latency", "derived"],
        issued=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        version=run_ts,
        # PROV-O provenance lives inside the semantic_description; the Catalog UI
        # reads prov:wasDerivedFrom from here to nest this under its source.
        extra_dataset={
            "prov:wasDerivedFrom": f"urn:dataset:{asset_id}",
            "prov:wasGeneratedBy": "hackfest_enrich_dataset",
            "prov:wasAttributedTo": PARTICIPANT_ID,
        },
    )
    register_derived_asset(
        asset_id=derived_asset_id,
        name=f"Microservice benchmark (augmented {run_ts})",
        content_type="text/csv",
        bucket=results_bucket,
        key=results_key,
        metadata={"semantic_description": semantic_description},
    )
    print(f"[hackfest] registered derived asset '{derived_asset_id}' — visible in the Catalog UI under its source")
    return derived_asset_id


@dag(
    dag_id="hackfest_enrich_dataset",
    description="Pull a dataset, derive new columns from it, and push the result back as a new asset",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hackfest", "edc", "dataops"],
    params={
        "asset_id": Param("", type="string", description="Asset ID registered on your own connector"),
    },
)
def hackfest_enrich_dataset():
    downloaded = download_dataset_edc()
    df = load_dataframe(downloaded["content"])
    augmented = augment_data(df)
    push_derived_asset(augmented)


hackfest_enrich_dataset()
