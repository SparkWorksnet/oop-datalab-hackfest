"""
Helper functions for interacting with EDC connectors during the hackfest.
"""

import json
import time

import requests


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