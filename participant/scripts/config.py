"""Load configuration from .env file."""

import os
from pathlib import Path

# .env lives in the participant/ dir (one level up from scripts/) so the same
# file is loaded by both these scripts and docker compose, which auto-loads the
# .env next to its compose file.
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

def _load_env():
    if not ENV_FILE.exists():
        return
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value

_load_env()

MY_HOST = os.environ.get("MY_HOST", "localhost")
PARTICIPANT_NAME = os.environ.get("PARTICIPANT_NAME", "participant")

CENTRAL_HOST = os.environ.get("CENTRAL_HOST", "192.168.1.100")
CENTRAL_PARTICIPANT_ID = os.environ.get("CENTRAL_PARTICIPANT_ID", "hackfest-central")

# ── Peer exchange (Task 5) ────────────────────────────────────────────────────
# The other participant you pull a dataset from. PEER_HOST and PEER_ASSET_ID have
# no sensible default — they must be provided in the .env (see .env.template);
# tr02_s3_pull_peer.py checks them and prints instructions if they are missing.
PEER_HOST = os.environ.get("PEER_HOST")
PEER_ASSET_ID = os.environ.get("PEER_ASSET_ID")
# The peer's connector id is normally auto-detected from their catalogue, so it
# does NOT need to be in .env. PEER_PARTICIPANT_ID is only a fallback override for
# the rare case the catalogue omits it; the default matches a peer who left
# PARTICIPANT_NAME unset (connector id "participant").
PEER_PARTICIPANT_ID = os.environ.get("PEER_PARTICIPANT_ID", "participant")

# Host-published RustFS port (used for access from the laptop). Access from
# inside the docker network always uses the container port 9000, regardless of
# how it is published on the host.
S3_HOST_PORT = os.environ.get("S3_HOST_PORT", "21004")
S3_INTERNAL_PORT = "9000"
S3_ACCESS = os.environ.get("S3_ACCESS", "participant-admin")
S3_SECRET = os.environ.get("S3_SECRET", "participant-secret-2024")

EDC_MGMT_PORT = os.environ.get("EDC_MGMT_PORT", "21001")
EDC_PROTOCOL_PORT = os.environ.get("EDC_PROTOCOL_PORT", "21002")

# The central connector's own DSP protocol port (see central-edc/docker-compose.yml's
# WEB_HTTP_PROTOCOL_PORT) — distinct from EDC_PROTOCOL_PORT above, which is this
# participant's own connector's port.
CENTRAL_PROTOCOL_PORT = os.environ.get("CENTRAL_PROTOCOL_PORT", "20002")

MY_MGMT = f"http://{MY_HOST}:{EDC_MGMT_PORT}"
MY_PROTOCOL = f"http://{MY_HOST}:{EDC_PROTOCOL_PORT}/protocol"
S3_ENDPOINT = f"http://{MY_HOST}:{S3_HOST_PORT}"
S3_INTERNAL = f"http://rustfs:{S3_INTERNAL_PORT}"

CENTRAL_PROTOCOL = f"http://{CENTRAL_HOST}:{CENTRAL_PROTOCOL_PORT}/protocol"
