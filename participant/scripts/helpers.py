"""
Helper functions for interacting with EDC connectors during the hackfest.
"""

import hashlib
import json
import time

import requests


# JSON-LD @context used by the Dataset Submission Portal (Track 1). Shared by
# the registration scripts so a script-registered asset carries the same
# semantic_description shape as a portal-registered one — same prefixes, same
# DCAT-AP / GAIA-X / 6G-DALI MAP terms.
SEMANTIC_CONTEXT = {
    "dct":   "http://purl.org/dc/terms/",
    "dcat":  "http://www.w3.org/ns/dcat#",
    "dali":  "https://dali-project.eu/ns#",
    "schema": "https://schema.org/",
    "gax":   "https://w3id.org/gaia-x/development#",
    "prov":  "http://www.w3.org/ns/prov#",
    "foaf":  "http://xmlns.com/foaf/0.1/",
    "vcard": "http://www.w3.org/2006/vcard/ns#",
    "adms":  "http://www.w3.org/ns/adms#",
    "rdfs":  "http://www.w3.org/2000/01/rdf-schema#",
    "skos":  "http://www.w3.org/2004/02/skos/core#",
    "spdx":  "http://spdx.org/rdf/terms#",
}

# Default 6G-DALI MAP testbed-context / experimentation terms, shared by every
# asset registered from this testbed. Merged into the Dataset node so both the
# original and derived assets describe the same measurement setup.
DALI_TESTBED_CONTEXT = {
    "dali:environment": "indoors",
    "dali:networkDomain": "RAN",
    "dali:ran3gppRelease": "Release 17",
    "dali:ranNewRadioType": "NR-SA",
    "dali:ranSplit": "No-Split",
    "dali:ranFocusedTechnology": "O-RAN",
    "dali:ranCoverageType": "Single_Micro",
    "dali:ranFrequencyBand": "n78",
    "dali:ranBandwidthMHz": "100",
    "dali:ranMaxEndDevices": "10",
    "dali:ranMobilityModel": "static",
    "dali:coreRelease": "Release 17",
    "dali:coreSolution": "OpenSource",
    "dali:transportType": "fiber_optics",
    "dali:computeOrchestratorType": "Kubernetes",
    "dali:computeGpuUse": "false",
    "dali:computeVirtualizationType": "Docker",
    "dali:observationPointHorizontal": "End device to Access",
    "dali:observationPointVertical": "Radio Level",
    "dali:measurementFamily": "DRB",
    "dali:measurementTool": "Prometheus exporter",
}


def build_semantic_description(asset_id, name, csv_bytes, columns,
                               protocol_url, catalog_base, *,
                               description, keywords, issued, version="1.0",
                               license_url="https://creativecommons.org/licenses/by/4.0/",
                               extra_dataset=None):
    """Build the DCAT-AP / GAIA-X / 6G-DALI MAP JSON-LD document that the
    Dataset Submission Portal stores as an asset's single 'semantic_description'
    property, and return it serialized to a string (that's how EDC carries it —
    an opaque string property, not expanded JSON-LD). schema:variableMeasured
    lives on the distribution, which is where dali.datalake.fetch_columns_from_asset
    looks.

    Shared by tr02_s1_register.py (original asset) and
    tr02_s5_pull_process_push.py (derived asset). Callers pass the
    dataset-level description/keywords/issued/version, and may add further
    Dataset-node terms via `extra_dataset` (e.g. PROV-O provenance on a
    derived asset)."""
    org = {"@type": "foaf:Organization", "foaf:name": name, "foaf:homepage": name}
    checksum = hashlib.sha256(csv_bytes).hexdigest()
    doc = {
        "@context": SEMANTIC_CONTEXT,
        "@id": f"urn:dataset:{asset_id}",
        "@type": ["dcat:Dataset", "gax:DataResource"],
        # ── DCAT-AP core fields ─────────────────────────────────────────
        "dct:description": description,
        "dct:issued": issued,
        "dct:publisher": org,
        "dct:creator": org,
        "dct:license": license_url,
        "dct:accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC",
        "dcat:keyword": list(keywords),
        "dcat:theme": "http://publications.europa.eu/resource/authority/data-theme/TECH",
        "dct:language": "http://publications.europa.eu/resource/authority/language/ENG",
        "adms:version": version,
        "dct:conformsTo": "https://www.go-fair.org/fair-principles/",
        "dcat:landingPage": f"{catalog_base}/api/catalog",
        # ── 6G-DALI MAP: project identity ───────────────────────────────
        "dali:snsProjectName": "6G-DALI",
        "dali:gdprCompliant": "true",
        "dali:fairCompliant": "true",
        # ── 6G-DALI MAP: testbed context + experimentation ──────────────
        **DALI_TESTBED_CONTEXT,
        # ── GAIA-X trust fields ─────────────────────────────────────────
        "gax:containsPII": False,
        "gax:producedBy": org,
        "gax:exposedThrough": protocol_url,
        "gax:policy": "urn:policy:open-policy",
        "dcat:contactPoint": {
            "@type": "vcard:Individual",
            "vcard:fn": name,
            "vcard:hasEmail": f"mailto:{name}",
        },
        "spdx:checksum": checksum,
        # ── Distribution: where schema:variableMeasured lives ───────────
        "dcat:distribution": {
            "@type": "dcat:Distribution",
            "dct:title": f"{name} (distribution)",
            "dct:identifier": asset_id,
            "dali:assetId": asset_id,
            "dali:connectorType": "dspaceconnector",
            "dct:format": "http://publications.europa.eu/resource/authority/file-type/CSV",
            "dcat:mediaType": "text/csv",
            "dct:license": license_url,
            "dcat:accessURL": protocol_url,
            "dcat:downloadURL": f"{catalog_base}/api/catalog/api/download?assetId={asset_id}",
            "dcat:byteSize": len(csv_bytes),
            "spdx:checksum": checksum,
            "schema:variableMeasured": ", ".join(columns),
        },
    }
    if extra_dataset:
        doc.update(extra_dataset)
    return json.dumps(doc)


