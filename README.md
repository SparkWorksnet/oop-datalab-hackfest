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

**DataOps pipelines** — automated workflows that pull raw data from the data space, run transformations and quality checks, and publish derived datasets back. In the full 6G-DALI deployment this is Apache Airflow; in this hackfest we demonstrate the same flow with Python scripts.

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
  │   │ RustFS:9000│ │ RustFS:9000│ │ RustFS:9000│      │
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

## Setup

| Guide | Who | Description |
|-------|-----|-------------|
| [Setup — Central EDC](tasks/setup-central.md) | Organiser | Start the central stack and register sample assets |
| [Setup — Participant](tasks/setup-participant.md) | Each participant | Start your local stack, configure `.env`, verify connectivity |

---

## Workshop Tracks

### Track 1 — Getting Started with Data Lab

**Objective:** Become familiar with the Data Lab architecture and core functionalities.

Participants will deploy the Data Lab module locally, explore the APIs and Catalog UI, and register their first dataset with rich 6G-DALI metadata.

| Task | Tool | What you will learn |
|------|------|---------------------|
| [Task 1 — Register a dataset](tasks/task-01-register.md) | `task_local_01-register.py` | Upload data to S3, register an EDC asset with MAP metadata, create policies and contracts, verify in the Catalog UI |
| [Task 3 — Bring your own data](tasks/task-03-bring-your-own-data.md) | Catalog UI: Submit Dataset | Use the built-in submission portal to upload your own CSV, configure metadata and quality checks, register on EDC |

**Topics covered:** Data Lab architecture, data and model catalogues, asset discovery, metadata and governance concepts, Catalog UI, Dataset Submission Portal.

**Expected outcomes:** Run Data Lab locally, register and discover data assets, submit datasets via the web portal with quality checks, understand how data assets become first-class entities within OpenOP.

---

### Track 2 — Experimenting with Dataspace Capabilities

**Objective:** Experience trusted and governed exchange of data across federated operator environments.

The Hackfest provides a pre-configured federation: a central EDC representing a shared operator domain, plus each participant running their own connector. Participants will publish assets, discover remote catalogues, negotiate contracts, and transfer data across domains.

| Task | Tool | What you will learn |
|------|------|---------------------|
| [Task 2 — Pull, process, push](tasks/task-02-pull-process-push.md) | `task_local_02-pull-process-push.py` | Contract negotiation, presigned URL transfer, data augmentation, derived asset registration with provenance |
| [Task 4 — Pull from central EDC](tasks/task-04-pull-central.md) | `task_central_04-pull.py` | Cross-domain catalogue discovery, inter-connector negotiation, cross-network data transfer |
| [Task 5 — Peer-to-peer exchange](tasks/task-05-peer-exchange.md) | `task_peer_05-discover-exchange.py` | Browse another participant's catalogue, negotiate and pull their dataset |

**Topics covered:** Dataspace concepts, federation mechanisms, trusted asset exchange, data governance policies, inter-domain interoperability, sharing of datasets.

**Expected outcomes:** Federated sharing of data assets, controlled and trusted data exchange, cross-domain interoperability, dataspace-enabled service ecosystems.

---

### Track 3 — Experimenting with DataOps

**Objective:** Explore how data pipelines can be designed, orchestrated, and executed using DataOps principles within the data space.

Participants will execute data processing workflows that pull data from the data space, transform it, and publish derived datasets back — demonstrating the full DataOps lifecycle.

| Task | Tool | What you will learn |
|------|------|---------------------|
| [Task 2 — Pull, process, push](tasks/task-02-pull-process-push.md) | `task_local_02-pull-process-push.py` | Manual DataOps: pull → augment → publish with provenance and lineage tracking |

**Topics covered:** DataOps architecture, pipeline orchestration, dataset preparation, data augmentation, provenance tracking, lineage visualisation.

**Expected outcomes:** Understand how data services can be orchestrated, how data pipelines become reusable services, how data preparation can be automated, and how DataOps capabilities integrate naturally with OpenOP.

---

### Track 4 — Build Your Own Extensions

**Objective:** Go beyond experimentation and actively contribute new functionality.

Participants are encouraged to bring their own datasets, AI models, and analytics services. Use the Data Lab infrastructure to register, share, and process your own data.

| Task | Guide | What you will do |
|------|-------|------------------|
| [Task 6 — Build your own extensions](tasks/task-06-build-your-own.md) | Guide | Custom pipelines, multi-source composition, AI features, custom policies |

**Development opportunities:**

- **DataOps Services** — data ingestion, transformation pipelines, quality checks, metadata generation
- **Dataspace Extensions** — new asset sharing scenarios, enhanced governance policies, multi-domain workflows
- **AI-Driven Features** — AI-based data cleaning, automated dataset enrichment, AI-assisted metadata generation
- **Proof-of-Concept Development** — autonomous DataOps workflows, intent-driven data management, cross-domain AI model orchestration

**Contributions developed during the Hackfest may become candidates for future integration into OpenOP.**

---

## Reference

### Services and Ports

#### Central EDC

| Service     | Port  | Purpose                      |
|-------------|-------|------------------------------|
| EDC UI      | 18180 | Catalog UI at `/api/catalog` |
| EDC Mgmt    | 18181 | Management API               |
| EDC DSP     | 18182 | Dataspace Protocol endpoint  |
| EDC Control | 18183 | Internal control plane       |
| RustFS API  | 9000  | S3-compatible storage        |
| RustFS UI   | 9001  | Storage web console          |

#### Participant

| Service     | Port  | Purpose                      |
|-------------|-------|------------------------------|
| EDC UI      | 28180 | Catalog UI at `/api/catalog` |
| EDC Mgmt    | 28181 | Management API               |
| EDC DSP     | 28182 | Dataspace Protocol endpoint  |
| EDC Control | 28183 | Internal control plane       |
| RustFS API  | 9000  | S3-compatible storage        |
| RustFS UI   | 9001  | Storage web console          |

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
curl -X POST http://<MY_HOST>:28181/management/v3/assets/request \
  -H "Content-Type: application/json" -d '{}'

# Browse a remote catalogue
curl -X POST http://<MY_HOST>:28181/management/v3/catalog/request \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "counterPartyAddress": "http://<PROVIDER>:18182/protocol",
    "protocol": "dataspace-protocol-http"
  }'

# Check negotiation status
curl http://<MY_HOST>:28181/management/v3/contractnegotiations/<ID>

# Check transfer status
curl http://<MY_HOST>:28181/management/v3/transferprocesses/<ID>
```

### Troubleshooting

| Problem | Solution |
|---------|----------|
| `No dataplane found` | The EDC data plane didn't register at startup. Restart the connector. |
| `411 Length Required` | The transfer destination must use `PresignedHttpData` type, not `HttpData`. |
| `Asset not found in provider catalogue` | The provider has no contract definition. Run `setup-assets.sh` on the central EDC. |
| `409 Conflict` on asset creation | Asset already exists. Task scripts handle this gracefully — re-run is safe. |
| Negotiation stuck in `REQUESTED` | Check that both connectors can reach each other's DSP endpoint (port 18182/28182). |
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
