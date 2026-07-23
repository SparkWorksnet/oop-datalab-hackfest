"""
DAG: hackfest_augment_dataset

The row-augmentation counterpart to hackfest_enrich_dataset. Where the enrich
DAG adds *columns* (feature engineering), this DAG adds *rows*: it pulls a
dataset from your own EDC connector (self-transfer, see
dali.datalake.download_dataset_edc), inserts a new interpolated row between every
pair of consecutive measurements (linear midpoint of the numeric columns;
non-numeric columns carry the earlier row's value), uploads the up-sampled CSV
to the "my-datasets" RustFS bucket, and registers it as a new derived asset on
your own connector.

Provenance (prov:wasDerivedFrom the source asset) lives inside the asset's
semantic_description JSON-LD, which the Catalog UI reads to nest this derived
asset under its source. Each run registers a fresh, randomly-identified asset,
so re-running builds a version history.

Trigger via dag_run.conf:
{
    "asset_id": "<uuid printed by tr02_s1_register.py>"
}

Works on any numeric CSV — it interpolates whatever numeric columns it finds, so
no fixed schema is required (unlike hackfest_enrich_dataset).

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

import numpy as np
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
def interpolate_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Insert one interpolated row between each pair of consecutive rows.

    Numeric columns get the linear midpoint of the two neighbouring rows;
    non-numeric columns (e.g. a "500M" memory-limit label) carry the earlier
    row's value. Row order is preserved: original, interpolated, original, …
    doubling the sampling resolution to (2n - 1) rows."""
    if len(df) < 2:
        print(f"[hackfest] {len(df)} row(s) — nothing to interpolate between; returning unchanged")
        return df

    a = df.reset_index(drop=True)
    num_cols = a.select_dtypes(include="number").columns.tolist()
    non_num = [c for c in a.columns if c not in num_cols]

    # Midpoint of each numeric column between rows i and i+1 (n-1 new rows).
    # Rounded to tame floating-point noise (e.g. 0.30000000000000004 -> 0.3).
    mids = np.round((a[num_cols].to_numpy()[:-1] + a[num_cols].to_numpy()[1:]) / 2.0, 6)
    mid = pd.DataFrame(mids, columns=num_cols)
    for c in non_num:
        mid[c] = a[c].to_numpy()[:-1]
    mid = mid[a.columns]  # restore original column order

    # Interleave: original rows at even slots, interpolated rows at odd slots.
    combined = pd.concat([a, mid], ignore_index=True)
    n = len(a)
    order = np.empty(2 * n - 1, dtype=int)
    order[0::2] = np.arange(n)
    order[1::2] = np.arange(n - 1) + n
    result = combined.iloc[order].reset_index(drop=True)

    print(f"[hackfest] interpolated {n} rows -> {len(result)} rows "
          f"(inserted {n - 1} rows across numeric columns {num_cols})")
    return result


@task
def push_derived_asset(df: pd.DataFrame) -> str:
    """Upload the up-sampled CSV to the "my-datasets" bucket and register it as
    a new derived asset on your own connector.

    Each run registers a fresh, randomly-identified derived asset; the link back
    to the source is carried by prov:wasDerivedFrom inside the asset's
    semantic_description JSON-LD, which the Catalog UI reads to nest it under its
    source."""
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
        name=f"Microservice benchmark (interpolated {run_ts})",
        csv_bytes=csv_bytes,
        columns=list(df.columns),
        protocol_url=EDC_PROTOCOL_URL,
        catalog_base=catalog_base,
        description="Row-augmented microservice benchmark: an interpolated (linear-midpoint) row inserted between every pair of consecutive measurements, doubling the sampling resolution.",
        keywords=["microservices", "cloud-native", "augmented", "interpolation", "up-sampled", "derived"],
        issued=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        version=run_ts,
        # PROV-O provenance lives inside the semantic_description; the Catalog UI
        # reads prov:wasDerivedFrom from here to nest this under its source.
        extra_dataset={
            "prov:wasDerivedFrom": f"urn:dataset:{asset_id}",
            "prov:wasGeneratedBy": "hackfest_augment_dataset",
            "prov:wasAttributedTo": PARTICIPANT_ID,
        },
    )
    register_derived_asset(
        asset_id=derived_asset_id,
        name=f"Microservice benchmark (interpolated {run_ts})",
        content_type="text/csv",
        bucket=results_bucket,
        key=results_key,
        metadata={"semantic_description": semantic_description},
    )
    print(f"[hackfest] registered derived asset '{derived_asset_id}' — visible in the Catalog UI under its source")
    return derived_asset_id


@dag(
    dag_id="hackfest_augment_dataset",
    description="Pull a dataset, insert interpolated rows between measurements, and push the result back as a new asset",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hackfest", "edc", "dataops"],
    params={
        "asset_id": Param("", type="string", description="Asset ID registered on your own connector"),
    },
)
def hackfest_augment_dataset():
    downloaded = download_dataset_edc()
    df = load_dataframe(downloaded["content"])
    interpolated = interpolate_rows(df)
    push_derived_asset(interpolated)


hackfest_augment_dataset()
