# Task 4 — Peer-to-Peer Exchange

Discover and pull a dataset from another participant's EDC connector.

**Script:** `participant/scripts/tr02_s3_peer_exchange.py`

## Prerequisites

- Your participant stack running (Tasks 1-2 completed — you have assets registered)
- Another participant's stack running with assets registered
- You know the other participant's IP address

## Run

```bash
cd participant/scripts
python tr02_s3_peer_exchange.py <PEER_IP>
```

## What happens

### Step 1: Browse the peer's catalogue

Your connector queries the other participant's EDC catalogue via the DSP protocol. Unlike Task 3 (which queries the central EDC), here you are connecting directly to another participant on the same network.

This demonstrates the **federated topology** — every participant is both a provider and a consumer simultaneously.

### Step 2: Select and negotiate

The script lists all datasets available from the peer, selects the first one, and negotiates a contract. Both sides use the same open-access policy, so the negotiation completes automatically.

### Step 3: Transfer

The peer's EDC reads the dataset from their RustFS and PUTs it to a presigned URL on your RustFS. The data lands in your `received/from-peer/` prefix.

## What to try

- Browse multiple participants' catalogues to see different datasets
- Pull a dataset that was derived (augmented) by another participant — check its provenance in the Lineage tab
- Register a dataset specifically for sharing with peers — use custom MAP metadata describing your testbed

## Verify

1. Check your **Catalog UI** — Negotiations tab shows the peer-to-peer negotiation
2. Check your **RustFS UI** — the file is in `received/from-peer/`
3. Check the peer's **Catalog UI** — their Negotiations tab shows the same negotiation from the provider side

## The Federated Picture

After multiple participants complete this task, the hackfest venue has a live federated data space:

```
  Participant A                    Participant B
  ┌────────────┐                  ┌────────────┐
  │ my-data    │ ◄── negotiate ──►│ my-data    │
  │ augmented  │ ◄── transfer  ──►│ augmented  │
  │ from-peer/ │                  │ from-peer/ │
  └─────┬──────┘                  └──────┬─────┘
        │                                │
        └────── both discover ───────────┘
               Central EDC
          ┌──────────────────┐
          │ sample datasets  │
          └──────────────────┘
```
