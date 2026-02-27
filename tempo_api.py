"""Pure Python client for the Tempo REST API v4."""

import requests

BASE_URL = "https://api.tempo.io/4"


class TempoAPIError(Exception):
    """Raised when the Tempo API returns a non-2xx response."""


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _check_response(resp: requests.Response) -> None:
    if not resp.ok:
        raise TempoAPIError(f"Tempo API error {resp.status_code}: {resp.text}")


def get_user_schedule(token: str, date: str) -> dict:
    """Get the user's schedule for a single date.

    Args:
        token: Tempo API bearer token.
        date: ISO date string (YYYY-MM-DD).

    Returns:
        Dict with keys: requiredSeconds, type, date.
    """
    resp = requests.get(
        f"{BASE_URL}/user-schedule",
        headers=_headers(token),
        params={"from": date, "to": date},
    )
    _check_response(resp)
    return resp.json()["results"][0]


def create_worklog(
    token: str,
    account_id: str,
    issue_id: int,
    seconds: int,
    date: str,
    description: str,
) -> dict:
    """Create a worklog entry in Tempo.

    Args:
        token: Tempo API bearer token.
        account_id: Jira/Atlassian account ID of the author.
        issue_id: Jira issue ID (integer, NOT the issue key string).
        seconds: Time spent in seconds.
        date: ISO date string (YYYY-MM-DD).
        description: Worklog description text.

    Returns:
        Full worklog response dict from the API.
    """
    payload = {
        "authorAccountId": account_id,
        "issueId": issue_id,
        "timeSpentSeconds": seconds,
        "startDate": date,
        "startTime": "08:00:00",
        "description": description,
    }
    resp = requests.post(
        f"{BASE_URL}/worklogs",
        headers=_headers(token),
        json=payload,
    )
    _check_response(resp)
    return resp.json()


def get_worklogs_for_date(token: str, account_id: str, date: str) -> list[dict]:
    """Get all worklogs for a specific user on a specific date.

    Args:
        token: Tempo API bearer token.
        account_id: Jira/Atlassian account ID to filter by.
        date: ISO date string (YYYY-MM-DD).

    Returns:
        List of worklog dicts with keys: tempoWorklogId, issue, timeSpentSeconds,
        startDate, description, author.
    """
    resp = requests.get(
        f"{BASE_URL}/worklogs",
        headers=_headers(token),
        params={"from": date, "to": date},
    )
    _check_response(resp)
    results = resp.json().get("results", [])
    return [
        wl for wl in results if wl.get("author", {}).get("accountId") == account_id
    ]


if __name__ == "__main__":
    pass
