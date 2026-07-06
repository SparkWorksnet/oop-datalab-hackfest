"""
DAG: hackfest_pull_to_dataops

Hackfest clone of 6G-DALI's dali_demo_op DAG: pulls a dataset via EDC
connector-to-connector transfer and prints each row of the CSV to the logs.

Trigger via dag_run.conf (both optional):
{
    "asset_id": "my-measurement",           # default: the Task 1 sample asset
    "dest_key": "my-measurement.csv"        # default: "<asset_id>.csv"
}

The dataset is pulled from your own connector's catalogue and pushed to a
presigned URL on your own RustFS "dataops" bucket; the transferred object
lands at  dataops/<dest_key>.

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

from datetime import datetime

from airflow.decorators import dag, task
from airflow.models.param import Param

from dali.datalake import download_dataset_edc


@task
def print_csv_rows(csv_content: str) -> None:
    """Print each row of the CSV with its line number."""
    lines = csv_content.splitlines()
    print(f"[hackfest_pull_to_dataops] {len(lines)} rows total")
    for i, line in enumerate(lines):
        print(f"[hackfest_pull_to_dataops] row {i:>4}: {line}")


@dag(
    dag_id="hackfest_pull_to_dataops",
    description="Pull a dataset from your own EDC connector into the dataops RustFS bucket",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hackfest", "edc", "dataops"],
    params={
        "asset_id": Param("my-measurement", type="string", description="Asset ID registered on your own connector"),
        "dest_key": Param("", type="string", description="Destination key in the dataops bucket (default: <asset_id>.csv)"),
    },
)
def hackfest_pull_to_dataops():
    csv_content = download_dataset_edc()
    print_csv_rows(csv_content)


hackfest_pull_to_dataops()