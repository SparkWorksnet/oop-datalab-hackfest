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

- Replace the sample CSV with your own data file (upload via RustFS UI at `http://<MY_HOST>:21005` or `s3.upload_file()`)
- Customise the MAP metadata to describe your testbed, environment, and measurement setup
- Use different `dali.environment`, `dali.networkDomain`, `dali.ranNewRadioType` values to match your data

Then ask other participants to discover and pull your dataset (Task 4).

### Custom DataOps Pipeline

Use `task_local_02-pull-process-push.py` (or its Airflow equivalent, Task 7's `hackfest_process_dataset`) as a starting point. Replace the augmentation logic with your own processing:

- **Data quality checks** — Task 7's `hackfest_validate_dataset` DAG already does this with Great Expectations (validate columns, check row counts, auto-generate checks from `schema.variableMeasured`) and writes the report as JSON next to the source file. Extend it with your own expectation types, or register the report as its own derived asset (it currently isn't — see `dali.datalake.upload_results` and `register_derived_asset` in `airflow/plugins/dali/`) so it shows up as its own row in the Catalog UI.
- **Feature engineering** — compute rolling averages, percentiles, or statistical summaries. Register the feature set for ML consumption.
- **Aggregation** — group by cell ID, time window, or slice type. Register the aggregated dataset as a new asset.
- **Join datasets** — pull from two sources (your own + central or peer), merge them, and register the combined result with `prov.wasDerivedFrom` listing both sources.

### Multi-Source Composition

```python
# Pull from central
dataset_a = edc.request_asset("hackfest-sample-001", CENTRAL_PROTOCOL)
# ... negotiate + transfer ...

# Pull from a peer
dataset_b = edc.request_asset("their-measurement", f"http://{PEER_IP}:21002/protocol")
# ... negotiate + transfer ...

# Read both, join, and register the result
merged = merge(a_content, b_content)
edc.create_asset("merged-dataset", ..., metadata={
    "prov.wasDerivedFrom": "hackfest-sample-001, their-measurement",
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

The flat, dotted-prefix fields below are what the Track 2 scripts (`tr02_s1_register.py`, `task_local_02-pull-process-push.py`, and `dali.datalake.register_derived_asset` in the Airflow plugins) still register directly as EDC asset properties — use these prefixes when registering your own assets that way.

The Catalog UI's Submit Dataset portal (Task 3) instead bundles all of this into one structured `semantic_description` JSON-LD document per asset (see Task 3) — if you're extending that portal rather than a script, follow its existing structure (nested `foaf:Organization`/vcard/`dali:testbedContext`/`dct:ProvenanceStatement` nodes) instead of adding new flat dotted keys.

When registering your own assets via script, use these field prefixes:

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
