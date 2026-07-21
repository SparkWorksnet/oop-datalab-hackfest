"""
DAG: hackfest_process_dataset

Hackfest clone of Track 3's task_local_02-pull-process-push.py script,
turned into a repeatable Airflow DAG: pulls a dataset from your own EDC
connector (self-transfer, see dali.datalake.download_dataset_edc), derives a
few new columns from it (throughput/latency categories, an efficiency
score, and a throughput delta between consecutive rows — the actual data
operation, unlike hackfest_pull_to_dataops which just prints what it pulled),
uploads the augmented CSV to the "my-datasets" RustFS bucket, and registers
it as a new derived asset on your own connector (prov:wasDerivedFrom the
source asset) — so it shows up in the Catalog UI nested under the original
(see catalog.html's lineage tree).

Trigger via dag_run.conf:
{
    "asset_id": "<uuid printed by tr02_s1_register.py>"
}

Expects "throughput_mbps" and "latency_ms" columns, matching
tr02_s1_register.py's sample data — adjust augment_data() if your own
dataset uses different column names.

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
from datetime import datetime, timezone

import pandas as pd
from airflow.decorators import dag, task
from airflow.models.param import Param
from airflow.sdk import get_current_context

from dali.datalake import (
    PARTICIPANT_ID,
    S3_ACCESS,
    S3_ENDPOINT,
    S3_SECRET,
    download_dataset_edc,
    register_derived_asset,
)


@task
def load_dataframe(csv_content: str) -> pd.DataFrame:
    """Parse the downloaded CSV content into a DataFrame."""
    return pd.read_csv(io.StringIO(csv_content))


@task
def augment_data(df: pd.DataFrame) -> pd.DataFrame:
    """Derive throughput/latency categories, an efficiency score, and a
    throughput delta between consecutive rows (see
    task_local_02-pull-process-push.py's Step 4 for the script version this
    mirrors).

    Resolves the throughput column by name rather than assuming a fixed
    schema: tr02_s1_register.py's sample data calls it "throughput_mbps",
    while the central connector's seed data (see
    central-edc/seed-data/sample-001.csv) calls it "throughput_dl_mbps" —
    both share "latency_ms"."""
    df = df.copy()

    throughput_col = next((c for c in ("throughput_mbps", "throughput_dl_mbps") if c in df.columns), None)
    latency_col = "latency_ms" if "latency_ms" in df.columns else None
    if not throughput_col or not latency_col:
        raise KeyError(
            "augment_data expects a throughput column (\"throughput_mbps\" or "
            "\"throughput_dl_mbps\") and a \"latency_ms\" column - found columns: "
            f"{list(df.columns)}. Adjust augment_data() for your dataset's schema."
        )

    df["throughput_category"] = df[throughput_col].apply(
        lambda t: "high" if t >= 150 else "medium" if t >= 100 else "low"
    )
    df["latency_category"] = df[latency_col].apply(
        lambda l: "good" if l <= 10 else "acceptable" if l <= 20 else "poor"
    )
    df["efficiency_score"] = (df[throughput_col] / df[latency_col]).round(2)
    df["throughput_delta_mbps"] = df[throughput_col].diff().fillna(0).round(1)
    print(f"[hackfest] augmented {len(df)} rows using throughput_col={throughput_col!r} latency_col={latency_col!r}; "
          f"added columns: throughput_category, latency_category, efficiency_score, throughput_delta_mbps")
    return df


@task
def push_derived_asset(df: pd.DataFrame) -> str:
    """Upload the augmented CSV to the "my-datasets" bucket and register it
    as a new derived asset on your own connector — mirrors
    task_local_02-pull-process-push.py's Steps 5-6, but as a repeatable DAG
    task instead of a one-off script.

    One dataset/asset per source, not one per run: the derived asset id and
    S3 key are both a fixed "<asset_id>-augmented" (no run timestamp), so
    re-running this DAG overwrites the same object and register_derived_asset
    simply skips re-registering an already-existing asset — lineage back to
    the source is carried entirely by the prov.* metadata below, not by a
    fresh id every time."""
    import boto3
    from botocore.client import Config

    params = get_current_context()["params"]
    asset_id = params["asset_id"]

    results_bucket = "my-datasets"
    results_key = f"{asset_id}-augmented.csv"
    derived_asset_id = f"{asset_id}-augmented"

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

    register_derived_asset(
        asset_id=derived_asset_id,
        name="Augmented dataset",
        content_type="text/csv",
        bucket=results_bucket,
        key=results_key,
        metadata={
            "dct.description": "Augmented dataset with derived throughput/latency categories and efficiency scores",
            "dct.issued": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "prov.wasDerivedFrom": asset_id,
            "prov.wasGeneratedBy": "hackfest_process_dataset",
            "prov.wasAttributedTo": PARTICIPANT_ID,
            "schema.variableMeasured": ", ".join(df.columns),
        },
    )
    print(f"[hackfest] registered derived asset '{derived_asset_id}' — visible in the Catalog UI under its source")
    return derived_asset_id


@dag(
    dag_id="hackfest_process_dataset",
    description="Pull a dataset, derive new columns from it, and push the result back as a new asset",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hackfest", "edc", "dataops"],
    params={
        "asset_id": Param("", type="string", description="Asset ID registered on your own connector"),
    },
)
def hackfest_process_dataset():
    downloaded = download_dataset_edc()
    df = load_dataframe(downloaded["content"])
    augmented = augment_data(df)
    push_derived_asset(augmented)


hackfest_process_dataset()
