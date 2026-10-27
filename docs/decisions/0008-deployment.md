# ADR-0008: The API on one EC2 instance behind Caddy; the web app on Vercel

**Status:** accepted · 2026-10-26

## Context

The API loads two embedding models (dense and BM25) in memory and must stay up with HTTPS,
persistence and secrets kept out of the repository, at no cost.

## Decision

- **API:** a Docker image (`apps/api/Dockerfile`, models baked in) on an AWS EC2 t3.small in
  Stockholm (paid from AWS's new-account credits), run with Docker Compose next to Caddy, which gets and renews
  the HTTPS certificate for an `sslip.io` hostname (`apps/api/deploy/compose.yaml`).
- **Deploys:** `.github/workflows/deploy-api.yml` runs after the API's CI passes on `main`:
  build, push to GHCR, copy the compose file over SSH, restart, health check.
- **Data:** Postgres on Neon and Qdrant on Qdrant Cloud, both managed free tiers.
- **Web:** Vercel, with the API URL set as a build variable.
- **Secrets:** only in `/opt/investigation-engine/.env` on the host (mode 600) and in GitHub
  secrets for SSH; never in the repository.

## Alternatives considered

| Option | Why not |
|---|---|
| Render free tier | 512 MB memory; the API measured about 505 MB with the models loaded |
| Hugging Face Spaces (Docker) | Docker Spaces need a paid plan |
| Google Cloud Run | Needs a card hold |
| AWS Lambda | Cold starts reload the models on every scale-up |

## Evidence

The live API answers `GET /health` at https://13-53-155-129.sslip.io/health; every deploy
ends with that health check in the workflow.

## Consequences

One instance, one region, no replica: a host failure takes the API down until it is
restarted. In-memory state (the daily rate limit) resets on deploy.
