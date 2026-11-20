# Architecture decision records

Status of every record below: **accepted for planning**. Implementation follows the milestone named in the record. Supersede a record by adding a new one. Do not silently change the architecture.

## ADR 001 — Modular monolith

**Context.** DevSphere needs a real multi-tenant product and a place to learn request flow, data modeling, and operations. The capacity sketch is about 100 organizations.

**Decision.** One API process and one worker process, with routers, dependencies, services, and repositories separated in one codebase. Extract a process only when a milestone shows an independent scaling or failure domain. Do not adopt microservices or Kubernetes on this roadmap.

**Consequences.** Deploy, trace, and debug one application. A bad boundary is a refactor inside the repo, not a network split. The worker can still fail independently of the API because it is a separate process.

## ADR 002 — Shared schema tenancy

**Context.** Organizations must not read or write each other's rows. Schema-per-tenant and database-per-tenant isolate more strongly and cost more to migrate, connect, and back up.

**Decision.** One PostgreSQL database and one schema. Every tenant-owned row has `organization_id`. Repositories filter on it. The organization id comes from an authenticated membership on the path, not from a client-supplied filter alone.

**Consequences.** Cross-tenant tests are an acceptance gate from M2. A missing filter is a defect even when RLS exists. Operational cost stays at one database.

## ADR 003 — ARQ as the only worker runtime

**Context.** Jobs are I/O bound: notification fan-out, and later embeddings. The API is async. Celery is the vocabulary many interviews use. Running both brokers would split operations.

**Decision.** ARQ on Redis is the only worker. Map its ideas onto Celery terms when studying: queue, retry, idempotency, dead letter. Do not add Celery.

**Consequences.** One Compose service to learn. Interview answers should name the concept first and the library second. A dead letter is the `failed` outbox row, not a second product.

## ADR 004 — Sessions

**Context.** The browser needs a session. Tests and non-browser clients need a header. Refresh tokens must survive rotation and be revocable.

**Decision.** Short-lived access JWT. Refresh tokens are hashed, stored, and grouped in families. Reuse of a rotated token revokes the family. Logout revokes the current family. Password change and reset revoke every family. The browser uses an HttpOnly access cookie and an HttpOnly refresh cookie limited to the refresh and logout paths. Non-browser clients send `Authorization: Bearer`. Passwords use Argon2. Login of an unknown email still runs a verify against a dummy hash, and the response does not reveal whether the email exists. Accounts are `active` or `disabled`.

**Consequences.** Cookie clients need CSRF (ADR 007). Bearer clients do not. Stolen refresh tokens are bounded by rotation and reuse detection. Email verification uses the same one-time hashed-token design as password reset and is documented rather than built as a second flow. The dev mailer logs the reset link. No email SaaS.

## ADR 005 — PostgreSQL for search vectors

**Context.** M6 needs text search. M12 needs embeddings. A dedicated search engine or vector database is another system to operate.

**Decision.** MVP search is PostgreSQL `tsvector` with a GIN index. From M12, embeddings live in pgvector in the same database. A document chunk references its document with a tenant-safe key. Leave pgvector only when retrieval quality or scale shows this database is the limiter.

**Consequences.** One backup covers documents and vectors. Vectors are not a security boundary. Retrieval still applies organization and permission filters. Tenant isolation tests apply to search and to vectors.

## ADR 006 — Composite foreign keys

**Context.** A repository filter can be forgotten. A task row could then point at another organization's project or member.

**Decision.** Tenant parents expose `UNIQUE (organization_id, id)`. Children reference that pair, including assignee and reporter through `organization_memberships (organization_id, user_id)`, comments through tasks, optional document project, and notification recipient. Application checks still return 404 or 422. The foreign key is the backstop. M4 proves it with a direct SQL insert that must fail.

Polymorphic `activity_events` cannot foreign-key every target. Those rows are written in the same transaction as a tenant-checked parent.

**Consequences.** Writes that cross organizations fail at commit. RLS (ADR 009) does not replace these keys. A foreign key blocks a bad write. RLS blocks a forgotten filter on read.

## ADR 007 — Signed session-bound CSRF

**Context.** Cookie sessions are sent on cross-site requests. A plain double-submit token can be defeated by cookie injection: a sibling subdomain, or another cookie-tossing path, sets a cookie to a value the attacker also submits.

**Decision.** CSRF tokens are HMAC-signed with the standard library. The payload contains the refresh-token family id, issued-at, and expiry. The browser stores the signed value in a cookie and echoes it in `X-CSRF-Token`. The server accepts a cookie-authenticated mutation only when the header matches the cookie, the HMAC verifies, and the family id is the current session. Bearer requests are exempt.

Cookies are host-only (no `Domain` attribute):

| Cookie | HttpOnly | Secure | SameSite | Path | Max-Age |
| --- | --- | --- | --- | --- | --- |
| Access | yes | yes on HTTPS | Lax | `/` | access lifetime |
| Refresh | yes | yes on HTTPS | Lax | refresh and logout routes | refresh lifetime |
| CSRF | no | yes on HTTPS | Lax | `/` | access lifetime |

