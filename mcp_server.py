#!/usr/bin/env python3
"""Tempo MCP Server - log time to Tempo via simple commands."""

import json
import os
from datetime import date, timedelta
from typing import Optional
from mcp.server.fastmcp import FastMCP
import tempo_api

mcp = FastMCP("tempo")


def load_config() -> dict:
    """Load Tempo configuration from ~/.tempo-config.json."""
    config_path = os.path.expanduser("~/.tempo-config.json")
    if not os.path.exists(config_path):
        raise RuntimeError(
            "Config file not found: ~/.tempo-config.json. "
            "Please create it. See README for instructions."
        )
    with open(config_path) as f:
        config = json.load(f)
    if "tempoToken" not in config:
        raise RuntimeError(
            "Missing 'tempoToken' in config. Get a token at: "
            "https://app.tempo.io/settings/api-integration"
        )
    # Environment variable override
    env_token = os.environ.get("TEMPO_TOKEN")
    if env_token:
        config["tempoToken"] = env_token
    return config


try:
    CONFIG = load_config()
except (FileNotFoundError, RuntimeError, json.JSONDecodeError) as e:
    CONFIG = None
    _CONFIG_ERROR = str(e)
else:
    _CONFIG_ERROR = None


def parse_date(d: Optional[str]) -> str:
    """Parse human-friendly date strings to ISO format.

    Args:
        d: Date string - "today", "yesterday", "", None, or YYYY-MM-DD.

    Returns:
        ISO date string (YYYY-MM-DD).
    """
    if not d or d == "today":
        return date.today().isoformat()
    if d == "yesterday":
        return (date.today() - timedelta(days=1)).isoformat()
    return d


@mcp.tool()
def tempo_log_time(
    type: str,
    date: str = "today",
    description: str = "",
    force: bool = False,
) -> str:
    """Log time to Tempo using a named preset.

    Presets define how hours are split across Jira issues (e.g. "usual" splits
    50/50 between CAPEX and OPEX). The total hours come from Tempo's schedule.

    Args:
        type: Preset name (e.g. "usual", "sick", "sick_kid", "vacation").
        date: Date to log for - "today", "yesterday", or YYYY-MM-DD.
        description: Override the default description for all entries.
        force: If True, log even on weekends/holidays or when entries already exist.

    Returns:
        Summary of logged worklogs or an error message.
    """
    if _CONFIG_ERROR:
        return f"❌ Configuration error: {_CONFIG_ERROR}"

    token = CONFIG["tempoToken"]
    account_id = CONFIG["accountId"]
    presets = CONFIG.get("presets", {})
    parsed_date = parse_date(date)

    # Validate preset
    if type not in presets:
        return f"❌ Unknown preset '{type}'. Available: {list(presets.keys())}"

    try:
        # Check required hours
        schedule = tempo_api.get_user_schedule(token, parsed_date)
        required_seconds = schedule.get("requiredSeconds", 0)

        if required_seconds == 0 and not force:
            return (
                f"⚠️ No required hours for {parsed_date} (weekend or holiday). "
                "Use force=True to log anyway."
            )

        # Check existing worklogs
        existing = tempo_api.get_worklogs_for_date(token, account_id, parsed_date)
        if existing and not force:
            return (
                f"⚠️ Already logged {len(existing)} worklog(s) for {parsed_date}. "
                "Use force=True to log anyway."
            )

        # Log each entry in the preset
        preset_entries = presets[type]
        logged = []
        for entry in preset_entries:
            seconds = int(required_seconds * entry["percentage"] / 100)
            issue_id = CONFIG["issueIds"][entry["issueKey"]]
            desc = description or entry["description"]
            result = tempo_api.create_worklog(
                token, account_id, issue_id, seconds, parsed_date, desc
            )
            hours = seconds / 3600
            logged.append(
                f"  • {entry['issueKey']} ({desc}): {hours}h "
                f"[ID: {result.get('tempoWorklogId', '?')}]"
            )

        total_hours = required_seconds / 3600
        summary = f"✅ Logged {total_hours}h for {parsed_date}:\n" + "\n".join(logged)
        return summary

    except tempo_api.TempoAPIError as e:
        return f"❌ Tempo API error: {e}"


