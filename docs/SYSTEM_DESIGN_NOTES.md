# System design notes

These notes are the working record of capacity, trade-offs, and measurements. Interview discussions are logged in [LEARNING_LOG.md](LEARNING_LOG.md). Benchmark tables stay empty until the milestone that runs them.

## Capacity sketch

Used to justify one modular monolith, PostgreSQL full-text search, and a single API process.

| Item | Sketch |
| --- | --- |
| Organizations | about 100 |
| Members per organization | about 20 |
| Projects | tens per active organization |
| Tasks | hundreds |
| Documents | low hundreds |

At this size, a second database, a dedicated search engine, a dedicated vector database, and a second deployable service add operational cost without a measured bottleneck. Caching is added only after a query plan or a Locust run shows the need.

What would change the decision later:

- Task-list p99 dominated by a sequential scan after the M4 indexes are in place, at a volume well above this sketch.
- Full-text ranking or write amplification that PostgreSQL cannot hold. That is the M6 discussion.
- Retrieval quality or vector scale that makes pgvector in this database the limiter. That is the M12 discussion.
- A worker or API failure domain that must deploy and scale on its own. That is the only door to extracting a service. Kubernetes is still out.

## How the system evolves

1. One process, synchronous writes, tenant filter in the repository, composite foreign keys.
2. Outbox after commit, at-least-once handlers, idempotent consumers (M5).
3. PostgreSQL full-text search (M6). Redis cache only where M7 measures a win.
4. RLS and `SET LOCAL` as a second read barrier on pooled connections (M8).
5. Nginx, CI, backups, expand/contract migrations (M10).
6. pgvector in the same database (M12), then named tools with server-issued confirmations (M13).

## Locust method

One load tool. Results are compared inside the same Compose setup. Absolute numbers are not production SLOs.

Each run records:

- p50, p95, p99 latency
- throughput
- database time (`pg_stat_statements` when the image can preload it, otherwise `log_min_duration_statement`)
- CPU and memory from `docker stats`
- cache hit ratio once a cache exists (M7)

No Prometheus or Grafana in this roadmap.

## M4 — task list and create

Status: not run.

Intentional bottleneck: N+1 loading of project and assignee. Cache hit ratio is not applicable.

| Run | p50 | p95 | p99 | Throughput | DB time | CPU | Memory | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Before | | | | | | | | N+1 |
| After | | | | | | | | Fixed list query |

Diagnosis:

## M7 — dashboard

Status: not run.

Uncached aggregates first. Redis only if that run shows a cache is worth it. Intentional bottleneck: a stampede on a cold key, then a short single-flight lock.

Also record what breaks if TTL is the only invalidation.

| Run | p50 | p95 | p99 | Throughput | DB time | Hit ratio | CPU | Memory | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Uncached | | | | | | n/a | | | |
| Cached, stampede | | | | | | | | | |
| After single-flight | | | | | | | | | |

## M10 — through Nginx

Status: not run.

Compare with the M4 baseline. Intentional bottleneck: a pool or index setting that opens a gap between p50 and p99.

| Run | p50 | p95 | p99 | Throughput | DB time | CPU | Memory | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Baseline via Nginx | | | | | | | | |
| After the bottleneck fix | | | | | | | | |

## Design discussions parked here

Short reminders. The full conversation goes in the learning log.

- Health checks tell a load balancer where to send traffic. They are a poor place to hide a deep dependency diagnostic.
- Shared schema with `organization_id` fits the sketch. Isolation is tested with cross-tenant API cases and, from M4, with a foreign key that rejects a bad write.
- Keyset pagination stays stable under concurrent inserts. Offset does not.
- Notification fan-out is eventually consistent. The create response returns before the notification row exists.
- A dashboard cache needs an explicit invalidation story. TTL alone serves stale counts after a write.
- Production rollback of a bad migration is the previous application plus a forward schema fix, after a backup. See [DEPLOYMENT.md](DEPLOYMENT.md).
