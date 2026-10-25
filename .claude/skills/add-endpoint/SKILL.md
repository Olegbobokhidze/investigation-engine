---
name: add-endpoint
description: Add or change an HTTP endpoint end to end — contract, backend schema/service/route, errors, tests, frontend types, API hook and mocks — following the repo conventions.
argument-hint: "<METHOD> <path> — <what it does>"
---

Implement the endpoint described in `$ARGUMENTS` across both apps, contract first.

## 1. Scope and contract

- Name the assignment requirement this endpoint serves. If none, stop and ask.
- Write down the contract before any code: method, path, query params (camelCase), request
  body or multipart fields, response shape with wire names, success status, and every error
  `code` + status it can return. Check it against "Cross-app contract" in `AGENTS.md`.
- Show the contract to the user and wait for approval if it is new or changes an existing one.

## 2. Backend (`apps/api`, see `apps/api/AGENTS.md`)

1. Pydantic request/response models extending the camelCase base model.
2. Service function with the business logic — no FastAPI imports; raise `AppError`
   subclasses (add a new one with its own `code` if needed).
3. Route in `api/routes/`, thin: validate, call the service, return the model. Register the
   router in `main.py` if it is new.
4. Tests: service unit tests and a route test with `TestClient`, covering the success path
   and each documented error.

## 3. Frontend (`apps/web`, see `apps/web/AGENTS.md`)

1. Types in `features/<feature>/types.ts` matching the contract exactly.
2. Request function + TanStack Query hook in `features/<feature>/api.ts`; mutations
   invalidate affected query keys.
3. MSW handler and fixtures in `mocks/`, returning the same shapes, statuses and error codes
   as the backend.

## 4. Verify

1. `make api-check` and `make web-check` must pass.
2. Run the `contract-guardian` agent; fix any breaking or drift findings.
3. Finish with a summary of the contract and a Conventional Commit message to propose
   (e.g. `feat(api): add document upload endpoint`). Don't commit.
