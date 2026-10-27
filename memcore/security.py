"""Security utilities for secret redaction, safe content handling, and policy protection."""

import re
from typing import List, Tuple

# Common patterns for API keys, tokens, passwords, private keys
SECRET_PATTERNS = [
    # AWS Access Key
    (re.compile(r'(?i)(AKIA[0-9A-Z]{16})'), "[REDACTED_AWS_ACCESS_KEY]"),
    # Generic Bearer Token
    (re.compile(r'(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})'), "Bearer [REDACTED_BEARER_TOKEN]"),
    # Generic Private Key
    (re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----'), "[REDACTED_PRIVATE_KEY]"),
    # GitHub Token (classic & fine-grained)
    (re.compile(r'(gh[pousr]_[A-Za-z0-9_]{36,255})'), "[REDACTED_GITHUB_TOKEN]"),
    # OpenAI API Key
    (re.compile(r'(sk-[a-zA-Z0-9]{20,T3BlbkFJ[a-zA-Z0-9]{20,}|sk-proj-[a-zA-Z0-9_\-]{40,})'), "[REDACTED_OPENAI_KEY]"),
    # Generic API Key / Secret assignments
    (re.compile(r'(?i)(api[_-]?key|secret|password|passwd|auth_token)\s*[:=]\s*["\']([^"\'\s]{8,})["\']'), r'\1="[REDACTED_SECRET]"'),
    # Database connection strings with passwords
    (re.compile(r'(postgres|mysql|mongodb|redis)://([^:]+):([^@]+)@'), r'\1://\2:[REDACTED_PASSWORD]@'),
]


def redact_secrets(text: str) -> Tuple[str, bool]:
    """Redacts secrets from input text.
    
    Returns:
        (sanitized_text, was_redacted)
    """
    if not text:
        return text, False
        
    sanitized = text
    redacted = False
    for pattern, replacement in SECRET_PATTERNS:
        new_text = pattern.sub(replacement, sanitized)
        if new_text != sanitized:
            redacted = True
            sanitized = new_text
            
    return sanitized, redacted


def sanitize_untrusted_input(text: str) -> str:
    """Sanitizes untrusted text to ensure no control injection occurs in system context."""
    if not text:
        return ""
    # Strip dangerous null bytes or non-printable controls except standard whitespace
    cleaned = "".join(ch for ch in text if ch == '\n' or ch == '\t' or ch == '\r' or ord(ch) >= 32)
    return cleaned
