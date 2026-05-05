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