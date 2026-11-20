# DevSphere

DevSphere is a multi-tenant workspace for engineering teams and a hands-on backend learning program. Organizations manage projects, tasks, documents, and activity. Later milestones add billing and a permission-aware assistant.

The goal is to understand each engineering decision: tenancy, authorization, data modeling, jobs, search, production operation, then agents. Backend depth stays ahead of UI polish.

M0 is in progress. The API boots locally, and PostgreSQL is a shared Supabase database. These documents are the current source of truth:

- [docs/ROADMAP.md](docs/ROADMAP.md) — milestones, dependencies, timeline, and the progress checklist
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — modular monolith, request path, tenancy, outbox
- [docs/DATABASE_DESIGN.md](docs/DATABASE_DESIGN.md) — entities, composite foreign keys, RLS planned for M8
- [docs/API_DESIGN.md](docs/API_DESIGN.md) — versioning, errors, status codes, pagination, idempotency
- [docs/DECISIONS.md](docs/DECISIONS.md) — architecture decision records
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — local shape now; production steps reserved for M10
- [docs/SYSTEM_DESIGN_NOTES.md](docs/SYSTEM_DESIGN_NOTES.md) — capacity sketch and benchmark placeholders
- [docs/LEARNING_LOG.md](docs/LEARNING_LOG.md) — interview packs and weekly practice
- [docs/DEBUGGING_LOG.md](docs/DEBUGGING_LOG.md) — debugging write-ups
- [Plan.md](Plan.md) — the mentoring brief

## How the program runs

Work proceeds one milestone at a time. Each milestone follows the same cycle: requirements, design, implementation, tests, debugging, performance, then interview questions. The milestone stops until its acceptance criteria in the roadmap are met.

One vertical slice of each milestone is implemented by the learner first. The review comes after that attempt.

A separate practice track runs in parallel: 3–5 Python problems per week, logged in [docs/LEARNING_LOG.md](docs/LEARNING_LOG.md). It does not gate a milestone. Notes live in `practice/` once that directory exists. Order: arrays and hash maps, two pointers and sliding window, stack and queue, binary search, linked lists, trees, heaps, graphs, recursion and backtracking, then dynamic programming. Each note states the pattern, time, and space. Solved problems are not reassigned unless they are useful revision.

Pace assumption: 8–12 hours per week, about 27–33 weeks for M0 through M14.

## Git

These rules apply from the first implementation commit:

- `main` stays bootable.
- Work happens on `milestone/<id>-<short-name>` (example: `milestone/m1-sessions`).
- Commit subject: `type(scope): why`.
- Types: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`.
- One concern per commit. Formatting-only changes are their own commit.

Review checklist at the end of every milestone:

- Tenant filter present on new tenant queries.
- Composite foreign keys on new tenant references.
- Authorization on the route.
- Error envelope used.
- Tests cover the failure case.
- No unrelated drive-by edits.

Quality gates, introduced in M0 and repeated in CI at M10: Ruff, mypy, and pre-commit. The web app adds `tsc --noEmit` in M4.

## What is in and out

MVP (M0–M9): register, reset a password, create an organization, invite a member, manage projects and tasks, comment, see in-app notifications, store documents, search inside the tenant, and view a dashboard. Functional screens start in M4 and finish in M9.

Production (M10–M11): Nginx, CI, deploy, backups, a load baseline, and a separate billing module.

AI (M12–M14): retrieval, a tool-calling assistant, evals, and an operator view. This slice waits until authentication, tenant isolation, and authorization have passed their acceptance criteria.

Out of this roadmap: microservices, Kubernetes, multi-region, SSO/SAML, WebSockets, a dedicated search engine, a dedicated vector database, mobile apps, Slack, fine-grained ABAC, and a second job system.

## Boot

Compose runs the API and Redis on your machine. PostgreSQL is one shared Supabase database, so both developers see the same schema and the same rows. Redis stays local because it will only hold disposable cache and queue data.

Create a free Supabase project and copy the **session** connection string (host `pooler.supabase.com`, port **5432**). Do not use port 6543. That port is the transaction pooler, and it breaks Alembic and later `SET LOCAL`. Put the string in `apps/api/.env`, using the shape in `apps/api/.env.example`. The scheme must be `postgresql+asyncpg`. Share that file through a password manager. It is gitignored.

Supabase is used only as Postgres. Its Auth service, storage, and dashboard row-level security stay off. This project builds those itself.

From the repository root, after `.env` exists:

```powershell
docker compose -f infra/compose.yaml up --build -d
docker compose -f infra/compose.yaml run --rm api python -m alembic upgrade head
```

Then open `http://localhost:8000/health`. The product contract is `http://localhost:8000/api/v1/openapi.json`. Product docs are at `http://localhost:8000/api/v1/docs`.

The free project is enough for this stage: 500 MB and a project that sleeps after about a week without traffic. Wake it from the Supabase dashboard if connections start failing. Do not reset the database from the dashboard while the other person is using it.

Tests read the same `.env`:

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest
```

Install the git hooks once the repository has a git checkout:

```powershell
cd apps/api
.\.venv\Scripts\pre-commit.exe install
.\.venv\Scripts\pre-commit.exe run --all-files
```

Stop the stack with `docker compose -f infra/compose.yaml down`. Add `-v` only when you intend to delete the database volume.
