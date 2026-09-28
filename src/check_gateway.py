"""Inspect local gateway settings without network calls or credential output."""

import json
from dataclasses import replace

from src.core.config import Settings


def configuration_report(settings=None):
    settings = settings or Settings()
    missing = [
        name
        for name, value in (
            ("LLM_GATEWAY_URL", settings.gateway_url),
            ("LLM_GATEWAY_API_KEY", settings.gateway_api_key),
            ("LLM_MODEL", settings.model),
        )
        if not value.strip()
    ]
    errors = []
    try:
        settings.validate()
        replace(settings, mode="gateway").validate()
    except ValueError as exc:
        # Settings.validate only emits fixed setting names, never input values.
        errors.append(str(exc))
    valid_protocol = settings.gateway_protocol in {"ollama", "openclaw"}
    return {
        "status": "blocked" if missing or errors else "configured_not_live_verified",
        "mode": settings.mode if settings.mode in {"demo", "gateway"} else "invalid",
        "protocol": settings.gateway_protocol if valid_protocol else "invalid",
        "endpoint_path": settings.gateway_endpoint_path if valid_protocol else None,
        "missing_settings": missing,
        "errors": errors,
        "network_requests": 0,
        "live_verified": False,
        "limits": (
            "Local configuration only. Does not verify reachability, authentication, "
            "model output, or remote agent tool permissions. See OPENCLAW.md before live use."
        ),
    }


def main():
    report = configuration_report()
    print(json.dumps(report, indent=2))
    return 2 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
