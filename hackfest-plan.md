# OpenOP Hackfest #3 — Workshop Plan

**Hands-on Workshop: Experimenting with Data Lab — Dataspace and DataOps Services**

This Hackfest is an intensive, hands-on technical workshop focused on the Data Lab Module Development Group (MDG) of OpenOP, based on contributions by 6G-DALI, the Flagship SNS-JU Project on 6G AI & Data.

Participants will explore how OpenOP is evolving beyond service exposure and orchestration towards a platform for data- and AI-driven service ecosystems, enabling trusted sharing and consumption of datasets, analytics services, and AI models across federated operator environments.

The Hackfest combines practical experimentation with collaborative development. Participants will deploy and explore the Data Lab capabilities locally, and will also have the opportunity to contribute new features, prototype advanced concepts, and bring their own ideas and datasets into the OpenOP ecosystem.

---

## Workshop Objectives

At the end of the Hackfest, participants will have gained practical experience with:

- Installing and running the Data Lab module locally
- Discovering and consuming datasets across federated instances
- Registering datasets through the web portal and programmatically
- Understanding dataspace-enabled exchange of digital assets
- Experimenting with DataOps workflows: pull, process, and publish
- Integrating their own datasets and building custom data pipelines

---

## Track 1 — Web UI Operations (1h 30m)

### Objective

Operate in the data space through the Catalog UI, with no code required: register datasets, browse the federated catalogue, and download data.

### Presentation

The organisers will present:

- **Data Lab architecture** — the core components: dataspace connector, S3-compatible object storage, and DataOps pipelines
- **The Dataspace Protocol** — how connectors discover catalogues, negotiate access, and transfer data
- **The Metadata Application Profile** — how datasets are described using DCAT-AP, testbed context fields, and provenance
- **The Catalog UI** — browsing assets, metadata, agreements, negotiations, transfers, and lineage
- **The Dataset Submission Portal** — registering datasets with metadata and quality checks

### Scenario

A pre-configured federation is provided:

- A **central connector** at the venue, pre-loaded with sample datasets
- Each **participant** runs their own connector and storage locally
- All connectors communicate over the local network

### Activities

Participants will:

1. Deploy the Data Lab module locally and open the Catalog UI
2. **Register** a dataset through the Dataset Submission Portal — fill in metadata, upload a file, configure quality checks, and submit
3. **Retrieve** — browse the local and central catalogues and inspect dataset metadata and lineage
4. **Download** a dataset to your machine from the Catalog UI

### Topics Covered

- Data Lab architecture
- Catalog UI: assets, metadata, lineage, agreements, negotiations, transfers
- Dataset Submission Portal and metadata profiles
- Catalogue discovery and dataset download

### Expected Outcomes

- Run the Data Lab locally
- Register a dataset through the web portal
- Discover and inspect data assets across the federation
- Download datasets through the Catalog UI

---

## Track 2 — Programmatic Access (1h 30m)

### Objective

Perform the same data space operations programmatically, using the EDC Management API and Python scripts: register datasets, pull from the central connector, and exchange data with other participants.

### Activities

Participants will:

1. **Register programmatically**
   - Run a script that uploads data, creates an asset with metadata, and sets up access policies
   - Verify the asset in the Catalog UI

2. **Pull from the central connector**
   - Browse the central catalogue, negotiate a contract, transfer a dataset, and verify it locally

3. **Exchange with other participants**
   - Browse another participant's catalogue
   - Negotiate and transfer their dataset to your local storage

### Topics Covered

- Programmatic asset registration via the Management API
- Metadata profiles and data governance
- Catalogue discovery, contract negotiation, and data transfer
- Cross-domain, peer-to-peer exchange

### Expected Outcomes

- Register datasets via scripts using standardised metadata
- Pull datasets from the central connector via sovereign data transfer
- Exchange datasets directly with other participants

---

## Track 3 — Data Operations (1h 30m)

### Objective

Design, execute, and compose data pipelines that pull data from the data space, transform it, and publish derived datasets back.

### Technology Baseline

The Data Lab provides a DataOps orchestration layer for designing and executing data pipelines as reusable services. Pipelines follow the **pull → process → publish** pattern: discover and negotiate access to source data, apply transformations, and publish results with full provenance tracking.

In the full deployment, pipelines are managed by a workflow orchestrator with scheduling, dependencies, and monitoring. The Hackfest demonstrates the same patterns using standalone scripts that participants can extend.

### Activities

Participants will:

1. **Run a DataOps pipeline** — negotiate access, transfer a dataset, augment it with derived columns, upload the result, and register it as a new derived asset with provenance
2. **Observe lineage** — verify the source → derived relationship in the Catalog UI
3. **Run multiple iterations** — produce a versioned history of derived datasets
4. **Build custom pipelines** — feature engineering, multi-source composition, dataset preparation

### Topics Covered

- DataOps: pull → process → publish lifecycle
- Pipeline orchestration and workflow design
- Data augmentation and transformation
- Provenance tracking and lineage visualisation
- Versioned derived datasets
- Custom pipeline development

### Expected Outcomes

- Orchestrate data pipelines within the data space
- Track dataset lineage through provenance
- Produce versioned derived assets
- Build and compose custom pipelines

---

## Track 4 — Contributing to the Platform (1h)

### Objective

Learn how to contribute to the Data Lab and help shape the future of OpenOP.

The Data Lab is built as an extensible, modular platform. Contributions developed during the Hackfest may become candidates for future integration into OpenOP, helping shape the next generation of capabilities at the intersection of Telecommunications, Cloud, Data and Artificial Intelligence.

### Contribution Areas

- **Datasets** — 5G/6G measurements, network KPIs, vertical industry data
- **Connector extensions** — new data source/sink types, governance policies, UI components
- **DataOps services** — reusable pipeline components: ingestion, validation, enrichment
- **AI-driven capabilities** — metadata generation, anomaly detection, intelligent discovery

### How to Contribute

- **During the Hackfest** — experiment with the platform, develop ideas, and propose them to the organisers during the session
- **After the Hackfest** — all workshop material, guides, and tools will be published openly. Participants and the wider community can browse the material, propose improvements, or contribute their own work at any time
- Accepted contributions are integrated into OpenOP with proper attribution

---

## Baseline Resources

### Infrastructure

- Pre-configured central Data Lab instance
- Participant deployment packages
- Documentation and guides

### Digital Assets

- Sample 5G measurement datasets
- Pre-registered assets with metadata
- Pre-configured access policies

### Participant Prerequisites

- Docker and Docker Compose
- Python 3.9+ with pip
- A terminal / command line