Local HTTP Compose may disable `Secure` through settings. That exception is documented beside the setting.

`SameSite=Lax` withholds cookies on cross-site POST in current browsers. It still sends cookies on top-level GET, it does not apply in older clients, and it treats subdomains as the same site. It is a baseline, not the control.

A script running on this origin can read the CSRF cookie and call the API with the session cookies. `HttpOnly` hides the session cookies from `document.cookie`. It does not stop `fetch` from sending them. CSRF tokens do not defend against XSS.

CORS is an origin allowlist and allows credentials only for the web origin. CORS decides which JavaScript origins may read a response. A cross-site form submit still runs on the server and still includes cookies. The CSRF check is what refuses the state change.

**Consequences.** M1 tests reject a missing header, a bad signature, and a token for another family. M4's browser can log in only after this exists. XSS remains a content problem, not a CSRF configuration problem.

## ADR 008 — Transactional outbox

**Context.** A task assignment must commit even when Redis is down, and a notification must still be delivered later. Publishing inside the database transaction is impossible. Publishing before the commit can emit an event for a write that rolls back.

**Decision.** The domain write and a `pending` outbox row commit together. After commit, enqueue to Redis. Only an enqueue acknowledgement sets `published`. The poller claims `pending` rows with `FOR UPDATE SKIP LOCKED`, sets `publishing`, `locked_until`, and a lock owner, then enqueues. Concurrent workers take different rows. An expired lock is reclaimed. The loop backs off while Redis refuses connections and continues when Redis accepts them. Rows that exhaust attempts become `failed`, keep `last_error`, and can be redriven to `pending`. They are not deleted.

The consumer inserts the notification under a unique idempotency key.

Mark-then-enqueue is rejected. The poller skips a published row. A crash or a Redis error after that mark and before a successful enqueue loses the event, because the durable row claims success and the queue has nothing. Enqueue-then-mark leaves a duplicate when the process dies after the acknowledgement and before the mark. The consumer absorbs that duplicate. A duplicate is recoverable. A published mark with no message is not.

Delivery is at-least-once. The API returns before the notification exists. Exactly-once delivery is not claimed.

**Consequences.** M5 tests every crash window: commit then crash before enqueue, enqueue error, acknowledgement then crash before mark, two workers, lock expiry, and Redis down then up. A teaching exercise shows the unsafe order dropping an event. A regression test marks `published` only after enqueue success.

## ADR 009 — Transaction-scoped RLS

**Context.** SQLAlchemy returns connections to a pool. A session-level tenant setting would still be present when the next request checks that connection out. The table owner bypasses row-level security unless it is forced, and a superuser can bypass it outright.

**Decision.** From M8, every transaction that touches tenant tables runs `SELECT set_config('app.organization_id', :org_id, true)` in that transaction. The third argument is local. The value is a bound parameter. Policies compare `organization_id` to `current_setting('app.organization_id', true)::uuid`. A missing setting matches no rows. The pool resets session state on return as a backstop. The isolation the design depends on is the local setting.

The worker has no request tenant. It sets the organization stored on the outbox event, inside that event's transaction, then commits before the next event.

Alembic uses the table owner. The API and the worker use `devsphere_app`, which is not a superuser, is not the owner, and does not have `BYPASSRLS`. Tenant tables use `ENABLE` and `FORCE ROW LEVEL SECURITY`. The app role cannot turn row security off.

The request copies W3C `traceparent` onto the outbox row. The worker continues that trace. The column exists from M5.

**Consequences.** M8 tests organization A then organization B on a pool of one connection, in the API and in the worker. It also shows the foreign key still rejecting a cross-organization write. RLS does not replace ADR 006.

## ADR 010 — URL versioning

**Decision.** Product routes are under `/api/v1`. `/health` is unversioned. OpenAPI is served for the versioned app. A breaking change is a new version, which this roadmap does not schedule.

**Consequences.** Clients and the generated TypeScript client pin a version. Health checks survive a future version bump.

## ADR 011 — Error envelope and status codes

**Decision.** Errors are `{ code, message, details }`. M8 adds `request_id`. No stack traces. Status codes: 200 read and update, 201 create, 202 password-reset request, 204 logout and empty deletes, 401 unauthenticated, 403 authenticated but not allowed, 404 hidden cross-tenant resources, 409 illegal transition or an idempotency key still in progress, 422 validation or a mismatched idempotency body, 429 rate limit from M8.

**Consequences.** Contract tests lock the envelope. Cross-tenant existence stays hidden behind 404.

## ADR 012 — API idempotency

**Context.** Clients retry creates. Outbox consumers deliver at least once. Webhooks retry.

**Decision.** Comment create accepts `Idempotency-Key`. The stored hash is SHA-256 of method, path, and canonical body. Unique `(organization_id, user_id, idempotency_key)`.

