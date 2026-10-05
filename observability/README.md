# AI20K observability stack

This stack runs on a dedicated EC2 host and provides:

- Grafana on port `3000`;
- Prometheus on localhost port `9090`;
- Loki on port `3100` for logs;
- Tempo on ports `4317`/`4318` for OTLP traces.

The develop and production EC2 hosts run the `docker-compose.observability.yml`
override. That override exposes the backend `/metrics` endpoint on host port
`8001` and runs Grafana Alloy to collect Docker logs and forward application
traces to this server.

## First-time monitoring EC2 setup

Run `deploy/observability-ec2-init.sh` as root, or install Docker Engine and
the Compose plugin manually. Then copy this directory to `/opt/observability`
and create `.env` from `.env.example`.

Required values:

```dotenv
PROMETHEUS_DEV_TARGET=10.0.1.10:8001
PROMETHEUS_PROD_TARGET=10.0.2.10:8001
GRAFANA_ADMIN_PASSWORD=<long-random-password>
GRAFANA_ROOT_URL=https://grafana.example.com
GRAFANA_BIND_ADDRESS=0.0.0.0
TELEMETRY_BIND_ADDRESS=0.0.0.0
```

Start or update the stack with:

```bash
docker compose --env-file .env up -d --remove-orphans
```

## Network rules

Use private EC2 addresses for `PROMETHEUS_*_TARGET`, `LOKI_URL`, and
`TEMPO_OTLP_ENDPOINT`. Security groups should allow:

- monitoring EC2 `3000/tcp` only from the administrator/VPN CIDR;
- monitoring EC2 `3100/tcp`, `4317/tcp`, and `4318/tcp` only from the develop
  and production EC2 security groups;
- develop/production EC2 `8001/tcp` only from the monitoring EC2 security group;
- no public ingress to Prometheus `9090` or Tempo query API `3200`.

The CI workflow expects these GitHub secrets:

| Secret | Purpose |
| --- | --- |
| `OBSERVABILITY_EC2_HOST` | Monitoring EC2 address |
| `OBSERVABILITY_EC2_USER` | SSH user |
| `OBSERVABILITY_EC2_SSH_KEY` | SSH private key |
| `OBSERVABILITY_GRAFANA_ADMIN_PASSWORD` | Grafana admin password |
| `OBSERVABILITY_GRAFANA_ROOT_URL` | Public/reverse-proxy Grafana URL |
| `OBSERVABILITY_DEV_TARGET` | Develop private address plus `:8001` |
| `OBSERVABILITY_PROD_TARGET` | Production private address plus `:8001` |
| `OBSERVABILITY_LOKI_URL` | Full Loki push URL, ending in `/loki/api/v1/push` |
| `OBSERVABILITY_TEMPO_OTLP_ENDPOINT` | Tempo private address plus `:4317` |

The existing develop/production deploy jobs use the last two values to
configure Alloy. Both application EC2 hosts must be able to reach the
monitoring EC2 over the private VPC network.
