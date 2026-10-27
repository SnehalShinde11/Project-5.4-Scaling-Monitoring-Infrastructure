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

Three independent regional Prometheus instances are configured through Docker Compose.

| Region | Host Port | Configuration |
|---|---:|---|
| US East | 9091 | `prometheus/us-east/prometheus.yml` |
| EU West | 9092 | `prometheus/eu-west/prometheus.yml` |
| AP South | 9093 | `prometheus/ap-south/prometheus.yml` |

Each instance has its own configuration, regional external labels, and persistent storage volume. The initial scrape target is the instance's own Prometheus metrics endpoint.

### Verification

Check each instance's readiness endpoint:

```bash
for port in 9091 9092 9093; do
  curl -fsS "http://127.0.0.1:${port}/-/ready"
  echo
done
