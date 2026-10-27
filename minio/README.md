# MinIO Object Storage

MinIO provides S3-compatible object storage for the lab's historical Prometheus metrics.

## Current status

The `thanos` bucket has been created and verified using the AWS CLI against the local MinIO endpoint at `http://127.0.0.1:9000`. The endpoint is bound to localhost by Compose and should not be exposed directly to the public internet.

## End-user setup

Follow **Task 3 — Configure MinIO object storage** in the repository's [main README](../README.md). It contains the prerequisites, isolated AWS CLI installation, safe credential loading from `.env`, bucket creation, verification, expected results, and troubleshooting.

The bucket is expected to be empty until Thanos Sidecars begin uploading TSDB blocks in Task 4. Bucket creation alone does not verify Thanos integration or historical queries.
