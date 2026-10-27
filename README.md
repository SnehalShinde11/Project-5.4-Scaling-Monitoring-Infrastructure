# Project 5.4 — Scaling Monitoring Infrastructure with Prometheus and Grafana

## Objective

Build a scalable monitoring environment using multiple Prometheus instances, Prometheus federation, MinIO object storage, Thanos components, and Grafana unified visualization.

## Assignment Tasks

1. Simulate a scaled environment using 2–3 regional Prometheus instances.
2. Configure a master Prometheus instance to federate metrics from regional instances.
3. Set up local S3-compatible object storage using MinIO.
4. Deploy Thanos Sidecar, Store Gateway, and Query with object storage integration.
5. Configure Grafana to query metrics through Thanos Query.
6. Test durability by stopping a regional Prometheus instance and checking historical metrics through Thanos.

## Task 1 — Simulate a Scaled Environment

### Objective

Deploy three independent Prometheus instances representing the US East, EU West, and AP South regions using Docker Compose.

### Prerequisites

- Git installed.
- Docker Engine and the Docker Compose plugin installed.
- Network access to download the required container images.
- A Linux VM or host on which to run the lab.

### Regional service details

| Region | Host port | Configuration file |
|---|---:|---|
| US East | 9091 | `prometheus/us-east/prometheus.yml` |
| EU West | 9092 | `prometheus/eu-west/prometheus.yml` |
| AP South | 9093 | `prometheus/ap-south/prometheus.yml` |

Each Prometheus instance has its own configuration, regional external labels, and persistent storage volume. In the initial lab configuration, each instance scrapes its own Prometheus metrics endpoint. Add region-specific application or exporter targets when distinct target sets are required.

**Compose backup:** The repository includes the [Task 1 Compose snapshot](backups/compose/compose-task-1.yaml), which captures the configuration before the federation master was added. Use it as a reference or rollback copy only; the current [`compose.yaml`](compose.yaml) is the main configuration for the completed Task 2 setup. The snapshot still expects the repository's `.env` file for MinIO and should be run from the repository root.

### Step 1: Clone the repository

Clone the repository and enter the project directory:

```bash
git clone https://github.com/SnehalShinde11/Project-5.4-Scaling-Monitoring-Infrastructure.git
cd Project-5.4-Scaling-Monitoring-Infrastructure
```

If the repository is already cloned, change to its local directory instead of cloning it again.

### Step 2: Configure the local environment file

The Compose configuration references a local `.env` file for MinIO. Create it from the example and set a strong local lab password:

```bash
cp .env.example .env
nano .env
```

Keep the real `.env` file private. Do not commit it to Git.

### Step 3: Validate the Compose configuration

```bash
docker compose config --quiet
```

Continue if the command exits successfully without reporting a configuration error.

### Step 4: Start the three regional Prometheus instances

```bash
docker compose up -d prometheus-us-east prometheus-eu-west prometheus-ap-south
```

Docker downloads the required image if it is not already available, then starts the three regional services.

### Step 5: Check the container status

```bash
docker compose ps
```

Confirm that the `prometheus-us-east`, `prometheus-eu-west`, and `prometheus-ap-south` services are running.

### Step 6: Verify Prometheus readiness

```bash
for port in 9091 9092 9093; do
  printf "Port %s: " "$port"
  curl -s -o /dev/null -w '%{http_code}\n' \
    "http://127.0.0.1:${port}/-/ready"
done
```

Expected result: HTTP status `200` for all three ports.

### Step 7: Verify scraped metrics

```bash
for port in 9091 9092 9093; do
  echo "Checking Prometheus on port $port"
  curl -fsSG "http://127.0.0.1:${port}/api/v1/query" \
    --data-urlencode 'query=up'
  echo
done
```

Each API response should return `"status":"success"`. A healthy scrape target should report the `up` metric with value `1`.

### Step 8: Open the Prometheus web interfaces

The Compose configuration binds the Prometheus host ports to `127.0.0.1`, so the interfaces are not exposed directly to the public network.

For a remote Linux VM, create an SSH tunnel from your local computer. Replace the placeholders with your SSH username and VM public IP:

```bash
ssh -L 9091:127.0.0.1:9091 \
    -L 9092:127.0.0.1:9092 \
    -L 9093:127.0.0.1:9093 \
    <SSH_USER>@<VM_PUBLIC_IP>
```

