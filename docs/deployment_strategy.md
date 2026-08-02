# CyberNexa Deployment, Release and Rollback Strategy

## 1. Purpose

This document defines the deployment, release, rollback and quality-control approach for the CyberNexa GenAI Intelligent Tutoring System.

The strategy supports:

- Reliable application releases
- Safe configuration of Ollama, Groq and OpenAI
- Automated CI quality checks
- Fast rollback when a release fails
- Protection of Firebase and API credentials
- Clear auditability and traceability through GitHub

This is the proposed deployment standard for the A4 prototype.

---

## 2. Current Architecture

The application includes:

- Streamlit user interface
- Python backend services
- Firebase authentication and database services
- Ollama for local LLM execution
- Groq and OpenAI for cloud LLM execution
- YAML-based provider configuration
- Environment-based secret management
- Request rate limiting
- Daily request and cost-budget controls
- GitHub Actions continuous integration

The default provider is configured in:

```text
config/llm_config.yaml

```

Private credentials are stored locally in:

```text
.env
.streamlit/secrets.toml
```

These files must never be committed to GitHub.

---