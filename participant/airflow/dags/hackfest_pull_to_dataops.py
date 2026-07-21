"""
DAG: hackfest_pull_to_dataops

Hackfest clone of 6G-DALI's dali_demo_op DAG: pulls a dataset via EDC
connector-to-connector transfer, loads it into a pandas DataFrame, and
prints it to the logs.

Trigger via dag_run.conf:
{
    "asset_id": "<uuid printed by tr02_s1_register.py>"
}

The dataset is pulled from your own connector's catalogue and pushed to a
presigned URL on your own RustFS "dataops" bucket; the transferred object
lands at  dataops/<asset_id>.csv.

Configuration (from the environment, not DAG params — see
dali.datalake for defaults):
    EDC_MGMT_URL        Your EDC connector's management API
    EDC_PROTOCOL_URL    Your EDC connector's protocol (DSP) API — used as
                        counterPartyAddress for the self-transfer
    PARTICIPANT_ID      Connector ID asserted during negotiation/transfer
    S3_ENDPOINT         RustFS endpoint reachable from this container
    S3_ACCESS / S3_SECRET  RustFS credentials
    DEST_BUCKET         Destination RustFS bucket (default: "dataops")
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
from airflow.decorators import dag, task
from airflow.models.param import Param

from dali.datalake import download_dataset_edc


@task
def load_dataframe(csv_content: str) -> pd.DataFrame:
    """Parse the downloaded CSV content into a DataFrame."""
    return pd.read_csv(io.StringIO(csv_content))


@task
def print_rows(df: pd.DataFrame) -> None:
    """Print the DataFrame."""
    print(f"[hackfest_pull_to_dataops] {len(df)} rows total, columns={list(df.columns)}")
    print(df)


@dag(
    dag_id="hackfest_pull_to_dataops",
    description="Pull a dataset from your own EDC connector into the dataops RustFS bucket",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hackfest", "edc", "dataops"],
    params={
        "asset_id": Param("", type="string", description="Asset ID registered on your own connector"),
    },
)
def hackfest_pull_to_dataops():
    downloaded = download_dataset_edc()
    df = load_dataframe(downloaded["content"])
    print_rows(df)


hackfest_pull_to_dataops()