#!/usr/bin/env python3
"""Generate the local Thanos S3 object-store config from the ignored .env file.

The generated thanos/objstore.yml contains credentials and must never be committed.
"""
import json
import os
from pathlib import Path

root = Path(__file__).resolve().parent.parent
env_file = root / ".env"
output = root / "thanos" / "objstore.yml"

if not env_file.is_file():
    raise SystemExit("Missing .env. Copy .env.example to .env and set the MinIO credentials.")

values = {}
for raw_line in env_file.read_text(encoding="utf-8").splitlines():
    line = raw_line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip().strip('"').strip("'")

access_key = values.get("MINIO_ROOT_USER", "")
secret_key = values.get("MINIO_ROOT_PASSWORD", "")
if not access_key or not secret_key or "replace_with_" in access_key or "replace_with_" in secret_key:
    raise SystemExit("Set non-placeholder MINIO_ROOT_USER and MINIO_ROOT_PASSWORD values in .env first.")

output.parent.mkdir(parents=True, exist_ok=True)
content = (
    "type: S3\n"
    "config:\n"
    "  bucket: thanos\n"
    "  endpoint: minio:9000\n"
    f"  access_key: {json.dumps(access_key)}\n"
    f"  secret_key: {json.dumps(secret_key)}\n"
    "  insecure: true\n"
)
output.write_text(content, encoding="utf-8")
os.chmod(output, 0o600)
print(f"Generated {output.relative_to(root)} with permissions 600. Credential values were not displayed.")
