# Learning log

Interview packs and weekly practice. Questions are attempted before the detailed answers are written here.

Each milestone pack contains:

- Practical implementation questions about the code just written.
- Backend interview questions on that milestone’s concepts.
- The system design discussion named in [ROADMAP.md](ROADMAP.md).

The DSA track is separate. It does not gate a milestone.

## Progress

| Milestone | Interview pack | System design topic |
| --- | --- | --- |
| M0 | questions posted, answers open | What `/health` should tell a load balancer, and why this product starts as a modular monolith |
| M1 | not started | Browser session design, including signed CSRF, token theft, and logout |
| M2 | not started | Tenancy model for about 100 organizations, and how isolation is tested |
| M3 | not started | Where authorization lives, and what would force ABAC |
| M4 | not started | Task-list API: indexes, pagination, and 100x data |
| M5 | not started | Notification fan-out, crash windows, and what the user observes |
| M6 | not started | Postgres full-text search versus a dedicated search engine |
| M7 | not started | Dashboard caching, invalidation, and what stays uncached |
| M8 | not started | Layered tenant isolation on a pooled connection |
| M9 | not started | SPA calling `/api/v1` directly, and what a BFF would add |
| M10 | not started | Deploy and rollback, including a failed migration and the worker |
| M11 | not started | Subscription state and webhook processing inside the monolith |
| M12 | not started | Tenant-safe retrieval, and when pgvector in Postgres is left behind |
| M13 | not started | An agent that can change data inside tenant and role limits |
| M14 | not started | Operating this monolith with jobs, traces, and admin views |

## Interview pack template

Copy this block when a milestone starts. Leave answers blank until the questions have been attempted.

### M_

#### Practical implementation

1.
2.
3.

#### Backend interview

1.
2.
3.

#### System design

Topic:

Notes after the discussion:

## Weekly practice

Target: 3–5 Python problems per week. Do not reassign a solved problem unless it is revision.

| Week | Problem | Pattern | Time | Space | Revisit |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

Order: arrays and hash maps, two pointers and sliding window, stack and queue, binary search, linked lists, trees, heaps, graphs, recursion and backtracking, then dynamic programming.

## M0

Attempt these before reading a write-up. Leave the notes blank until you have answered them.

#### Practical implementation

1. At what moment does a missing `DATABASE_URL` stop the process, and why is that earlier than the first database query?
2. Why is `GET /health` absent from `/api/v1/openapi.json`?
3. The baseline Alembic revision runs no `CREATE TABLE`. What does `alembic upgrade head` still change?

#### Backend interview

1. What is the difference between a liveness check and a readiness check?
2. Why do these tests use a real PostgreSQL server instead of a fake connection?
3. What does a load balancer do with a failed health check, and what should that check refuse to prove?

#### System design

Topic: what `/health` should tell a load balancer, and why this product starts as a modular monolith.

Notes after the discussion:

