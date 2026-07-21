"""
DAG: hackfest_validate_dataset

Hackfest clone of 6G-DALI's dali_dataspace_validate_dataset DAG: pulls a
dataset from your own EDC connector (self-transfer, see
dali.datalake.download_dataset_edc), checks its content actually matches its
own format (a proper CSV loadable into a DataFrame — see
dali.validation.validate_file_format), runs a configurable set of Great
Expectations checks, and writes the results as a JSON report back next to
the original file — same bucket/credentials as the asset's own registered
dataAddress (see dali.datalake.upload_results), not the "dataops" staging
bucket the pull step uses. That's also where the Catalog UI's "Validation"
button looks for it (see CatalogUiController.getValidationReport in
edc/connector-ui).

Two things this DAG does NOT do, unlike the production original, because
this hackfest stack has no piveau catalogue at all:
  - It never publishes dqv:QualityMeasurement nodes anywhere — there's no
    catalogue record to attach them to. report_outcome just logs the
    pass/fail summary instead of dali.dataspace.publish_quality_to_piveau.
  - When no "expectations" param is given, it auto-generates expectations
    from schema.variableMeasured read directly off the EDC asset's own
    properties (see dali.datalake.fetch_columns_from_asset), rather than
    from a piveau dataset record (see production's fetch_columns_from_piveau).

Trigger via dag_run.conf:
{
    "asset_id":     "<uuid printed by tr02_s1_register.py>",
    "expectations": [                                         # optional
        {"type": "expect_table_row_count_to_be_between", "min_value": 1},
        {"type": "expect_column_values_to_not_be_null",  "column": "timestamp"}
    ]
}

Configuration (from the environment, not DAG params — see dali.datalake for
defaults):
    EDC_MGMT_URL        Your EDC connector's management API
    EDC_PROTOCOL_URL    Your EDC connector's protocol (DSP) API — used as
                        counterPartyAddress for the self-transfer
    PARTICIPANT_ID      Connector ID asserted during negotiation/transfer
    S3_ENDPOINT         RustFS endpoint reachable from this container
    S3_ACCESS / S3_SECRET  RustFS credentials
    DEST_BUCKET         Staging bucket for the pulled file (default: "dataops") —
                        the validation report itself is written next to the
                        original asset instead, not into this bucket
"""

from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag
from airflow.models.param import Param

from dali.datalake import download_dataset_edc, upload_results
from dali.validation import report_outcome, run_expectations, validate_file_format


@dag(
    dag_id="hackfest_validate_dataset",
    description="Validate a dataset pulled from your own EDC connector with Great Expectations",
    start_date=datetime(2025, 1, 1),
    schedule=None,
    catchup=False,
    tags=["hackfest", "edc", "great-expectations", "validation"],
    params={
        "asset_id":     Param("", type="string", description="Asset ID registered on your own connector"),
        "expectations": Param([], type="array",  description="List of GX expectation configs"),
    },
)
def hackfest_validate_dataset():
    downloaded   = download_dataset_edc()
    format_check = validate_file_format(file_content=downloaded["content"], asset_title=downloaded["asset_title"])
    report       = run_expectations(
        file_content=downloaded["content"], asset_title=downloaded["asset_title"], format_check=format_check
    )
    output_key   = upload_results(report=report)
    report_outcome(output_key=output_key, report=report)


hackfest_validate_dataset()
