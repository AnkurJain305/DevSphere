# Debugging log

Use this when a defect is investigated. Fill it during the milestone, not only after the fix.

Scheduled exercises:

- M4 — N+1 on the task list, found from query count or database time, then fixed with a regression test.
- M8 — a trace that stops before the SQL span because a session was opened outside the instrumented path.
- M8 — a trace that dies at the outbox because `traceparent` was not copied onto the row.

## Entry template

### Date

### Milestone

### Symptom

### Layer

API, service, repository, database, worker, browser, or infrastructure.

### Reproduction

### Evidence

Logs, stack trace, query count, `EXPLAIN`, trace, or benchmark numbers.

### Hypotheses

1.

### Test of the hypothesis

### Root cause

### Fix

### Regression test

### What the first wrong guess missed
