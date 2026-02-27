# used-tempon

A Python MCP server that lets you log time to [Tempo](https://tempo.io/) (Jira time tracker) via natural language in Claude Desktop or OpenCode.

## What it does

Three MCP tools are exposed:

| Tool | Description |
|------|-------------|
| `tempo_log_time` | Log time for a date using a named preset (e.g. "usual", "sick", "vacation") |
| `tempo_get_workload` | Show expected vs. logged hours for a date |
| `tempo_get_config` | Show current configuration (token is redacted) |

Hours per day come automatically from Tempo's user schedule — respects your contracted hours, not a hardcoded 8h assumption.

## Prerequisites

- Python 3.11+
- A [Tempo Cloud](https://tempo.io/) account with API access
- A Tempo API token (see below)

## Installation

```bash
git clone https://github.com/your-username/used-tempon.git
cd used-tempon
pip install -r requirements.txt
```

## Configuration

Create `~/.tempo-config.json` (this file is **not** committed — keep it private):

```json
{
  "tempoToken": "your-tempo-api-token",
  "accountId": "your-atlassian-account-id",
  "issueIds": {
    "PROJECT-1": 10001,
    "PROJECT-2": 10002,
    "PROJECT-3": 10003,
    "PROJECT-4": 10004
  },
  "presets": {
    "usual": [
      {"issueKey": "PROJECT-1", "percentage": 50, "description": "Feature work"},
      {"issueKey": "PROJECT-2", "percentage": 50, "description": "Support"}
    ],
    "sick": [
      {"issueKey": "PROJECT-3", "percentage": 100, "description": "Sick leave"}
    ],
    "vacation": [
      {"issueKey": "PROJECT-4", "percentage": 100, "description": "Vacation"}
    ]
  }
}
```

You can also set the token via environment variable (takes precedence over the config file):
```bash
export TEMPO_TOKEN="your-tempo-api-token"
```

### How to get a Tempo API token

Go to **Tempo → Settings → API Integration**:
`https://app.tempo.io/settings/api-integration`

Generate a new token and copy it into `tempoToken` in your config file.

### How to find issue IDs

The Tempo API requires the **numeric integer issue ID**, not the string issue key (e.g. `PROJECT-123`).

To find the numeric ID for an issue:
- Call the Jira REST API: `GET /rest/api/3/issue/PROJECT-123` and look at the `id` field
- Or inspect existing Tempo worklogs via `GET https://api.tempo.io/4/worklogs` — each worklog contains `"issue": {"id": 12345, "key": "PROJECT-123"}`

### How to find your Atlassian account ID

- Visit your Jira profile page (click your avatar → Profile)
- Or call `GET /rest/api/3/myself` — the response includes `"accountId"`

## Register in Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "tempo": {
      "command": "/path/to/python3",
      "args": ["/path/to/used-tempon/mcp_server.py"]
    }
  }
}
```

Replace `/path/to/python3` with your Python 3.11+ binary (e.g. from `which python3` or `pyenv which python3`).

## Register in OpenCode

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "tempo": {
      "type": "local",
      "command": "/path/to/python3",
      "args": ["/path/to/used-tempon/mcp_server.py"]
    }
  }
}
```

Restart Claude Desktop or OpenCode after editing the config.

## Usage

Once registered, use natural language in Claude or OpenCode:

```
"log usual"                          → logs today using the "usual" preset
"log sick for yesterday"             → logs sick leave for yesterday
"log vacation for 2026-03-15"        → logs vacation for a specific date
"check my workload for today"        → shows logged vs expected hours
"what's my tempo config?"            → shows configured presets and issue mappings
"log usual for 2026-02-20 force"     → logs even if entries already exist
```

## Behaviour notes

- **Contracted hours**: Total hours come from Tempo's user schedule for that day — not hardcoded 8h
- **Preset splits**: Percentages in each preset are applied to the day's required seconds (e.g. 50/50 on a 6h45m day = 3h22m30s each)
- **Duplicate detection**: Warns if entries already exist for a date; use `force=True` to log anyway
- **Weekend/holiday guard**: Warns if Tempo says no hours are required for that day; use `force=True` to override

## File structure

```
used-tempon/
├── mcp_server.py     # FastMCP server with MCP tools
├── tempo_api.py      # Pure Tempo REST API client
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

`~/.tempo-config.json` lives outside the repo and is never committed.

## License

MIT