@mcp.tool()
def tempo_get_workload(date: str = "today") -> str:
    """Show logged time vs expected hours for a date.

    Use this to check if a day is fully logged or see what's missing.

    Args:
        date: Date to check - "today", "yesterday", or YYYY-MM-DD.

    Returns:
        Formatted workload summary with expected hours, logged entries, and status.
    """
    if _CONFIG_ERROR:
        return f"❌ Configuration error: {_CONFIG_ERROR}"

    token = CONFIG["tempoToken"]
    account_id = CONFIG["accountId"]
    parsed_date = parse_date(date)

    try:
        # Get schedule
        schedule = tempo_api.get_user_schedule(token, parsed_date)
        required_seconds = schedule.get("requiredSeconds", 0)
        day_type = schedule.get("type", "UNKNOWN")
        expected_hours = required_seconds / 3600

        # Get existing worklogs
        worklogs = tempo_api.get_worklogs_for_date(token, account_id, parsed_date)

        lines = [
            f"📅 {parsed_date} ({day_type})",
            f"Expected: {expected_hours}h ({required_seconds}s)",
            "",
        ]

        if worklogs:
            total_logged = 0
            lines.append(f"Logged ({len(worklogs)} entries):")
            for wl in worklogs:
                seconds = wl.get("timeSpentSeconds", 0)
                total_logged += seconds
                hours = seconds / 3600
                issue_id = wl.get("issue", {}).get("id")
                issue_ids = CONFIG.get("issueIds", {})
                reverse = {v: k for k, v in issue_ids.items()}
                issue_key = reverse.get(issue_id, f"id:{issue_id}")
                desc = wl.get("description", "")
                lines.append(f"  • {issue_key}: {hours}h — \"{desc}\"")
            total_hours = total_logged / 3600
            lines.append(f"Total logged: {total_hours}h")
            lines.append("")
            if total_logged >= required_seconds:
                lines.append("Status: ✅ Fully logged")
            else:
                remaining = (required_seconds - total_logged) / 3600
                lines.append(f"Status: ⚠️ {remaining}h remaining")
        else:
            lines.append("No worklogs yet.")

        return "\n".join(lines)

    except tempo_api.TempoAPIError as e:
        return f"❌ Tempo API error: {e}"


@mcp.tool()
def tempo_get_config() -> str:
    """Show current Tempo configuration (token is redacted).

    Use this to verify which presets, issue mappings, and account settings
    are configured.

    Returns:
        Formatted configuration summary with redacted token.
    """
    if _CONFIG_ERROR:
        return (
            f"❌ Configuration error: {_CONFIG_ERROR}\n\n"
            "To set up, create ~/.tempo-config.json with:\n"
            "  tempoToken, accountId, baseUrl, issueIds, presets\n"
            "See README for full instructions."
        )

    # Redact token - show only last 4 chars
    token = CONFIG.get("tempoToken", "")
    if len(token) > 4:
        redacted = f"****{token[-4:]}"
    else:
        redacted = "****"

    lines = [
        "⚙️ Tempo Configuration",
        f"  Token: {redacted}",
        f"  Account ID: {CONFIG.get('accountId', '?')}",
        f"  Base URL: {CONFIG.get('baseUrl', tempo_api.BASE_URL)}",
        "",
        "Issue Mappings:",
    ]
    for key, issue_id in CONFIG.get("issueIds", {}).items():
        lines.append(f"  {key} → {issue_id}")

    lines.append("")
    lines.append("Presets:")
    for name, entries in CONFIG.get("presets", {}).items():
        entry_parts = [
            f"{e['issueKey']} ({e['percentage']}%)" for e in entries
        ]
        lines.append(f"  {name}: {', '.join(entry_parts)}")

    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
