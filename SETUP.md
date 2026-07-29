# CyberNexa / GenAI ITS Setup Guide

## 1. Requirements

- Python 3.11 or newer
- Git (recommended)
- A Groq API key **or** a locally running Ollama instance
- Firebase service-account configuration

## 2. Create the local environment

### Windows Command Prompt

```bat
1.0_env_setup\setup_env.bat
```

### Windows PowerShell

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\1.0_env_setup\setup_env.ps1
```

The scripts create `.venv`, install `requirements.txt`, and validate the safe example configuration templates.

## 3. Add private configuration

Create the two local secret files. They are already excluded by `.gitignore`.

```powershell
Copy-Item .env.example .env
Copy-Item .streamlit\secrets.example.toml .streamlit\secrets.toml
```

Edit `.env` and select a provider:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_real_key
```

For Ollama:

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

Then replace the placeholders in `.streamlit/secrets.toml` with the Firebase service-account values.

## 4. Validate configuration

```powershell
python 1.5_security/config_validator.py
```

The validator reports missing or invalid settings without printing secret values.

## 5. Run the prototype

```powershell
streamlit run 1.1_interface/streamlit_app.py
```

Open the local URL displayed by Streamlit, normally `http://localhost:8501`.

## 6. Test model switching

Change only this setting in `.env`:

```env
LLM_PROVIDER=groq
```

or:

```env
LLM_PROVIDER=ollama
```

Restart Streamlit after changing the provider. The application code does not need to be edited.

## 7. Rate limiting and budget protection

The prototype reads these values from `.env`:

```env
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=10
RATE_LIMIT_WINDOW_SECONDS=60
LLM_DAILY_REQUEST_LIMIT=250
```

These controls protect the prototype from excessive calls and provide a basic daily request budget. The current counters are stored in application memory, which is suitable for the A4 prototype. A production multi-server deployment should use a shared store such as Redis or Firestore.

## 8. Common problems

- **GROQ_API_KEY missing:** add the key to `.env` and restart the app.
- **Ollama connection error:** start Ollama and confirm `OLLAMA_BASE_URL` and `OLLAMA_MODEL`.
- **Firebase error:** verify the `[FIREBASE]` section in `.streamlit/secrets.toml`.
- **Request limit reached:** wait for the configured time window or ask the administrator to change the limit.
