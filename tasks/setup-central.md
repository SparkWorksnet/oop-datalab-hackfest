# Setup — Central EDC

The central EDC runs once at the hackfest venue. It provides the shared catalogue with sample datasets that participants pull from.

## Start the stack

```bash
cd central-edc

# Place sample CSV files in seed-data/ before starting (optional — samples are included)
docker compose up -d
```

Wait for all services to be healthy:

```bash
docker compose ps
```

All services should show `healthy` or `running`.

## Register assets

```bash
chmod +x setup-assets.sh
./setup-assets.sh <CENTRAL_HOST_IP>
```

This creates:
- An **open-access policy** (`open-policy`) — no constraints
- A **contract definition** (`open-contract`) — matches all assets
- Two **sample assets** with 6G measurement data

## Verify

1. Open `http://<CENTRAL_HOST_IP>:18180/api/catalog` — the Catalog UI should show the two sample assets
2. Open `http://<CENTRAL_HOST_IP>:9001` — the RustFS console should show the `central-datasets` bucket with the CSV files (login: `central-admin` / `central-secret-2024`)
3. Test the DSP endpoint:

```bash
curl -X POST http://<CENTRAL_HOST_IP>:18181/management/v3/catalog/request \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "counterPartyAddress": "http://<CENTRAL_HOST_IP>:18182/protocol",
    "protocol": "dataspace-protocol-http"
  }'
```

This should return a `dcat:Catalog` with the two datasets.

## Services

| Service     | Port  | Purpose                      |
|-------------|-------|------------------------------|
| EDC UI      | 18180 | Catalog UI at `/api/catalog` |
| EDC Mgmt    | 18181 | Management API               |
| EDC DSP     | 18182 | Dataspace Protocol endpoint  |
| EDC Control | 18183 | Internal control plane       |
| RustFS API  | 9000  | S3-compatible storage        |
| RustFS UI   | 9001  | Storage web console          |

## Adding more datasets

To add more datasets after startup:

1. Upload files to RustFS via the console UI or `aws` CLI:

```bash
aws --endpoint-url http://<CENTRAL_HOST_IP>:9000 s3 cp myfile.csv s3://central-datasets/
```

2. Register the asset:

```bash
curl -X POST http://<CENTRAL_HOST_IP>:18181/management/v3/assets \
  -H "Content-Type: application/json" \
  -d '{
    "@context": {"@vocab": "https://w3id.org/edc/v0.0.1/ns/"},
    "@id": "my-new-dataset",
    "properties": {
      "name": "My New Dataset",
      "contenttype": "text/csv"
    },
    "dataAddress": {
      "type": "MinioAsset",
      "endpoint": "http://rustfs:9000",
      "bucketName": "central-datasets",
      "accessKey": "central-admin",
      "secretKey": "central-secret-2024",
      "prefix": "myfile.csv"
    }
  }'
```

The new asset will automatically be covered by the existing open contract definition.

## Reset

To start fresh:

```bash
docker compose down -v
docker compose up -d
./setup-assets.sh <CENTRAL_HOST_IP>
```

The `-v` flag removes all volumes (database + storage).
