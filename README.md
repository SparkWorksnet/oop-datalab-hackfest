# OpenOP Hackfest #3 — Data Lab: Dataspace and DataOps Services

This Hackfest is an intensive, hands-on technical workshop focused on the **Data Lab Module Development Group (MDG)** of OpenOP, based on contributions by **6G-DALI**, the Flagship SNS-JU Project on 6G AI & Data.

Participants will explore how OpenOP is evolving beyond service exposure and orchestration towards a platform for **data- and AI-driven service ecosystems**, enabling trusted sharing and consumption of datasets, analytics services, and AI models across federated operator environments.

---

## The 6G-DALI Data Lab

The **6G-DALI Data Lab** is a set of data infrastructure components designed for 6G research and experimentation within OpenOP. It provides a complete data lifecycle — from raw measurement ingestion through processing to discovery and sharing — built on open standards and sovereign data exchange.

### Why a Data Space for 6G?

6G research generates large volumes of measurement data across distributed testbeds: RAN measurements, network KPIs, spectrum analytics, ML training datasets. Today this data lives in silos — each testbed has its own storage, its own format, its own access model. Sharing data between research teams, across testbeds, or with external partners requires manual coordination and ad-hoc file transfers.

A **data space** solves this by providing:

- **Sovereign data sharing** — data owners keep control over who can access their data and under what conditions, enforced through contract negotiation rather than open file shares
- **Standardised metadata** — every dataset is described using DCAT-AP and the 6G-DALI Metadata Application Profile (MAP), making datasets discoverable and comparable across testbeds
- **Interoperable storage** — S3-compatible object stores (RustFS, MinIO, SeaweedFS) mean any testbed can host data without vendor lock-in
- **Automated processing** — DataOps pipelines can discover, pull, transform, and re-publish datasets without manual intervention

### Components

```
  ┌──────────────────────────────────────────────────────────────────────┐
  │                        6G-DALI Data Lab                             │
  │                                                                     │
  │  ┌─────────────────┐    ┌─────────────────┐    ┌────────────────┐  │
  │  │  EDC Connector   │    │  S3 Storage     │    │  DataOps       │  │
  │  │                  │    │  (RustFS)       │    │  (Airflow)     │  │
  │  │  - Catalogue     │    │                 │    │                │  │
  │  │  - Negotiation   │◄──►│  - Raw data     │◄──►│  - Ingest      │  │
  │  │  - Transfer      │    │  - Processed    │    │  - Validate    │  │
  │  │  - Policies      │    │  - Derived      │    │  - Augment     │  │
  │  │  - Catalog UI    │    │                 │    │  - Publish     │  │
  │  └────────┬─────────┘    └─────────────────┘    └────────────────┘  │
  │           │                                                         │
  │           │ Dataspace Protocol (DSP)                                │
  │           │                                                         │
  └───────────┼─────────────────────────────────────────────────────────┘
              │
              ▼
    Other connectors, testbeds, partners
```

**Eclipse Dataspace Connector (EDC)** — the core component. Each participant runs their own connector which acts as both a catalogue (listing their datasets) and a transfer agent (negotiating access and moving data). Connectors communicate via the Dataspace Protocol (DSP), an open standard for data space interoperability.

**S3-compatible storage (RustFS)** — datasets are stored as objects in S3 buckets. The EDC reads from and writes to storage using presigned URLs, so S3 credentials never leave the data owner's infrastructure.

**DataOps pipelines** — automated workflows that pull raw data from the data space, run transformations and quality checks, and publish derived datasets back. The same flow is demonstrated two ways in this hackfest: as plain Python scripts (Task 3), and as repeatable Apache Airflow DAGs (Task 4) — a lightweight standalone Airflow ships with each participant's stack at `http://<MY_HOST>:21006`.

### The 6G-DALI Metadata Application Profile (MAP)

