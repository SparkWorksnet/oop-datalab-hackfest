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

# Source dataset (all three distributions):
#   "Benchmarking on Microservices Configurations and the Impact on the
#    Performance in Cloud Native Environments" — EURECOM 5G testbed.
#   Nassima Toumi et al., CC BY 4.0, DOI 10.5281/zenodo.6907619
#   https://catalogue.dspace.sparkworks.net/datasets/53ba2f86-7f06-4324-b168-4cba63ea1272

# Sample dataset 1 — RabbitMQ (file-1.csv), asset id cfdedca2-998e-46f9-b860-1bbf2aeb6a2f
curl -s -X POST "${MGMT}/assets" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": "cfdedca2-998e-46f9-b860-1bbf2aeb6a2f",
    "properties": {
      "name": "RabbitMQ Performance Measurements",
      "contenttype": "text/csv",
      "dct.description": "CPU and memory consumption measurements for the RabbitMQ (distributed message broker) microservice under varying workloads and configurations, generated on the EURECOM 5G testbed to benchmark cloud-native microservice performance.",
      "dct.issued": "2022-07-19",
      "dct.creator": "Nassima Toumi",
      "dct.publisher": "EURECOM",
      "dct.license": "https://creativecommons.org/licenses/by/4.0/",
      "dct.accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC",
      "dct.source": "https://doi.org/10.5281/zenodo.6907619",
      "adms.identifier": "10.5281/zenodo.6907619",
      "dcat.keyword": "Kafka, NGINX, microservices, CPU consumption, cloud-native, AMF, containerisation, network function virtualisation, performance, workload, InfluxDB, NFV, memory consumption, 5G core, benchmarking",
      "adms.version": "1.0",
      "dali.snsProjectName": "6G-DALI",
      "dali.gdprCompliant": "true",
      "dali.fairCompliant": "true",
      "dali.environment": "cloud",
      "dali.measurementTool": "EURECOM 5G testbed",
      "schema.variableMeasured": "time, ram_limit, cpu_limit, ram_usage, cpu_usage, n, min, lat50, lat75, lat95, lat99"
    },
    "dataAddress": {
      "type": "MinioAsset",
      "endpoint": "http://rustfs:9000",
      "bucketName": "central-datasets",
      "accessKey": "central-admin",
      "secretKey": "central-secret-2024",
      "prefix": "file-1.csv"
    }
  }' ; echo

# Sample dataset 2 — AMF (file-2.csv), asset id 1aea6aae-19ae-404e-949c-45d9949f3113
curl -s -X POST "${MGMT}/assets" \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": "1aea6aae-19ae-404e-949c-45d9949f3113",
    "properties": {
      "name": "AMF Performance Measurements",
      "contenttype": "text/csv",
      "dct.description": "CPU and memory consumption measurements for the AMF (5G Access and Mobility Function) microservice under varying workloads and configurations, generated on the EURECOM 5G testbed to benchmark cloud-native microservice performance.",
      "dct.issued": "2022-07-19",
      "dct.creator": "Nassima Toumi",
      "dct.publisher": "EURECOM",
      "dct.license": "https://creativecommons.org/licenses/by/4.0/",
      "dct.accessRights": "http://publications.europa.eu/resource/authority/access-right/PUBLIC",
      "dct.source": "https://doi.org/10.5281/zenodo.6907619",
      "adms.identifier": "10.5281/zenodo.6907619",
      "dcat.keyword": "Kafka, NGINX, microservices, CPU consumption, cloud-native, AMF, containerisation, network function virtualisation, performance, workload, InfluxDB, NFV, memory consumption, 5G core, benchmarking",
      "adms.version": "1.0",
      "dali.snsProjectName": "6G-DALI",
      "dali.gdprCompliant": "true",
      "dali.fairCompliant": "true",
      "dali.environment": "cloud",
      "dali.measurementTool": "EURECOM 5G testbed",
      "schema.variableMeasured": "time, ram_limit, cpu_limit, ram_usage, cpu_usage, n, mean, lat50, lat75, lat80, lat90, lat95, lat98, lat99, lat100"
    },
    "dataAddress": {
      "type": "MinioAsset",
      "endpoint": "http://rustfs:9000",
      "bucketName": "central-datasets",
      "accessKey": "central-admin",
      "secretKey": "central-secret-2024",
      "prefix": "file-2.csv"
    }
  }' ; echo

# Note: the Python web server distribution (file-3.csv) is intentionally not
# registered here — it is provided to participants to upload themselves via the
# Dataset Submission Portal (Task 3), from participant/scripts/seed-data/file-3.csv.

echo ""
echo "=== Central EDC setup complete ==="
echo "  Catalog UI:  http://${CENTRAL_HOST}:20000/api/catalog"
echo "  DSP endpoint: http://${CENTRAL_HOST}:20002/protocol"
echo ""
echo "  Participants should use this DSP address as their counterPartyAddress."
