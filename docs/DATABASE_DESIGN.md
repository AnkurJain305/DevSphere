# Database design

No tables exist yet. This document is the schema the milestones will migrate. Query plans for the task list are filled in at M4. Row-level security is added in M8 and does not replace the foreign keys below.

## Roles

| Role | Used by | Privileges |
| --- | --- | --- |
| Table owner | Alembic | Owns tables. Not used by the API or the worker. |
| `devsphere_app` | API and worker, from M8 | DML only. Not a superuser. `rolbypassrls = false`. Cannot disable row security. |

Until M8, the local development role may own the tables. M8 splits the roles and turns on `ENABLE ROW LEVEL SECURITY` and `FORCE ROW LEVEL SECURITY` for tenant tables.

## Identity

### `users`

Email, password hash (Argon2), status (`active`, `disabled`).

### `password_reset_tokens`

User, hashed token, expiry, used time. Single use. Requesting a reset always returns 202, including for an unknown email.

### `refresh_tokens`

User, family id, hashed token, expiry, revoked time. Rotation writes a new row in the same family. Reuse of a rotated token revokes the family.

## Tenancy

### `organizations`

Name, slug.

### `organization_memberships`

User, organization, role (`owner`, `admin`, `member`, `viewer`). Unique `(organization_id, user_id)`. That unique pair is the target of later composite foreign keys. A duplicate membership fails in the database.

The creator of an organization is `owner`. An admin cannot remove an owner. The last owner cannot leave.

## Projects and tasks (M4)

### `projects`

Organization, name, status. Unique `(organization_id, id)`.

### `tasks`

Organization, project, title, status, priority, assignee, reporter, due date. Unique `(organization_id, id)`.

Status moves `todo` → `in_progress` → `done`, and may become `cancelled`. An illegal transition is 409.

`organization_id` is denormalized onto the task so lists and policies can filter without joining through the project. The composite foreign key below keeps that column honest.

## Collaboration (M5)

### `task_comments`

Organization, task, author, body.

### `activity_events`

Organization, actor, entity type, entity id, action, JSON payload. Append-only. Written in the same transaction as the tenant-checked parent.

This table is polymorphic, so PostgreSQL cannot foreign-key every target. That limitation is accepted. Comments, tasks, documents, and notifications use real composite foreign keys instead.

### `notifications`

Organization, recipient, type, read time, consumer idempotency key. Unique on the consumer key so a duplicate outbox delivery inserts one row.

### `outbox_events`

Organization, type, payload, consumer idempotency key, status (`pending`, `publishing`, `published`, `failed`), attempts, available time, lock deadline, lock owner, published time, last error, W3C `traceparent`.

The trace column exists in M5 and is filled in M8.

Index for the poller: unpublished rows by availability. The claim is `FOR UPDATE SKIP LOCKED`.

### `idempotency_keys`

Organization, user, client key, request hash (SHA-256 of method, path, and canonical body), status (`in_progress`, `completed`), stored status code and body, expiry.

Unique `(organization_id, user_id, idempotency_key)`.

## Documents (M6)

### `documents`

Organization, optional project, title, text body, storage key. The storage key is a server-generated id. The client filename is metadata only and is never joined onto the storage root.

Full-text search uses `tsvector` and a GIN index on documents and tasks.

## Later tables

Not migrated until their milestone.

| Milestone | Tables |
| --- | --- |
| M11 | `plans`, `subscriptions`, `webhook_events` |
| M12 | `document_chunks` with a pgvector column, referencing the document with a tenant-safe key |
| M13 | `agent_conversations`, `agent_messages`, `agent_tool_calls`, `agent_confirmations` |

`agent_confirmations` stores user, organization, tool name, validated argument hash, expiry, and used time.

## Composite foreign keys

Parents that other tenant rows point at carry `UNIQUE (organization_id, id)`. Children reference that pair. A task for organization A cannot store a project id or member id that exists only in organization B. The insert fails even if application code forgets the check. The service still checks first so callers get 404 or 422.

- `tasks (organization_id, project_id)` → `projects (organization_id, id)`
- `tasks (organization_id, assignee_id)` → `organization_memberships (organization_id, user_id)` when the assignee is set
- `tasks (organization_id, reporter_id)` → `organization_memberships (organization_id, user_id)`
- `task_comments (organization_id, task_id)` → `tasks (organization_id, id)`
- `task_comments (organization_id, author_id)` → `organization_memberships (organization_id, user_id)`
- `documents (organization_id, project_id)` → `projects (organization_id, id)` when the project is set
- `notifications (organization_id, recipient_id)` → `organization_memberships (organization_id, user_id)`

M4 demonstrates the cross-organization failure with a direct SQL insert.

```sql
-- Shape, not a migration. Parents expose the pair. Children reference it.
ALTER TABLE projects
  ADD CONSTRAINT projects_org_id_key UNIQUE (organization_id, id);

ALTER TABLE tasks
  ADD CONSTRAINT tasks_project_same_org
  FOREIGN KEY (organization_id, project_id)
  REFERENCES projects (organization_id, id);
```

## Indexes called out during design

- Unique membership `(organization_id, user_id)`.
- Tasks by `(organization_id, status, updated_at)`.
- Tasks by `(assignee_id, status)`.
- Activity by `(organization_id, created_at)`.
- GIN full-text on documents and tasks (M6).
- Outbox unpublished rows by availability (M5).

Further indexes wait for a query plan. M4 writes the task-list `EXPLAIN` here.

## Task list query plan (M4)

Not measured yet.

| Query | Plan | Index used | Notes |
| --- | --- | --- | --- |
| List tasks for an organization | | | Filled after the N+1 fix |

## Row-level security (M8)

Policies compare `organization_id` to `current_setting('app.organization_id', true)::uuid`.

The setting is applied inside the transaction:

```sql
SELECT set_config('app.organization_id', :org_id, true);
```

The third argument is `SET LOCAL`. The value is a bound parameter. It disappears at commit or rollback, so the next checkout of a pooled connection does not inherit a tenant. A missing setting matches no rows.

The API and the worker connect as `devsphere_app`. The table owner is reserved for Alembic. `FORCE ROW LEVEL SECURITY` keeps the owner from silently bypassing policies if a connection is misconfigured. The application role does not have `BYPASSRLS` and cannot set `row_security` off.

Workers call `set_config` once per event, using the `organization_id` stored on that outbox row.

RLS does not replace the composite foreign keys. One test shows the foreign key rejecting a cross-organization write. Another shows RLS hiding a row when the application filter is omitted. A third uses a pool of one connection: organization A, then organization B, in the API and in the worker.