Keep the SSH session open, then visit these URLs in your local browser:

- US East: http://localhost:9091
- EU West: http://localhost:9092
- AP South: http://localhost:9093

### Expected outcome

Three independent regional Prometheus instances are running with separate configurations, regional labels, and persistent storage. Their readiness endpoints and query APIs can be checked independently.

### Troubleshooting

- If a service is not running, inspect its logs with `docker compose logs prometheus-us-east`, replacing the service name as needed.
- If Compose reports that `.env` is missing, repeat Step 2.
- If a readiness check fails, run `docker compose ps` and inspect the corresponding service logs before continuing.

## Task 2 — Configure Prometheus Federation

### Objective

Run a federation master that collects selected metrics from the three regional Prometheus instances. The master uses the regional services' internal Docker network addresses, so it does not depend on their host-mapped ports.

### Federation configuration

The existing configuration is:

`prometheus/federation/prometheus.yml`

It defines three federation scrape jobs, each querying the regional Prometheus `/federate` endpoint with the selector `{job="prometheus"}`. The `honor_labels: true` setting preserves labels on federated time series, including each source's `region` label. Each federation job also adds a `source_region` target label for identifying the source in federation scrape-health metrics.

The Compose service is named `prometheus-federation`, maps host port `127.0.0.1:9094` to container port `9090`, and stores its TSDB in the separate `prometheus_federation_data` volume.

### Step 1: Create a backup before changing Compose

If you are adding the master service to an existing lab, save a copy of the current Compose file first:

```bash
mkdir -p backups/compose
cp compose.yaml "backups/compose/compose-before-federation-$(date +%Y%m%d-%H%M%S).yaml"
```

These are local recovery copies. Keep secrets out of backups and do not commit local backups unless they have been reviewed and sanitized.

### Step 2: Validate the configuration

From the repository directory, validate the Compose file and confirm the federation service is listed:

```bash
docker compose config --quiet
docker compose config --services
```

The service list should include `prometheus-federation` as well as the three regional Prometheus services and MinIO.

### Step 3: Start the federation master

Ensure the three regional Prometheus services are running, then start the master:

```bash
docker compose up -d prometheus-federation
docker compose ps
```

### Step 4: Check readiness

```bash
curl -s -o /dev/null -w 'Master HTTP status: %{http_code}\n' \
  http://127.0.0.1:9094/-/ready
```

Expected result: HTTP status `200`.

### Step 5: Verify federation scrape targets

Allow at least 15–30 seconds for the first scrape, then run:

```bash
curl -s http://127.0.0.1:9094/api/v1/targets | python3 -c '
import json, sys
data = json.load(sys.stdin)
for target in data["data"]["activeTargets"]:
    print(
        "job:", target["labels"].get("job"),
        "| health:", target["health"],
        "| scrape URL:", target["scrapeUrl"],
        "| error:", target.get("lastError", "")
    )
'
```

Expected result: `federation-us-east`, `federation-eu-west`, and `federation-ap-south` each report health `up`, with no scrape error.

### Step 6: Query federated regional metrics

Check that the master has received the regional `up` time series:

```bash
curl -sG 'http://127.0.0.1:9094/api/v1/query' \
  --data-urlencode 'query=count by (region) (up{job="prometheus"})' \
  | python3 -m json.tool
```

Expected result: successful query results for the `us-east`, `eu-west`, and `ap-south` region labels, each with value `1`.

Verify the federation scrape-health metrics separately:

```bash
curl -sG 'http://127.0.0.1:9094/api/v1/query' \
  --data-urlencode 'query=up{job=~"federation-.*"}' \
  | python3 -m json.tool
```

Expected result: three series, one per federation job, each with value `1`. If a target is down, inspect `docker compose logs prometheus-federation` and check that all regional services are running.

### Step 7: Access the master safely

The master is bound to localhost rather than exposed directly to the public network. For a remote VM, add a tunnel for port `9094` to the SSH command used in Task 1:

```bash
ssh -L 9091:127.0.0.1:9091 \
    -L 9092:127.0.0.1:9092 \
    -L 9093:127.0.0.1:9093 \
    -L 9094:127.0.0.1:9094 \
    <SSH_USER>@<VM_PUBLIC_IP>
```

With the tunnel active, open http://localhost:9094.

### Expected outcome

A fourth Prometheus instance acts as the federation master and successfully collects the selected `job="prometheus"` series from all three regional instances. Regional labels remain queryable, and federation target health can be monitored independently.

**Scope note:** Federation only transfers time series matched by the configured `match[]` selector; it does not automatically copy every metric from each regional Prometheus. The initial regional configurations scrape their own Prometheus metrics endpoints. Add application or exporter scrape targets to the regional configurations when the lab requires distinct regional workloads.

## Task 3 — Configure MinIO object storage

### Objective

Create the S3-compatible bucket that Thanos will use for Prometheus TSDB blocks in Task 4. This task verifies bucket access only; Thanos uploads and historical-query validation are covered later.

### Prerequisites

- Task 1 services are running and MinIO readiness returns HTTP `200`.
- The repository's `.env` file exists locally and contains `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`. Create it from `.env.example` if needed, and set a strong lab password.
- Run the commands below on the VM from the repository root. MinIO is intentionally bound to `127.0.0.1:9000`; do not expose this endpoint publicly.

### Step 1: Check MinIO readiness

```bash
cd ~/Project-5.4

sudo docker compose ps minio

curl -s -o /dev/null \
  -w 'MinIO readiness HTTP status: %{http_code}\n' \
  http://127.0.0.1:9000/minio/health/ready

# Confirm required variable names without printing secret values
sed -E 's/=.*/=<hidden>/' .env
```

Expected: MinIO is running, readiness returns `200`, and the two variable names are present.

### Step 2: Install AWS CLI in a local Python virtual environment

The AWS CLI can use MinIO's S3-compatible API. The virtual environment keeps the Python package installation isolated from system Python.

```bash
sudo apt-get update
sudo apt-get install -y python3-venv

python3 -m venv .venv-task3
. .venv-task3/bin/activate
python -m pip install --upgrade pip
python -m pip install awscli
```

### Step 3: Authenticate and create the bucket

The following commands read credentials from the local `.env` file; they do not print the values. Do not commit `.env` or paste its contents into chat.

```bash
cd ~/Project-5.4

export AWS_ACCESS_KEY_ID="$(sed -n 's/^MINIO_ROOT_USER=//p' .env)"
export AWS_SECRET_ACCESS_KEY="$(sed -n 's/^MINIO_ROOT_PASSWORD=//p' .env)"
export AWS_DEFAULT_REGION=us-east-1
export AWS_EC2_METADATA_DISABLED=true

aws configure set default.s3.signature_version s3v4

# List buckets before creating the target bucket
aws --endpoint-url http://127.0.0.1:9000 s3 ls

# Create the bucket; if it already exists, continue to verification
aws --endpoint-url http://127.0.0.1:9000 s3 mb s3://thanos
```

If the bucket already exists, AWS CLI may report that it cannot be created because it already exists. This is not a problem; proceed to the verification command.

### Step 4: Verify the bucket

```bash
aws --endpoint-url http://127.0.0.1:9000 s3 ls s3://thanos

# Remove credentials from this shell when finished
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY
```

An empty listing with no error is expected for a newly created bucket because no Thanos blocks have been uploaded yet.

### Expected outcome

- MinIO readiness is HTTP `200`.
- The `thanos` bucket is created and can be listed using the AWS CLI.
- Credentials remain in the ignored local `.env` file and are not committed.
- No claim is made yet about Thanos uploads or historical queries; those are verified in Tasks 4 and 6.

### Troubleshooting

- **Connection refused:** check `sudo docker compose ps minio` and `sudo docker compose logs --tail=100 minio`.
- **Access denied / signature error:** verify the local `.env` variable names and values; ensure the AWS CLI signature version is set to `s3v4`.
- **Missing credentials:** check that both required variables exist without displaying their values: `sed -E 's/=.*/=<hidden>/' .env`.
- **Bucket already exists:** run the bucket listing command to verify access instead of trying to recreate it.

## Documentation status

Tasks 1–3 currently have end-user execution and verification instructions. Tasks 4–6 will be documented with tested commands and expected results as the Thanos, Grafana, and durability-test implementations are completed. Use the configuration files already included in the repository rather than recreating them manually.
