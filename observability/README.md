# AI20K observability stack

This stack runs on a dedicated EC2 host and provides:

- Grafana on port `3000`;
- Prometheus on localhost port `9090`;
- Pushgateway on localhost port `9091` for short-lived CI metrics;
- Loki on port `3100` for logs;
- Tempo on ports `4317`/`4318` for OTLP traces.

The develop and production EC2 hosts run the `docker-compose.observability.yml`
override. That override exposes the backend `/metrics` endpoint on host port
`8001`, node exporter on `9100`, and cAdvisor on `8080`. Grafana Alloy collects
Docker logs and forwards application traces. The Grafana overview dashboard
shows request rate, p95 latency, 5xx rate, host CPU/memory, and backend
container CPU/memory by environment. cAdvisor mounts the Docker socket read-only
to attach Compose service labels to container metrics used by the dashboard.

The provisioned `AI20K - CI/CD Pipeline` dashboard reads sanitized run status
and timing metrics from Prometheus. At the end of a run, CI uses its temporary
GitHub-provided `GITHUB_TOKEN` to read only that run, then sends the metrics
through the existing monitoring SSH connection to the loopback-only
Pushgateway. No GitHub PAT is required. Detailed masked logs remain in GitHub
Actions and are opened from the dashboard link; raw CI logs are not copied to
Loki.

## CI alerts

Grafana provisions these rules under `AI20K Operations` and evaluates them
every minute:

| Alert | Fires when | Why |
| --- | --- | --- |
| `CI pipeline failed` | A `push` to production branch `main` reports `failure` within the last 10 minutes | A required production test, security, build, or deployment job failed. Feature and develop runs do not alert. |
| `Production pipeline exceeded 60 minutes` | A completed `push` workflow on `main` takes longer than 3600 seconds | Production delivery is unusually slow; inspect runner queueing and the longest job. |
| `CI metrics Pushgateway unavailable` | Prometheus sees `up{job="ci-pushgateway"} < 1`, or no target data, continuously for 5 minutes | CI observability may be blind even if application CI still works. The delay avoids alerts during a short restart. |
| `Production monitoring target unavailable` | Backend, node-exporter, or cAdvisor is unavailable continuously for 3 minutes | The server/application may be down, or monitoring connectivity may be broken. |
| `Production server resource saturation` | CPU >85%, RAM >90%, or root disk >85% continuously for 10 minutes | Sustained resource pressure can cause latency, process termination, or disk write failures. The `signal` label identifies CPU, memory, or disk. |
| `Production HTTP traffic anomaly` | For 5 minutes: 5xx >5% while traffic >1 RPS, p95 >2 seconds, or traffic >100 RPS | Detects backend failures, slow requests, and traffic overload. The `signal` label identifies the breached condition. |

CI result/duration alerts apply only to production pushes on `main`. An absence
of new workflow metrics does not alert because a repository can
legitimately have no new commits. Rules are visible in Grafana Alerting after
deployment. Configure a Grafana contact point and notification policy separately
if email, Slack, or another external delivery channel is required; this change
does not introduce a new outbound credential.

The thresholds are an initial operational baseline. Review normal production
traffic for at least one week, then tune request-rate and saturation thresholds
to the server size and expected workload.

## First-time monitoring EC2 setup

Run `deploy/observability-ec2-init.sh` as root, or install Docker Engine and
the Compose plugin manually. Then copy this directory to `/opt/observability`
and create `.env` from `.env.example`.

Required values:

```dotenv
PROMETHEUS_DEV_TARGET=10.0.1.10:8001
PROMETHEUS_PROD_TARGET=10.0.2.10:8001
NODE_EXPORTER_DEV_TARGET=10.0.1.10:9100
NODE_EXPORTER_PROD_TARGET=10.0.2.10:9100
CADVISOR_DEV_TARGET=10.0.1.10:8080
CADVISOR_PROD_TARGET=10.0.2.10:8080
GRAFANA_ADMIN_PASSWORD=<long-random-password>
GRAFANA_ROOT_URL=https://grafana.example.com
GRAFANA_BIND_ADDRESS=0.0.0.0
# Set to the monitoring EC2 private IP for application hosts to reach Loki/Tempo.
TELEMETRY_BIND_ADDRESS=10.0.0.5
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
- develop/production EC2 `9100/tcp` and `8080/tcp` only from the monitoring EC2 security group;
- no public ingress to Prometheus `9090` or Tempo query API `3200`.
- no public ingress to Pushgateway `9091`; CI reaches it through SSH.

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
| `OBSERVABILITY_NODE_EXPORTER_DEV_TARGET` | Develop private address plus `:9100` |
| `OBSERVABILITY_NODE_EXPORTER_PROD_TARGET` | Production private address plus `:9100` |
| `OBSERVABILITY_CADVISOR_DEV_TARGET` | Develop private address plus `:8080` |
| `OBSERVABILITY_CADVISOR_PROD_TARGET` | Production private address plus `:8080` |
| `OBSERVABILITY_LOKI_URL` | Full Loki push URL, ending in `/loki/api/v1/push` |
| `OBSERVABILITY_TEMPO_OTLP_ENDPOINT` | Tempo private address plus `:4317` |

The existing develop/production deploy jobs use the last two values to
configure Alloy. Deployment derives the private host address from the route to
the monitoring peer and binds backend metrics/exporter ports there. The
monitoring deployment derives its telemetry bind address from the route to the
development host. Manual Compose deployments should set bind variables to the
matching private interface address. Both application EC2 hosts must be able to
reach the monitoring EC2 over the private VPC network.

On each application host, allow inbound `8001/tcp`, `9100/tcp`, and `8080/tcp`
only from the monitoring EC2 security group. The Compose override starts
node-exporter and cAdvisor alongside the backend; exporter images can be pinned
with `NODE_EXPORTER_IMAGE` and `CADVISOR_IMAGE` when updating versions.