The first request commits `in_progress` before the comment transaction. A concurrent request sees that state, returns 409, and does not insert. The comment and the move to `completed`, with the stored status and body, commit together. The same hash replays that response. A different hash returns 422. A crash during `in_progress` leaves no comment. After the lease, the same key and hash may claim the row. After `expires_at`, the key executes as a new request. Expiry is enforced on the request path. No extra scheduler.

Outbox consumers use their own unique key. The M11 webhook inbox applies a verified event once.

**Consequences.** M5 includes a concurrent-request test. Idempotency state is not the outbox status. They solve different retries.

## ADR 013 — Agent confirmations

**Context.** A model can be prompted, by a user or by document text, to claim that a write was approved.

**Decision.** From M13, a write tool validates arguments, checks role and organization, and inserts `agent_confirmations` bound to the user, organization, tool name, and hash of the validated arguments. Expiry is about five minutes. `used_at` starts null. The tool result tells the model to wait and includes the confirmation id. No task exists yet.

The user confirms through an API endpoint. That transaction re-checks user, organization, tool name, expiry, and unused state, writes the task from the stored arguments, and sets `used_at`. A `confirmed` flag from the model or from document text is ignored. Modified arguments, expiry, a second use, and another user or organization write nothing. The second confirm returns 409.

The agent calls named service methods only. It does not generate SQL. Tool calls and confirmations are audited.

**Consequences.** Confirmation is a backend row, not a boolean the model can set. AI work does not start before M1–M3 have passed, and M13 also waits for M12.

## ADR 014 — Migration recovery

**Decision.** Each Alembic revision runs in a PostgreSQL transaction. A failure rolls back and leaves `alembic_version` on the previous revision. The deploy stops and the previous application keeps running. Production recovery is a forward fix. Downgrade scripts are not the rollback plan.

Changes use expand/contract. Take a backup before the migration. Long DDL sets a lock timeout.

**Consequences.** M10 includes a failed-upgrade test and a restore drill. Destructive drops wait until running code no longer reads or writes the old shape.

## ADR 015 — Locust

**Context.** M4, M7, and M10 need repeatable latency and throughput numbers. Two load tools would split the method.

**Decision.** Locust is the only load tool. Scenarios live in `benchmarks/`. k6 is the unused alternative. Record p50, p95, p99, throughput, database time, CPU, and memory. Record cache hit ratio once a cache exists. CPU and memory come from `docker stats`. Database time comes from `pg_stat_statements` when available, otherwise from `log_min_duration_statement`. No Prometheus or Grafana.

**Consequences.** Results are comparable only inside the same Compose setup. They are not production SLOs. Each benchmark milestone has an intentional bottleneck and a second run.

## ADR 016 — Git and quality gates

**Decision.** `main` stays bootable. Branches are `milestone/<id>-<short-name>`. Commit subjects are `type(scope): why` with types `feat`, `fix`, `test`, `refactor`, `docs`, `chore`. One concern per commit.

Ruff lints and formats Python. mypy typechecks the API. pre-commit runs both from M0. The web app adds `tsc --noEmit` in M4. GitHub Actions runs the same checks plus Pytest in M10. No component library unless a screen cannot be built readably without one. Contract tests are Pytest against the OpenAPI document. No Schemathesis, Dredd, or Pact.

**Consequences.** The review checklist in the README applies at the end of every milestone. Refactors with unchanged behavior are their own commits: M3 permission dependencies, M4 list query, M8 error handlers.

## ADR 017 — Local document storage

**Decision.** M6 stores bytes through a storage interface. The first driver writes under a configured root. The storage key is a server-generated id. The client filename is metadata. The driver resolves the path and refuses to write outside the root. Allowlisted types are `text/plain` and `text/markdown`, with a size limit. Object storage can replace the driver later without a new document model.

**Consequences.** M6 includes a traversal test. The interface is the extension point. A second storage product is not added now.

## ADR 018 — Generated API client

**Decision.** The web app, starting in M4, calls the API through a TypeScript client generated from OpenAPI. M9 regenerates it for the whole MVP surface. The UI is not a second contract and is not the authorization layer.

**Consequences.** Contract drift shows up when the client is regenerated. Hand-written fetch wrappers are not added beside it.

## ADR 019 — Shared Supabase Postgres for development

**Context.** Two people are building DevSphere and want one database so they see the same schema and the same rows. Each laptop still runs the API. Redis only holds disposable data later, so it stays local.

**Decision.** Development Postgres is one Supabase free-tier project, used only as Postgres. Alembic remains the owner of the schema. The app connects with `postgresql+asyncpg` over TLS to the session pooler on port 5432. The transaction pooler on port 6543 is not used. Supabase Auth, storage, and dashboard row-level security are not part of the application. `DATABASE_URL` lives in `apps/api/.env` and is not committed.

**Consequences.** Either developer can migrate or delete shared rows. Coordinate before a destructive migration. The free project pauses after inactivity. A production database is still an M10 decision. Local Compose no longer starts Postgres.
