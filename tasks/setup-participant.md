# Setup — Participant

Each participant runs this on their own machine.

## Configure

```bash
cd participant
cp .env.template .env
```

Edit `.env` and set:
- `MY_HOST` — your machine's IP address (not `localhost`)
- `CENTRAL_HOST` — the IP of the central EDC (provided by the organiser)
- `PARTICIPANT_NAME` — your team name

## Start the stack

`docker compose` automatically loads `participant/.env`, so the `MY_HOST` and
`PARTICIPANT_NAME` you set above are picked up — no `export` needed.

```bash
cd participant
docker compose up -d
```

Wait for all services to be healthy:

```bash
docker compose ps
```

## Install Python dependencies

```bash
pip install -r scripts/requirements.txt
```

## Verify

1. Open the **Catalog UI** at `http://<MY_HOST>:21000/api/catalog` — should load with empty tables
2. Open the **RustFS UI** at `http://<MY_HOST>:21005` — login with `participant-admin` / `participant-secret-2024`
3. Check that the `my-datasets` and `received` buckets exist
4. Test connectivity to the central EDC:

```bash
curl -X POST http://<MY_HOST>:21001/management/v3/catalog/request \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "counterPartyAddress": "http://<CENTRAL_HOST>:20002/protocol",
    "protocol": "dataspace-protocol-http"
  }'
```

This should return the central EDC's catalogue with its sample datasets.

## Services

| Service     | Port  | Purpose                      |
|-------------|-------|------------------------------|
| EDC UI      | 21000 | Catalog UI at `/api/catalog` |
| EDC Mgmt    | 21001 | Management API               |
| EDC DSP     | 21002 | Dataspace Protocol endpoint  |
| EDC Control | 21003 | Internal control plane       |
| RustFS API  | 21004 | S3-compatible storage        |
| RustFS UI   | 21005 | Storage web console          |

## Reset

To start fresh (wipes all data, assets, negotiations, transfers):

```bash
docker compose down -v
docker compose up -d
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Cannot connect to localhost:21000` | Use your machine's IP instead of localhost |
| RustFS UI shows no buckets | Run `docker compose run --rm rustfs-init` to recreate buckets |
| Catalogue request returns empty | Central EDC may not have assets registered — ask the organiser to run `setup-assets.sh` |
| `Connection refused` to central EDC | Check that `CENTRAL_HOST` in `.env` is correct and the central stack is running |

## Next steps

Once setup is verified, proceed to [Task 2 — Register a dataset](task-02-register.md).
