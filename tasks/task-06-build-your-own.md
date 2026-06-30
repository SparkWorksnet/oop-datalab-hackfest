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

Use `task_local_02-pull-process-push.py` as a starting point. Replace the augmentation logic with your own processing:

- **Data quality checks** — validate columns, detect outliers, compute completeness scores. Register a quality report JSON as a derived asset.
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

When registering your own assets, use these field prefixes:

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
