#!/bin/bash
# ============================================================================
# Register sample assets, policy, and contract definition on the central EDC
# Run after docker compose up -d
# Usage: ./setup-assets.sh [CENTRAL_HOST]
# ============================================================================

CENTRAL_HOST=${1:-localhost}
MGMT="http://${CENTRAL_HOST}:20001/management/v3"

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
  }' ; echo

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
  }' ; echo

# ── 3. Register sample assets ──────────────────────────────────────────────
echo ""
echo "--- Registering sample assets ---"

# Sample dataset 1 — 5G NR RAN measurements
curl -s -X POST "${MGMT}/assets" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": "hackfest-sample-001",
    "properties": {
      "name": "5G NR RAN Measurement Dataset",
      "contenttype": "text/csv",
      "dct.description": "Per-cell 5G NR downlink and uplink throughput, latency, RSRP, SINR and connected UE count measurements from a lab testbed.",
      "dct.issued": "2024-06-01",
      "dct.publisher": "OpenOP Hackfest",
      "dct.license": "https://creativecommons.org/licenses/by/4.0/",
      "dct.accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC",
      "dcat.keyword": "5G NR, RAN, throughput, latency, RSRP, SINR, measurement",
      "adms.version": "1.0",
      "dali.snsProjectName": "6G-DALI",
      "dali.gdprCompliant": "true",
      "dali.fairCompliant": "true",
      "dali.environment": "indoors",
      "dali.networkDomain": "RAN",
      "dali.ran3gppRelease": "Release 17",
      "dali.ranNewRadioType": "NR-SA",
      "dali.ranCoverageType": "Single_Micro",
      "dali.ranFrequencyBand": "n78",
      "dali.ranBandwidthMHz": "100",
      "dali.ranMobilityModel": "static",
      "dali.observationPointHorizontal": "End device to Access",
      "dali.observationPointVertical": "Radio Level",
      "dali.measurementFamily": "DRB",
      "dali.measurementTool": "Prometheus exporter",
      "schema.variableMeasured": "throughput_dl_mbps, throughput_ul_mbps, latency_ms, rsrp_dbm, sinr_db, connected_ues"
    },
    "dataAddress": {
      "type": "MinioAsset",
      "endpoint": "http://rustfs:9000",
      "bucketName": "central-datasets",
      "accessKey": "central-admin",
      "secretKey": "central-secret-2024",
      "prefix": "sample-001.csv"
    }
  }' ; echo

# Sample dataset 2 — Network slice KPI measurements
curl -s -X POST "${MGMT}/assets" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": "hackfest-sample-002",
    "properties": {
      "name": "Network Slice KPI Dataset",
      "contenttype": "text/csv",
      "dct.description": "End-to-end KPI measurements across URLLC and eMBB network slices including latency, packet loss, availability and jitter.",
      "dct.issued": "2024-06-01",
      "dct.publisher": "OpenOP Hackfest",
      "dct.license": "https://creativecommons.org/licenses/by/4.0/",
      "dct.accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC",
      "dcat.keyword": "5G, network slicing, URLLC, eMBB, KPI, latency, packet loss, availability",
      "adms.version": "1.0",
      "dali.snsProjectName": "6G-DALI",
      "dali.gdprCompliant": "true",
      "dali.fairCompliant": "true",
      "dali.environment": "indoors",
      "dali.networkDomain": "E2E",
      "dali.ran3gppRelease": "Release 17",
      "dali.ranNewRadioType": "NR-SA",
      "dali.sliceType": "Multi-slice",
      "dali.observationPointHorizontal": "E2E Application layer",
      "dali.observationPointVertical": "Network Layer",
      "dali.measurementFamily": "RRC",
      "dali.measurementTool": "Custom KPI collector",
      "schema.variableMeasured": "e2e_latency, packet_loss_rate, availability, jitter"
    },
    "dataAddress": {
      "type": "MinioAsset",
      "endpoint": "http://rustfs:9000",
      "bucketName": "central-datasets",
      "accessKey": "central-admin",
      "secretKey": "central-secret-2024",
      "prefix": "sample-002.csv"
    }
  }' ; echo

echo ""
echo "=== Central EDC setup complete ==="
echo "  Catalog UI:  http://${CENTRAL_HOST}:20000/api/catalog"
echo "  DSP endpoint: http://${CENTRAL_HOST}:20002/protocol"
echo ""
echo "  Participants should use this DSP address as their counterPartyAddress."
