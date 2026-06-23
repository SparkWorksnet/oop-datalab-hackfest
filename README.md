# OpenOP DataOps & Data Space Hackfest

Hands-on workshop showcasing how the 6G-DALI Data Space modules work together for the OpenOP (Operator Platform). Participants learn how to register datasets in an Eclipse Dataspace Connector (EDC), discover and transfer data between connectors, and process it using DataOps pipelines.

## Architecture

```
                         Hackfest Venue
  ┌──────────────────────────────────────────────────────┐
  │                                                      │
  │   Central EDC (hosted once)                          │
  │   ┌──────────────┐  ┌─────────┐  ┌──────────────┐   │
  │   │  EDC          │  │ MinIO   │  │ PostgreSQL   │   │
  │   │  :18180 UI    │  │ :9000   │  │              │   │
  │   │  :18181 Mgmt  │  │ :9001   │  │              │   │
  │   │  :18182 DSP   │  │         │  │              │   │
  │   └──────┬────────┘  └─────────┘  └──────────────┘   │
  │          │ DSP protocol                              │
  │          │                                           │
  │   ┌──────┴──────────────────────────────────┐        │
  │   │         LAN / Wi-Fi                     │        │
  │   └──────┬──────────┬───────────┬───────────┘        │
  │          │          │           │                     │
  │   Participant A  Participant B  Participant C  ...   │
  │   ┌────────────┐ ┌────────────┐ ┌────────────┐      │
  │   │ EDC :28180 │ │ EDC :28180 │ │ EDC :28180 │      │
  │   │ MinIO:9000 │ │ MinIO:9000 │ │ MinIO:9000 │      │
  │   │ PG         │ │ PG         │ │ PG         │      │
  │   └────────────┘ └────────────┘ └────────────┘      │
  └──────────────────────────────────────────────────────┘
```

## Prerequisites

Each participant needs:

- Docker and Docker Compose
- Python 3.9+ with pip
- A terminal / command line
- Network access to the central EDC host

## Quick Start

### Central EDC (organiser — run once)

```bash
cd central-edc

# Place sample CSV files in seed-data/ before starting
docker compose up -d

# Wait for services to be ready, then register assets
chmod +x setup-assets.sh
./setup-assets.sh <CENTRAL_HOST_IP>
```

Verify at `http://<CENTRAL_HOST_IP>:18180/api/catalog` — you should see the sample assets.

### Participant setup

```bash
cd participant

# Set your team name and the central EDC IP
export PARTICIPANT_NAME=team-alpha
export CENTRAL_EDC_HOST=192.168.1.100

# Start your local stack
docker compose up -d

# Install Python dependencies
pip install -r scripts/requirements.txt
```

Verify your connector at `http://localhost:28180/api/catalog`.

## Exercises

### Exercise 1 — Local data registration and transfer

Register a dataset on your own connector, negotiate a contract with yourself, and transfer the data between MinIO buckets via the EDC.

```bash
cd scripts
python exercise1_local.py
```

What happens step by step:

1. A sample CSV is uploaded to your local MinIO (`my-datasets` bucket)
2. The file is registered as an EDC asset with type `MinioAsset`
3. An open policy and contract definition are created
4. Your connector's catalogue is queried — the asset should appear
5. A contract is negotiated (your connector acts as both provider and consumer)
6. A presigned PUT URL is generated for the `received` bucket
7. The EDC transfers the file from `my-datasets` to `received` via the presigned URL
8. The received file is verified

After completion, check:
- Catalog UI at `http://localhost:28180/api/catalog` — asset visible under Assets tab
- MinIO UI at `http://localhost:9001` — file in both buckets
- Negotiations and Transfers tabs show the completed operations

### Exercise 2 — Pull a dataset from the central EDC

Discover datasets in the central EDC catalogue, negotiate access, and transfer a dataset to your local MinIO.

```bash
python exercise2_central.py <CENTRAL_HOST_IP>
```

What happens step by step:

1. Your connector queries the central EDC catalogue via the DSP protocol
2. Available datasets are listed
3. A contract is negotiated with the central connector
4. A presigned PUT URL is generated on your local MinIO (`received` bucket)
5. The central EDC reads the file from its MinIO and PUTs it to your presigned URL
6. The file lands in your local `received/from-central/` prefix

