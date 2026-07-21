"""
Hackfest clone of 6G-DALI's dali.utils plugin: format-detection/DataFrame-
parsing helpers shared by dali.validation. Trimmed to just what this
hackfest's validation DAG needs — no piveau helpers (fetch_columns_from_piveau,
dist_keys, node_types, ...) and no production S3/EDC connection constants,
since this stack has no piveau catalogue and dali.datalake already owns the
EDC/S3 endpoints it needs (see dali.datalake.fetch_columns_from_asset for the
no-piveau equivalent of the column auto-detection).
"""

from __future__ import annotations

import ast
import json
import math

import great_expectations as gx

DEFAULT_EXPECTATIONS = [
    {"type": "expect_table_row_count_to_be_between", "min_value": 1},
]


def sanitize(obj):
    """Recursively replace nan/inf floats with None so the result is JSON-safe."""
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    return obj


def detect_format(asset_title: str) -> str:
    """The file format label (csv/tsv/jsonl/json) inferred from asset_title's
    extension — used both to pick a parser (see dataframe_from_content) and
    to label the pre-flight format check (see dali.validation.validate_file_format).
    Defaults to csv, which also covers files with no/unrecognized extension."""
    ext = asset_title.rsplit(".", 1)[-1].lower() if "." in asset_title else ""
    if ext == "tsv":
        return "tsv"
    if ext in ("jsonl", "ndjson"):
        return "jsonl"
    if ext == "json":
        return "json"
    return "csv"


def dataframe_from_content(content: str, asset_title: str):
    """Load a distribution's raw text content into a pandas DataFrame, picking
    the parser from asset_title's extension (see detect_format). Raises
    (ValueError, pandas.errors.ParserError, etc.) if the content doesn't
    actually match its expected format."""
    import io
    import pandas as pd

    fmt = detect_format(asset_title)
    if fmt == "tsv":
        return pd.read_csv(io.StringIO(content), sep="\t")
    if fmt == "jsonl":
        return pd.read_json(io.StringIO(content), lines=True)
    if fmt == "json":
        return pd.read_json(io.StringIO(content))
    return pd.read_csv(io.StringIO(content))


def exp_class(exp_type: str):
    """Return the Great Expectations class for a given expectation type string."""
    class_name = "".join(word.capitalize() for word in exp_type.split("_"))
    return getattr(gx.expectations, class_name)


def parse_expectations(value) -> list[dict]:
    """Parse an expectations value that may be a list, JSON string, or Python literal."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        s = value.strip()
        if s in ("", "[]"):
            return []
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return ast.literal_eval(s)
    return []