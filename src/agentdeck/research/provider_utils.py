"""Shared helpers for provider inference across research tooling."""

from __future__ import annotations


def provider_from_module(module: str) -> str:
    """Infer provider name from a fully qualified module path."""
    module_lower = (module or "").lower()
    if "openai" in module_lower:
        return "openai"
    if "anthropic" in module_lower:
        return "anthropic"
    if "google" in module_lower:
        return "google"
    if "mock" in module_lower:
        return "mock"
    return "unknown"