After completion, check:
- Your Catalog UI — Negotiations tab shows the cross-connector negotiation
- Your MinIO UI — the file is in `received/from-central/`

## Services and Ports

### Central EDC

| Service    | Port  | Purpose                     |
|------------|-------|-----------------------------|
| EDC UI     | 18180 | Catalog UI at `/api/catalog`|
| EDC Mgmt   | 18181 | Management API              |
| EDC DSP    | 18182 | Dataspace Protocol endpoint |
| EDC Control| 18183 | Internal control plane      |
| MinIO API  | 9000  | S3-compatible storage       |
| MinIO UI   | 9001  | Storage web console         |

### Participant

| Service    | Port  | Purpose                     |
|------------|-------|-----------------------------|
| EDC UI     | 28180 | Catalog UI at `/api/catalog`|
| EDC Mgmt   | 28181 | Management API              |
| EDC DSP    | 28182 | Dataspace Protocol endpoint |
| EDC Control| 28183 | Internal control plane      |
| MinIO API  | 9000  | S3-compatible storage       |
| MinIO UI   | 9001  | Storage web console         |

## Key Concepts

### EDC Transfer Types

| Type | Data Address | Use case |
|------|-------------|----------|
| `MinioAsset` | Source: reads from MinIO | Provider-side dataset storage |
| `PresignedHttpData` | Destination: HTTP PUT to presigned URL | Consumer-side S3/MinIO ingestion |

### Transfer Flow

```
Consumer                           Provider
   │                                  │
   │  POST /catalog/request           │
   │ ────────────────────────────────►│  Discover datasets
   │  ◄──── dcat:Catalog ────────────│
   │                                  │
   │  POST /contractnegotiations      │
   │ ────────────────────────────────►│  Negotiate access
   │  ◄──── agreement ID ───────────│
   │                                  │
   │  generate presigned PUT URL      │
   │  (on consumer's MinIO)           │
   │                                  │
   │  POST /transferprocesses         │
   │ ────────────────────────────────►│  Start transfer
   │                                  │
   │         Provider reads from      │
   │         its MinIO and PUTs       │
   │         to the presigned URL     │
   │                                  │
   │  ◄──── file arrives in MinIO ───│
   │                                  │
```

### Management API Cheat Sheet

```bash
# List assets
curl -X POST http://localhost:28181/management/v3/assets/request \
  -H "Content-Type: application/json" -d '{}'

# Browse a remote catalogue
curl -X POST http://localhost:28181/management/v3/catalog/request \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "counterPartyAddress": "http://<PROVIDER>:18182/protocol",
    "protocol": "dataspace-protocol-http"
  }'

# Check negotiation status
curl http://localhost:28181/management/v3/contractnegotiations/<ID>

# Check transfer status
curl http://localhost:28181/management/v3/transferprocesses/<ID>
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `No dataplane found` | The EDC data plane didn't register at startup. Restart the connector. |
| `411 Length Required` | The transfer destination must use `PresignedHttpData` type, not `HttpData`. |
| `Asset not found in provider catalogue` | The provider has no contract definition. Run `setup-assets.sh` on the central EDC. |
| Negotiation stuck in `REQUESTED` | Check that both connectors can reach each other's DSP endpoint (port 18182/28182). |
| Presigned URL expired | URLs expire after 5 minutes. Re-run the exercise script. |
| `UnknownHostException: minio` | The EDC container can't resolve `minio`. Ensure the MinIO container is running and on the same Docker network. |

## Docker Image

The EDC connector image used in this hackfest:

```
ghcr.io/sparkworksnet/6gdali-testbed-connector:latest
```

It includes the following custom extensions:
- **MinioAssetDataSource** — one-shot read from MinIO buckets (no polling)
- **PresignedHttpData Sink** — HTTP PUT with explicit Content-Length for S3/MinIO presigned URLs
- **Catalog UI** — web dashboard at `/api/catalog` showing assets, contracts, policies, agreements, negotiations, and transfers
- **Data plane self-registration** — automatic registration with `MinioAsset` source and `PresignedHttpData-PUSH` transfer type
