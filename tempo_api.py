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


def get_user_schedule(token: str, date: str, account_id: str = "") -> dict:
    """Get the user's schedule for a single date.

    Args:
        token: Tempo API bearer token.
        date: ISO date string (YYYY-MM-DD).
        account_id: Optional Atlassian account ID. If empty, uses token owner.

    Returns:
        Dict with keys: requiredSeconds, type, date.
    """
    params = {"from": date, "to": date}
    if account_id:
        params["accountId"] = account_id
    resp = requests.get(
        f"{BASE_URL}/user-schedule",
        headers=_headers(token),
        params=params,
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



def search_jira_users(jira_base_url: str, jira_email: str, jira_token: str, query: str) -> list[dict]:
    """Search Jira users by display name.

    Args:
        jira_base_url: Jira instance base URL (e.g. "https://yourorg.atlassian.net")
        jira_email: Atlassian account email for Basic Auth
        jira_token: Jira API token for Basic Auth
        query: Name search string (e.g. "Alice")

    Returns:
        List of dicts with keys: accountId, displayName, emailAddress, active
    """
    import base64
    credentials = base64.b64encode(f"{jira_email}:{jira_token}".encode()).decode()
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }
    resp = requests.get(
        f"{jira_base_url}/rest/api/3/user/search",
        headers=headers,
        params={"query": query, "maxResults": 10},
    )
    _check_response(resp)
    return [
        {
            "accountId": u["accountId"],
            "displayName": u.get("displayName", ""),
            "emailAddress": u.get("emailAddress", ""),
            "active": u.get("active", True),
        }
        for u in resp.json()
        if u.get("accountType") == "atlassian"
    ]


if __name__ == "__main__":
    pass
