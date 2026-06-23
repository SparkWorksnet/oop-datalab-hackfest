#!/bin/bash
# ============================================================================
# Register sample assets, policy, and contract definition on the central EDC
# Run after docker compose up -d
# Usage: ./setup-assets.sh [CENTRAL_HOST]
# ============================================================================

CENTRAL_HOST=${1:-localhost}
MGMT="http://${CENTRAL_HOST}:18181/management/v3"

echo "=== Setting up central EDC at ${CENTRAL_HOST} ==="

# ── 1. Create policy (no constraints — open access) ────────────────────────
echo ""
echo "--- Creating policy: open-policy ---"
curl -s -X POST "${MGMT}/policydefinitions" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": "open-policy",
    "policy": {
      "@context": "http://www.w3.org/ns/odrl.jsonld",
      "@type": "Set"
    }
  }' | jq .

# ── 2. Create contract definition (matches all assets) ─────────────────────
echo ""
echo "--- Creating contract definition: open-contract ---"
curl -s -X POST "${MGMT}/contractdefinitions" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": "open-contract",
    "accessPolicyId": "open-policy",
    "contractPolicyId": "open-policy",
    "assetsSelector": []
  }' | jq .

# ── 3. Register sample assets ──────────────────────────────────────────────
echo ""
echo "--- Registering sample assets ---"

# Sample dataset 1
curl -s -X POST "${MGMT}/assets" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": "hackfest-sample-001",
    "properties": {
      "name": "Sample 5G Measurement Dataset",
      "contenttype": "text/csv",
      "description": "Sample 5G NR measurement data for the hackfest"
    },
    "dataAddress": {
      "type": "MinioAsset",
      "endpoint": "http://rustfs:9000",
      "bucketName": "central-datasets",
      "accessKey": "central-admin",
      "secretKey": "central-secret-2024",
      "prefix": "sample-001.csv"
    }
  }' | jq .

# Sample dataset 2
curl -s -X POST "${MGMT}/assets" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": "hackfest-sample-002",
    "properties": {
      "name": "Sample Network KPI Dataset",
      "contenttype": "text/csv",
      "description": "Sample network KPI data for the hackfest"
    },
    "dataAddress": {
      "type": "MinioAsset",
      "endpoint": "http://rustfs:9000",
      "bucketName": "central-datasets",
      "accessKey": "central-admin",
      "secretKey": "central-secret-2024",
      "prefix": "sample-002.csv"
    }
  }' | jq .

echo ""
echo "=== Central EDC setup complete ==="
echo "  Catalog UI:  http://${CENTRAL_HOST}:18180/api/catalog"
echo "  DSP endpoint: http://${CENTRAL_HOST}:18182/protocol"
echo ""
echo "  Participants should use this DSP address as their counterPartyAddress."
