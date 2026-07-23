# Task 5 — Build Your Own Extensions

Go beyond the guided tasks and contribute new functionality to the Data Lab.

## Starting Point

By now you have completed Tasks 1-4 and have a working Data Lab environment with:

- Your own EDC connector with registered assets
- A local RustFS with raw and augmented datasets
- Contract negotiation and transfer working locally and across connectors
- The Catalog UI showing assets, metadata, provenance lineage

Use this as a foundation to build something new.

## Ideas

### Bring Your Own Dataset

Use `tr02_s1_register.py` as a starting point. Edit the script to:

- Point `CSV_PATH` at your own data file (or upload via the RustFS UI at `http://<MY_HOST>:21005` / `s3.upload_file()`)
- Customise the MAP metadata via `build_semantic_description` — its `name`, `description`, `keywords` arguments, and testbed terms like `dali:environment`, `dali:networkDomain`, `dali:ranNewRadioType` (add extra ones through its `extra_dataset` parameter) — to describe your testbed and measurement setup

Then ask other participants to discover and pull your dataset (Task 3 — pull from a peer).

### Custom DataOps Pipeline

Use `tr02_s5_pull_process_push.py` (or its Airflow equivalent, Task 4's `hackfest_enrich_dataset`) as a starting point. Replace the augmentation logic with your own processing:

- **Data quality checks** — Task 4's `hackfest_validate_dataset` DAG already does this with Great Expectations (validate columns, check row counts, auto-generate checks from `schema.variableMeasured`) and writes the report as JSON next to the source file. Extend it with your own expectation types, or register the report as its own derived asset (it currently isn't — see `dali.datalake.upload_results` and `register_derived_asset` in `airflow/plugins/dali/`) so it shows up as its own row in the Catalog UI.
- **Feature engineering** — compute rolling averages, percentiles, or statistical summaries. Register the feature set for ML consumption.
- **Aggregation** — group by `cpu_limit`/`ram_limit`, concurrency (`c`), or a time window. Register the aggregated dataset as a new asset.
- **Join datasets** — pull from two sources (your own + central or peer), merge them, and register the combined result with `prov.wasDerivedFrom` listing both sources.

### Multi-Source Composition

```python
# Pull from central
dataset_a = edc.request_asset("cfdedca2-998e-46f9-b860-1bbf2aeb6a2f", CENTRAL_PROTOCOL)  # central RabbitMQ sample
# ... negotiate + transfer ...

# Pull from a peer
dataset_b = edc.request_asset("their-measurement", f"http://{PEER_IP}:21002/protocol")
# ... negotiate + transfer ...

# Read both, join, and register the result
merged = merge(a_content, b_content)
edc.create_asset("merged-dataset", ..., metadata={
    "prov.wasDerivedFrom": "cfdedca2-998e-46f9-b860-1bbf2aeb6a2f, their-measurement",
    "prov.wasGeneratedBy": "multi-source-merge-pipeline",
})
```

Check the Lineage tab — the merged asset will show multiple parent connections.

### AI-Assisted Features

- **Auto-metadata** — read the CSV headers and generate `schema.variableMeasured` automatically
- **Auto-categorisation** — classify the dataset's `dali.networkDomain` based on column names
- **Anomaly detection** — flag outlier rows and register a cleaned version as a derived asset
- **Data summarisation** — generate a natural-language description for `dct.description` from the data statistics

### Custom Policies

The current setup uses an open-access policy. Experiment with restricted access:

```python
# Policy that requires a specific participant ID
edc.create_policy("restricted-policy", {
    "@context": "http://www.w3.org/ns/odrl.jsonld",
    "@type": "Set",
    "permission": [{
        "action": "use",
        "constraint": [{
            "leftOperand": "participantId",
            "operator": "eq",
            "rightOperand": "team-alpha"
        }]
    }]
})
```

Then create a contract definition that uses this policy instead of the open one.

## MAP Field Reference

There are two registration styles in this hackfest, sharing the same MAP field names:

- **Structured `semantic_description` JSON-LD** — one document per asset with colon-prefixed terms (`dct:description`, `dali:snsProjectName`, `schema:variableMeasured`, `prov:wasDerivedFrom`) and nested `foaf:Organization`/vcard/`dali:testbedContext`/`dct:ProvenanceStatement` nodes. This is what the Catalog UI's Submit Dataset portal (Task 1), the Track 2/3 scripts (`tr02_s1_register.py`, `tr02_s5_pull_process_push.py`), **and** the Airflow `hackfest_enrich_dataset` DAG use — via `build_semantic_description` (in `scripts/helpers.py`, mirrored in `airflow/plugins/dali/semantic.py`). The connector's Catalog UI reads lineage (`prov:wasDerivedFrom`) out of this document. If you extend these, add your terms to that document rather than inventing flat keys.
- **Flat, dotted-prefix EDC properties** — one property per field (`dct.description`, `prov.wasDerivedFrom`, …). This is what the central `setup-assets.sh` uses; the Catalog UI still honours flat `prov.wasDerivedFrom` as a fallback, so you can register your own assets this way too.

The fields are the same either way — only the separator differs (`:` for JSON-LD vs `.` for flat EDC properties). When registering via the flat-property style, use these prefixes:

| Prefix | Fields | Description |
|--------|--------|-------------|
| `dct.` | description, issued, publisher, license, accessRights, language | DCAT-AP core |
| `dcat.` | keyword | DCAT-AP tags |
| `adms.` | version | Version label |
| `dali.` | snsProjectName, gdprCompliant, fairCompliant, environment, networkDomain, ran*, core*, transport*, compute*, observationPoint*, measurementFamily, measurementTool | 6G-DALI MAP |
| `schema.` | variableMeasured | Measured variables |
| `prov.` | wasDerivedFrom, wasGeneratedBy, wasAttributedTo | Provenance |

## Contributing Back

Contributions developed during the Hackfest may become candidates for future integration into OpenOP. If you build something interesting, share your script with the organisers.
