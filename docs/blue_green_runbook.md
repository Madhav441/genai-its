# CyberNexa Blue-Green Deployment Runbook

## Purpose

This prototype runs two copies of the CyberNexa Streamlit application:

- **Blue**: the current active deployment
- **Green**: the candidate deployment

Nginx sends user traffic to one slot at a time. The inactive slot remains available for health checking before traffic is switched.

## Files

- `Dockerfile` packages the Streamlit application.
- `deploy/compose.blue-green.yml` starts Blue, Green and Nginx.
- `deploy/nginx/active.conf` identifies the currently active slot.
- `deploy/switch-slot.sh` switches traffic after validating the Nginx configuration.
- `deploy/verify-blue-green.sh` tests initial deployment, switch and rollback.
- `.github/workflows/blue-green.yml` performs the Docker validation on a GitHub-hosted Linux runner.

## Automated validation sequence

1. Build the application image.
2. Start Blue and Green.
3. Wait for both Streamlit health checks.
4. Route traffic to Blue.
5. Switch traffic to Green.
6. Verify Green remains healthy.
7. Roll back traffic to Blue.
8. Remove all temporary containers and volumes.

The Streamlit health endpoint is:

```text
/_stcore/health
```

The active slot can be checked through:

```text
/deployment-slot
```

## Local execution when Docker is available

```bash
bash deploy/verify-blue-green.sh
```

The application proxy is exposed on:

```text
http://localhost:8080
```

## Security

Real `.env`, `.streamlit/secrets.toml`, and service-account JSON files are excluded from the Docker build context. GitHub Actions validates the container infrastructure without storing production credentials.

## Evidence for A4

Use the successful **Blue-Green Deployment Validation** GitHub Actions run as evidence for:

- image build
- Blue and Green health checks
- traffic switch
- rollback
- automated cleanup