Every dataset registered in the data space carries metadata following the **6G-DALI MAP**, which extends DCAT-AP 3.0 with 5G/6G-specific fields:

| Layer | Fields | Purpose |
|-------|--------|---------|
| **DCAT-AP** | title, description, license, keywords, access rights | Standard EU open data discovery |
| **6G-DALI Identity** | SNS project name, GDPR/FAIR compliance | Project-level tracking |
| **Testbed Context** | environment, network domain, 3GPP release, frequency band, RAN type, compute infrastructure | Characterise the measurement setup |
| **Experimentation** | observation points, measurement family, tools, measured variables | Describe what was measured and how |
| **Provenance** | wasDerivedFrom, wasGeneratedBy, wasAttributedTo | Track dataset lineage through processing |

---

## Hackfest Architecture

```
                         Hackfest Venue
  ┌──────────────────────────────────────────────────────┐
  │                                                      │
  │   Central EDC (hosted once)                          │
  │   ┌──────────────┐  ┌─────────┐  ┌──────────────┐   │
  │   │  EDC          │  │ RustFS  │  │ PostgreSQL   │   │
  │   │  :20000 UI    │  │ :9000   │  │              │   │
  │   │  :20001 Mgmt  │  │ :9001   │  │              │   │
  │   │  :20002 DSP   │  │         │  │              │   │
  │   └──────┬────────┘  └─────────┘  └──────────────┘   │
  │          │ DSP protocol                              │
  │          │                                           │
  │   ┌──────┴──────────────────────────────────┐        │
  │   │         LAN / Wi-Fi                     │        │
  │   └──────┬──────────┬───────────┬───────────┘        │
  │          │          │           │                     │
  │   Participant A   Participant B   Participant C  ... │
  │   ┌──────────────┐┌──────────────┐┌──────────────┐  │
  │   │ EDC :21000   ││ EDC :21000   ││ EDC :21000   │  │
  │   │ RustFS :21004││ RustFS :21004││ RustFS :21004│  │
  │   │ Airflow:21006││ Airflow:21006││ Airflow:21006│  │
  │   │ PG           ││ PG           ││ PG           │  │
  │   └──────────────┘└──────────────┘└──────────────┘  │
  └──────────────────────────────────────────────────────┘
```

## Prerequisites

Each participant needs:

- Docker and Docker Compose
- Python 3.9+ with pip
- A terminal / command line
- Network access to the central EDC host

## Setup

| Guide | Who | Description |
|-------|-----|-------------|
| [Setup — Central EDC](tasks/setup-central.md) | Organiser | Start the central stack and register sample assets |
| [Setup — Participant](tasks/setup-participant.md) | Each participant | Start your local stack, configure `.env`, verify connectivity |

---

## Workshop Tracks

### Track 1 — Web UI Operations

**Objective:** Operate in the data space through the Catalog UI — register datasets, browse the federated catalogue, and download data, all without writing code.

The organisers will present the Data Lab components, the Dataspace Protocol, the 6G-DALI Metadata Application Profile, the Catalog UI, and the Dataset Submission Portal. Participants will then deploy their local stack and work through the UI.

| Task | Tool | What you will learn |
|------|------|---------------------|
| [Setup — Participant](tasks/setup-participant.md) | Docker Compose | Deploy your local EDC + RustFS + PostgreSQL stack |
| [Task 1 — Bring your own data](tasks/task-01-bring-your-own-data.md) | Catalog UI: Submit Dataset | Register a dataset via the 4-step wizard, then browse assets, metadata and lineage, and download datasets from the Catalog UI |

**Topics covered:** Data Lab architecture (EDC, RustFS, DataOps), Catalog UI (assets, metadata, lineage, agreements, negotiations, transfers, per-asset Preview and Validation buttons), Dataset Submission Portal (metadata wizard, file upload, quality checks, structured JSON-LD dataset description), catalogue discovery and dataset download.

