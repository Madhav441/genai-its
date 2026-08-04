# CyberNexa Project Context & Architecture Guidelines

## 1. Project Overview
We are building CyberNexa: a decoupled, secure, and governable GenAI tutoring framework. It is built in Python using Streamlit for the frontend. It is NOT a standard chatbot; it strictly enforces Bounded Prompt Contracts and Institutional Data Sovereignty.

## 2. My Role & Task
I am Ronan, the Lead Architect. My current task is building the "Input Sanitisation and Prompt Injection Defence" middleware (OWASP LLM-01 mitigation) and hooking it into the existing UI.

## 3. Strict Development Rules (CRITICAL)
*   **Zero-Impact Integration:** This is a group project. Do NOT rewrite, refactor, or alter existing UI components, state management, or routing created by other team members. Only inject the `InputSanitizer` exactly where the user input is captured.
*   **Human-Readable Code:** Write clean, straightforward Python. Do not use overly clever list comprehensions, complex decorators, or "AI-style" code. Use standard, brief inline comments to explain *why* something is happening, not *what*.
*   **Decoupled Middleware:** Security logic must live in `middleware/input_sanitizer.py`. 
*   **Secondary LLM Gate:** All user inputs must be intercepted and evaluated by a lightweight Gemini model before touching the main AI engine. It must return strict JSON: `{"is_safe": bool, "reason": str}`.
*   **Visible Governance:** If an attack is blocked, use Streamlit's `st.error` to display a visible Red Banner warning. Do not fail silently.
*   **Dependency Management:** If a new package is required (like `google-genai`), remind me to add it to `requirements.txt`.