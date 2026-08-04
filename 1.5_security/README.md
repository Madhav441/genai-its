# Module 5: Audit & Observability

Owner: Sujal Kumar  
Project: CyberNexa / GenAI ITS  
Branch: sujal-audit-observability

## Purpose

This module provides audit logging and observability support for the CyberNexa GenAI Intelligent Tutoring System.

The audit logger records important system, security, and AI interaction events in a structured format. These logs can support incident response, compliance review, debugging, and future dashboard monitoring.

## Design Principles Supported

This module supports:

- DP3: Bounded Prompt Contracts
- DP4: Institutional Data Sovereignty
- DP8: Prompt Engineering as Pedagogy

Audit logging helps make system behaviour more transparent without exposing sensitive student data, prompts, answer keys, or credentials.

## Current Implementation

The current implementation is located in:

`1.5_security/audit_logger.py`

At this stage, the logger writes audit events locally to:

`logs/audit_logs.jsonl`

The `logs/` folder is excluded from Git using `.gitignore` because runtime audit logs may contain sensitive or temporary development data.

## Audit Event Structure

Each audit event follows this structure:

- `event_id`
- `timestamp`
- `event_type`
- `severity`
- `user_id`
- `session_id`
- `source_module`
- `message`
- `metadata`

This structure is designed to work locally during development and later map cleanly into Firestore.

## Supported Event Types

The logger currently supports:

- `auth_attempt`
- `rbac_check`
- `input_sanitisation_flag`
- `output_guardrail_trigger`
- `rate_limit_hit`
- `llm_api_call`
- `quiz_state_change`
- `prompt_template_change`
- `contract_violation`
- `system_error`

## Supported Severity Levels

The logger supports:

- `INFO`
- `WARNING`
- `ERROR`
- `CRITICAL`

## Privacy and Metadata Sanitisation

Audit logs should not expose sensitive student or system information. The logger automatically redacts sensitive metadata fields before writing them to log output.

The following fields are redacted if found in metadata:

- `password`
- `api_key`
- `secret`
- `token`
- `private_key`
- `raw_prompt`
- `full_prompt`
- `student_answer`
- `rubric`
- `answer_key`

If a sensitive field is found, its value is replaced with:

`[REDACTED]`

Long metadata values are also truncated to reduce accidental over-logging.

## Firestore Preparation

Firestore has been manually prepared in the CyberNexa Firebase project.

A collection has been created called:

`audit_logs`

A manual test document has also been added to confirm the intended structure. The Firestore document uses the same fields as the local audit logger:

- `event_id`
- `timestamp`
- `event_type`
- `severity`
- `user_id`
- `session_id`
- `source_module`
- `message`
- `metadata`

At this stage, Firestore integration is not yet hardcoded into the logger. This is intentional because the logger should continue working locally even if Firebase credentials are not available.

## Testing

Automated tests are located in:

`tests/test_audit_logger.py`

Run the tests with:

python3 -m pytest tests/test_audit_logger.py

## Sprint 3 Progress

The audit logger now supports optional Firestore storage using the `audit_logs` collection.

Each event is first written to the local JSONL audit file. The same sanitised event is then written to Firestore when the database connection is enabled. If Firestore is unavailable, the local audit record remains available as a fallback.

A controlled `contract_violation` event was successfully written to the live Firestore database. The event represented a prompt-injection attempt and included information such as the event type, severity, source module and guardrail result. The original prompt was replaced with `[REDACTED]` before storage.

### Testing Status

* 7 core audit logger tests passed.
* 5 mocked Firestore integration tests passed.
* 12 tests passed in total.
* Live Firestore writing was verified manually.
* Local fallback behaviour was tested.

### Red-Team Testing Preparation

A red-team testing plan has been prepared for the following scenarios:

* Prompt injection
* System-prompt extraction
* Answer-key extraction
* Rubric leakage
* Role bypass
* Rate-limit abuse
* Malicious file instructions
* Unsafe cybersecurity requests

Each scenario has been mapped to an expected system response, audit-event type, severity level and responsible module.

### Current Limitation

The controlled prompt-injection event demonstrates that the audit logging and Firestore storage pipeline works.

It does not yet represent a complete end-to-end attack passing through the real CyberNexa AI Gate. Full testing requires the AI Gate, rate limiter, file validator, output guardrails and access-control components to be combined into one shared integration branch.

### Next Step

Once a shared integration branch is confirmed, the red-team scenarios can be converted into automated Pytest cases that send controlled attacks into the real system and verify that they are blocked, sanitised and logged correctly.

## Runtime Audit Integration

The audit logger is connected to the real rate limiter and LLM wrapper.

It automatically records:

- `rate_limit_hit` when an enforced limit is exceeded
- `llm_api_call` after a successful model request
- `system_error` when an LLM provider request fails

Audit events contain operational metadata only. API keys, raw prompts, student answers, rubrics, answer keys and model response content are not logged.

Runtime events are stored locally in `logs/audit_logs.jsonl`.

To watch the audit log while using the application:

    tail -f logs/audit_logs.jsonl

Run the project tests with:

    python3 -m pytest tests -q

At the time of integration, all 35 tests passed.

### RT-06 Rate-Limit Abuse Test

The RT-06 demonstration sends repeated requests through the real rate limiter, confirms that the excessive request is blocked, creates a genuine `rate_limit_hit` event and verifies the event in the Firestore `audit_logs_test` collection.

Run it with:

    python3 1.5_security/rt06_rate_limit_firestore_demo.py

RT-06 is currently the completed end-to-end red-team scenario. Other scenarios require their relevant controls, including the AI Gate, output guardrails, access control and file validation.
