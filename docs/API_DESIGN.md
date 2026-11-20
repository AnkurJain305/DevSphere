# API design

Product routes live under `/api/v1`. `/health` stays unversioned so a load balancer does not depend on a product version. A breaking change would be a new version. This roadmap does not need one.

Per-route request and response bodies are filled in during the milestone that adds the route. This document holds the rules those routes must follow. FastAPI publishes the OpenAPI document. A contract test fails if a shipped route, status code, or error shape is missing from it.

No routes are implemented yet.

## Error envelope

```json
{
  "code": "string",
  "message": "string",
  "details": []
}
```

M8 adds `request_id`. Responses do not include stack traces.

## Status codes

| Code | When |
| --- | --- |
| 200 | Read and update |
| 201 | Create |
| 202 | Password-reset request, for known and unknown emails |
| 204 | Logout and deletes with no body |
| 401 | Missing, expired, or revoked authentication |
| 403 | Authenticated, but not allowed |
| 404 | Hidden cross-tenant resource, and other missing resources |
| 409 | Illegal state transition, idempotency key still `in_progress`, confirmation already used |
| 422 | Validation, or an idempotency key reused with a different body |
| 429 | Rate limit, from M8 |

Cross-tenant reads stay 404 so the caller cannot learn that the other organization's row exists.

## Lists

Filters and sort fields are allowlisted. Unknown fields are rejected. The task list uses keyset pagination with a stable id tie-break. Offset pagination is discussed for the interview and is not used for that list.

## Idempotency (M5)

`Idempotency-Key` on comment create.

- Unique per organization, user, and key.
- Request hash is SHA-256 of method, path, and canonical body.
- The first request commits `in_progress` before the comment transaction. A concurrent request with the same key receives 409 and does not insert.
- The comment and the move to `completed`, including the stored status and body, commit together. A later retry with the same hash replays that response.
- The same key with a different hash returns 422.
- A crash after the `in_progress` commit leaves no comment. After the lease, the same key and hash may claim the row again.
- After `expires_at`, a completed key executes as a new request. Expiry is checked on the request path.

Outbox consumers use a separate unique key on the notification. Webhook inbox in M11 follows the same once-only rule after the signature check.

## Authentication sketch (M1)

| Method | Path | Result |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | 201, or 422 |
| POST | `/api/v1/auth/login` | Sets cookies. Unknown emails still pay an Argon2 verify. The body does not reveal whether the email exists. |
| POST | `/api/v1/auth/refresh` | Rotates the refresh family. Reuse revokes the family. |
| POST | `/api/v1/auth/logout` | 204. Revokes the current family. |
| POST | `/api/v1/auth/password-reset` | 202 always |
| POST | `/api/v1/auth/password-reset/confirm` | Sets the password and revokes every family. The token works once. |

Cookie-authenticated mutations require `X-CSRF-Token`. Bearer calls do not. Cookie names and flags are specified in [DECISIONS.md](DECISIONS.md) (ADR 007).

## Resource sketch

Contracts are added in the milestone column. Paths are the intended shape.

| Milestone | Resources | Notes |
| --- | --- | --- |
| M0 | `GET /health` | Unversioned. OpenAPI at `/api/v1/openapi.json`. |
| M2 | `/api/v1/orgs`, memberships, invites | Invite row is the product. No email provider. |
| M3 | Membership role changes | Permission checks in dependencies. |
| M4 | `/api/v1/orgs/{org_id}/projects`, `.../tasks` | Filters, sort, keyset pagination, status transitions. |
| M5 | `.../comments`, activity, notifications | `Idempotency-Key` on comment create. |
| M6 | `.../documents`, search | Upload type and size limits. Storage key is server-generated. |
| M7 | `.../dashboard` | Counts match the tables. |
| M8 | Existing routes | Request id on errors. 429 on login rate limit. |
| M11 | `/api/v1/billing`, webhook inbox | Signature verified before the body is trusted. |
| M13 | Assistant messages, `POST` confirm | Confirmation id is server-issued. A model `confirmed` flag is ignored. |
| M14 | Operator admin routes | Denied to organization owners. |

## CORS

Allowlist from settings. Credentials are allowed only for the web origin. A disallowed `Origin` is rejected. CORS does not replace the CSRF check. See ADR 007.