class EdcClient:
    """Minimal EDC management API client."""

    def __init__(self, management_url, protocol_url=None):
        self.mgmt = management_url.rstrip("/")
        self.protocol = protocol_url.rstrip("/") if protocol_url else None
        self.headers = {"Content-Type": "application/json"}

    # ── Assets ──────────────────────────────────────────────────────────────

    def delete_asset(self, asset_id):
        from urllib.parse import quote
        resp = requests.delete(f"{self.mgmt}/management/v3/assets/{quote(asset_id, safe='')}", headers=self.headers)
        print(f"  Delete asset '{asset_id}': {resp.status_code}")

    def create_asset(self, asset_id, name, content_type, data_address, metadata=None):
        properties = {
            "name": name,
            "contenttype": content_type,
        }
        if metadata:
            properties.update(metadata)
        resp = requests.post(
            f"{self.mgmt}/management/v3/assets",
            headers=self.headers,
            json={
                "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
                "@id": asset_id,
                "properties": properties,
                "dataAddress": data_address,
            },
        )
        if resp.status_code == 409:
            print(f"  Asset '{asset_id}' already exists, skipping registration")
            return {"@id": asset_id, "status": "already_exists"}
        if not resp.ok:
            print(f"  [ERROR] {resp.status_code}: {resp.text}")
            resp.raise_for_status()
        return resp.json() if resp.text else {"@id": asset_id, "status": resp.status_code}

    def list_assets(self):
        return requests.post(
            f"{self.mgmt}/management/v3/assets/request",
            headers=self.headers,
            json={},
        ).json()

    # ── Policy + Contract ───────────────────────────────────────────────────

    def create_open_policy(self, policy_id="open-policy"):
        resp = requests.post(
            f"{self.mgmt}/management/v3/policydefinitions",
            headers=self.headers,
            json={
                "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
                "@id": policy_id,
                "policy": {
                    "@context": "http://www.w3.org/ns/odrl.jsonld",
                    "@type": "Set",
                },
            },
        )
        if resp.status_code == 409:
            print(f"  Policy '{policy_id}' already exists, skipping")
            return {"@id": policy_id, "status": "already_exists"}
        return resp.json() if resp.text else {"@id": policy_id}

    def create_contract_definition(self, contract_id="open-contract", policy_id="open-policy"):
        resp = requests.post(
            f"{self.mgmt}/management/v3/contractdefinitions",
            headers=self.headers,
            json={
                "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
                "@id": contract_id,
                "accessPolicyId": policy_id,
                "contractPolicyId": policy_id,
                "assetsSelector": [],
            },
        )
        if resp.status_code == 409:
            print(f"  Contract definition '{contract_id}' already exists, skipping")
            return {"@id": contract_id, "status": "already_exists"}
        return resp.json() if resp.text else {"@id": contract_id}

    # ── Catalogue ───────────────────────────────────────────────────────────

    def request_catalogue(self, provider_protocol_url):
        resp = requests.post(
            f"{self.mgmt}/management/v3/catalog/request",
            headers=self.headers,
            json={
                "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
                "counterPartyAddress": provider_protocol_url,
                "protocol": "dataspace-protocol-http",
            },
        )
        resp.raise_for_status()
        return resp.json()

    def request_asset(self, asset_id, provider_protocol_url):
        resp = requests.post(
            f"{self.mgmt}/management/v3/catalog/request",
            headers=self.headers,
            json={
                "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
                "counterPartyAddress": provider_protocol_url,
                "protocol": "dataspace-protocol-http",
                "querySpec": {
                    "filterExpression": [{
                        "operandLeft": "https://w3id.org/edc/v0.0.1/ns/id",
                        "operator": "=",
                        "operandRight": asset_id,
                    }]
                },
            },
        )
        resp.raise_for_status()
        catalog = resp.json()
        datasets = catalog.get("dcat:dataset", [])
        if isinstance(datasets, dict):
            datasets = [datasets]
        if not datasets:
            raise RuntimeError(f"Asset '{asset_id}' not found in provider catalogue")
        return datasets[0]

    # ── Negotiation ─────────────────────────────────────────────────────────

    def negotiate_contract(self, offer_id, asset_id, provider_protocol_url, provider_id):
        resp = requests.post(
            f"{self.mgmt}/management/v3/contractnegotiations",
            headers=self.headers,
            json={
                "@context": {
                    "@vocab": "https://w3id.org/edc/v0.0.1/ns/",
                    "odrl": "http://www.w3.org/ns/odrl/2/",
                },
                "@type": "ContractRequest",
                "counterPartyAddress": provider_protocol_url,
                "providerId": provider_id,
                "protocol": "dataspace-protocol-http",
                "policy": {
                    "@id": offer_id,
                    "@type": "http://www.w3.org/ns/odrl/2/Offer",
                    "odrl:permission": [],
                    "odrl:prohibition": [],
                    "odrl:obligation": [],
                    "odrl:target": {"@id": asset_id},
                    "odrl:assigner": {"@id": provider_id},
                },
            },
        )
        resp.raise_for_status()
        return resp.json()

    def wait_for_negotiation(self, negotiation_id, timeout=60, interval=2):
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = requests.get(f"{self.mgmt}/management/v3/contractnegotiations/{negotiation_id}")
            resp.raise_for_status()
            state = resp.json()
            status = state.get("state", state.get("edc:state", ""))
            print(f"  Negotiation state: {status}")
            if status == "FINALIZED":
                return state.get("contractAgreementId") or state.get("edc:contractAgreementId")
            if status in ("TERMINATED", "ERROR"):
                raise RuntimeError(f"Negotiation failed: {status}")
            time.sleep(interval)
        raise TimeoutError("Negotiation did not complete in time")

    # ── Transfer ────────────────────────────────────────────────────────────

    def start_transfer(self, agreement_id, asset_id, provider_protocol_url, provider_id, destination_url):
        resp = requests.post(
            f"{self.mgmt}/management/v3/transferprocesses",
            headers=self.headers,
            json={
                "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
                "@type": "TransferRequest",
                "counterPartyAddress": provider_protocol_url,
                "connectorId": provider_id,
                "protocol": "dataspace-protocol-http",
                "contractId": agreement_id,
                "assetId": asset_id,
                "transferType": "PresignedHttpData-PUSH",
                "dataDestination": {
                    "type": "PresignedHttpData",
                    "baseUrl": destination_url,
                    "method": "PUT",
                },
            },
        )
        resp.raise_for_status()
        return resp.json()

    def wait_for_transfer(self, transfer_id, timeout=120, interval=3):
        deadline = time.time() + timeout
        while time.time() < deadline:
            resp = requests.get(f"{self.mgmt}/management/v3/transferprocesses/{transfer_id}")
            resp.raise_for_status()
            state = resp.json()
            status = state.get("state", state.get("edc:state", ""))
            print(f"  Transfer state: {status}")
            if status == "COMPLETED":
                return True
            if status in ("TERMINATED", "ERROR"):
                raise RuntimeError(f"Transfer failed: {status}")
            time.sleep(interval)
        raise TimeoutError("Transfer did not complete in time")