**Expected outcomes:** Run the Data Lab locally, register a dataset through the web portal, discover and inspect data assets across the federated data space, and download datasets through the Catalog UI.

---

### Track 2 — Programmatic Access

**Objective:** Perform the same data space operations programmatically, via the EDC Management API and Python scripts: register datasets, pull from the central connector, and exchange data with other participants.

Participants will register a dataset via Python, pull a dataset from the central connector, and discover and pull datasets from other participants — all through the Management API.

| Task | Tool | What you will learn |
|------|------|---------------------|
| [Task 2 — Register a dataset](tasks/task-02-register.md) | `tr02_s1_register.py` | Programmatic registration: upload to S3, create asset with MAP metadata, create policy and contract |
| [Task 3 — Pull from central EDC](tasks/task-03-pull.md#from-the-central-edc) | `tr02_s2_pull_central.py` | Discover the central catalogue, negotiate a contract, transfer a dataset to your local storage |
| [Task 3 — Pull from a peer](tasks/task-03-pull.md#from-a-peer) | `tr02_s3_pull_peer.py` | Browse another participant's catalogue, negotiate and pull their dataset |
| [Task 3 — Pull from your own connector](tasks/task-03-pull.md#from-your-own-connector-local) | `tr02_s4_pull_local.py` | Self-transfer: negotiate with your own connector and pull one of your assets locally |

**Topics covered:** Programmatic asset registration via the Management API, 6G-DALI MAP metadata, catalogue discovery, contract negotiation and data transfer, cross-domain peer-to-peer exchange, policies and governance.

**Expected outcomes:** Register datasets via scripts using standardised metadata, pull datasets from the central connector via contract negotiation, and exchange datasets directly with other participants.

---

### Track 3 — DataOps and Build Your Own

**Objective:** Execute data processing workflows and build custom extensions on top of the Data Lab.

Participants will run a DataOps pipeline that pulls data, augments it, and publishes derived datasets with provenance metadata. They will then build their own custom pipelines and extensions.

| Task | Tool | What you will learn |
|------|------|---------------------|
| [Task 3 — Pull, process, push](tasks/task-03-pull.md#pull-process--push-dataops-lifecycle) | `tr02_s5_pull_process_push.py` | Full DataOps lifecycle: negotiate → transfer → augment → publish with provenance and lineage |
| [Task 4 — Airflow DataOps DAGs](tasks/task-04-airflow-dataops.md) | Airflow at `:21006` | The same pull/process/validate lifecycle as repeatable, triggerable Airflow DAGs, plus automated Great Expectations quality checks |
| [Task 5 — Build your own extensions](tasks/task-05-build-your-own.md) | Guide | Custom pipelines, multi-source composition, AI features, custom policies |

**Topics covered:** DataOps architecture (pull → process → publish), data augmentation, provenance tracking (PROV-O), dataset lineage visualisation, versioned derived datasets, Airflow-based pipeline orchestration, automated data quality validation (Great Expectations), custom pipeline development.

**Development opportunities:**

- **DataOps Services** — data quality checks, feature engineering, aggregation, multi-source joins
- **Dataspace Extensions** — custom policies, restricted access, multi-domain workflows
- **AI-Driven Features** — auto-metadata generation, anomaly detection, data summarisation
- **Proof-of-Concept Development** — autonomous DataOps workflows, intent-driven data management

**Expected outcomes:** Execute pull → process → publish pipelines (as scripts and as Airflow DAGs), track dataset lineage through provenance, produce versioned derived assets, validate data quality automatically, build custom extensions on the Data Lab infrastructure.

**Contributions developed during the Hackfest may become candidates for future integration into OpenOP.**

---

## Reference

### Services and Ports

#### Central EDC

| Service     | Port  | Purpose                      |
|-------------|-------|------------------------------|
| EDC UI      | 20000 | Catalog UI at `/api/catalog` |
| EDC Mgmt    | 20001 | Management API               |
| EDC DSP     | 20002 | Dataspace Protocol endpoint  |
| EDC Control | 20003 | Internal control plane       |
| RustFS API  | 9000  | S3-compatible storage        |
| RustFS UI   | 9001  | Storage web console          |

#### Participant

| Service     | Port  | Purpose                      |
|-------------|-------|------------------------------|
| EDC UI      | 21000 | Catalog UI at `/api/catalog` |
| EDC Mgmt    | 21001 | Management API               |
| EDC DSP     | 21002 | Dataspace Protocol endpoint  |
| EDC Control | 21003 | Internal control plane       |
| RustFS API  | 21004 | S3-compatible storage        |
| RustFS UI   | 21005 | Storage web console          |

### EDC Transfer Types

| Type | Data Address | Use case |
|------|-------------|----------|
| `MinioAsset` | Source: reads from S3-compatible storage | Provider-side dataset storage |
| `PresignedHttpData` | Destination: HTTP PUT to presigned URL | Consumer-side S3 ingestion |

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
   │  (on consumer's S3)              │
   │                                  │
   │  POST /transferprocesses         │
   │ ────────────────────────────────►│  Start transfer
   │                                  │
   │         Provider reads from      │
   │         its S3 and PUTs          │
   │         to the presigned URL     │
   │                                  │
   │  ◄──── file arrives in S3 ─────│
   │                                  │
```

### Management API Cheat Sheet

```bash
# List assets
curl -X POST http://<MY_HOST>:21001/management/v3/assets/request \
  -H "Content-Type: application/json" -d '{}'

# Browse a remote catalogue
curl -X POST http://<MY_HOST>:21001/management/v3/catalog/request \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "counterPartyAddress": "http://<PROVIDER>:20002/protocol",
    "protocol": "dataspace-protocol-http"
  }'

# Check negotiation status
curl http://<MY_HOST>:21001/management/v3/contractnegotiations/<ID>

# Check transfer status
curl http://<MY_HOST>:21001/management/v3/transferprocesses/<ID>
```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| `No dataplane found` | The EDC data plane didn't register at startup. Restart the connector. |
| `411 Length Required` | The transfer destination must use `PresignedHttpData` type, not `HttpData`. |
| `Asset not found in provider catalogue` | The provider has no contract definition. Run `setup-assets.sh` on the central EDC. |
| `409 Conflict` on asset creation | Asset already exists. Task scripts handle this gracefully — re-run is safe. |
| Negotiation stuck in `REQUESTED` | Check that both connectors can reach each other's DSP endpoint (central 20002 / participant 21002). |
| Presigned URL expired | URLs expire after 5 minutes. Re-run the task script. |
| `UnknownHostException` | The EDC container can't resolve the storage hostname. Ensure RustFS is running on the same Docker network. |

### Docker Image

```
ghcr.io/sparkworksnet/6gdali-testbed-connector:latest
```

Custom extensions included:
- **MinioAssetDataSource** — one-shot read from S3-compatible storage (no polling)
- **PresignedHttpData Sink** — HTTP PUT with explicit Content-Length for presigned URLs
- **Catalog UI** — web dashboard at `/api/catalog` with assets, contracts, policies, agreements, negotiations, transfers, and lineage tree
- **Data plane self-registration** — automatic registration with `MinioAsset` source and `PresignedHttpData-PUSH` transfer type

---

## Baseline Resources Provided by the Organisers

### Infrastructure
- Pre-configured central OpenOP / Data Lab instance
- Participant deployment packages (Docker Compose)
- Documentation and task guides

### Digital Assets
- Sample 5G measurement datasets (CSV)
- Metadata catalogues with 6G-DALI MAP examples
- Pre-registered assets with contract definitions

### Workflows
- DataOps processing scripts (pull → augment → publish)
- Dataspace exchange scenarios (local and cross-domain)
- Asset registration templates with MAP metadata
