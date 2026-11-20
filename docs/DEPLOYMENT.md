# Deployment

This file records how the app runs today and the production rules M10 must meet. Sections marked **M10** are not implemented.

## Local API, shared database

Compose runs the API and Redis 8. PostgreSQL is the shared Supabase free-tier database. See [ADR 019](DECISIONS.md).

```powershell
docker compose -f infra/compose.yaml up --build -d
docker compose -f infra/compose.yaml run --rm api python -m alembic upgrade head
```

- `apps/api/.env` supplies `DATABASE_URL`. It is not committed.
- Use Supabase's session pooler, port 5432. The transaction pooler on port 6543 is the wrong mode for Alembic.
- `GET /health` returns 200 from the platform app. It does not check PostgreSQL.
- `GET /api/v1/openapi.json` is the product contract. `/health` is not in that document.
- Alembic is a separate command. The API does not migrate itself on startup.
- Redis is local, healthy, and unused by the API until a later milestone needs a cache, a rate limit, or the outbox publisher.
- Pytest from `apps/api` loads the same `.env` and migrates that shared database.

The free tier is enough for the current data volume. The project sleeps after inactivity, and waking it is a dashboard action. A database reset deletes the other developer's rows.

`Secure` cookies are on when the site is served over HTTPS. Local HTTP Compose may turn `Secure` off through settings. That exception stays documented beside the setting. Cookie settings arrive in M1.

There is no cloud account, TLS certificate, or CI workflow yet.

## Request path (filled in at M10)

Client → DNS → Nginx → API process → PostgreSQL, and the outbox poller in the worker → Redis → notification handler → PostgreSQL.

The write-up of that path belongs in this file when M10 is done.

## Environments

| Environment | Purpose | Data |
| --- | --- | --- |
| Local Compose | Development and the benchmark baselines | Disposable |
| Staging | Chosen with the cloud target at the start of M10 | Restorable from backup |
| Production | The deployed monolith and worker | Backup before every migration |

Local, staging, and production differ in secrets, `Secure` cookies, CORS origins, and who can reach the database. They share the same images and the same migrations.

## CI (M10)

GitHub Actions runs the same checks as pre-commit, plus Pytest: Ruff, mypy, and from M4 the web typecheck. A pull request is not done until that workflow is green.

## Nginx and TLS (M10)

Nginx routes `/api` to the API and the rest to the web app. TLS is explained with a local or staging certificate. The cloud target is chosen at the start of M10, not before.

## Migrations and failure (M10)

- PostgreSQL runs each Alembic revision in a transaction. A revision that raises rolls back. `alembic_version` stays on the previous revision.
- The deploy stops. The previous application version keeps running.
- Production recovery is a forward fix. Downgrade scripts are not the rollback plan.
- Schema changes use expand/contract. The expand release adds nullable columns or new tables and stays compatible with the old code. A later release contracts, after the running code no longer depends on the old shape.
- Destructive steps are not in the same release as the code that stops writing the old shape.
- Take a backup before the migration job.
- Long DDL sets a lock timeout so a stuck migration fails and rolls back instead of blocking the table.

Acceptance for this section: a revision that fails mid-upgrade leaves the schema and `alembic_version` at the previous revision, and a backup can be restored into a clean database.

## Health

`/health` answers whether the process can serve. It does not prove that every dependency is fast. M0 decides which dependencies the check includes. A load balancer should treat failure as "send traffic elsewhere," not as a full diagnosis.

## Benchmarks

Load results live in [SYSTEM_DESIGN_NOTES.md](SYSTEM_DESIGN_NOTES.md). M10 runs Locust through Nginx and compares p50, p95, p99, throughput, database time, CPU, and memory with the M4 baseline.

## Secrets

Configuration comes from the environment. Secrets are not committed. M0 introduces the settings object and a test that the process refuses to boot when a required setting is missing.
