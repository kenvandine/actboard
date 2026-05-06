---
description: Configure Ubuntu sponsoring-report queues to monitor (no auth required)
---

Ubuntu publishes per-team sponsoring queues as public JSON at
<http://sponsoring-reports.ubuntu.com/jsons/> — one file per team
(e.g. `ubuntu-desktop.json`, `ubuntu-rocm-dev.json`, `motu.json`,
`general.json`). Each file lists merge proposals waiting for a sponsor to
review and upload. No token needed; this command just collects which
queues the user wants triaged.

## Step 1 — list available reports

`GET http://sponsoring-reports.ubuntu.com/jsons/` returns an Apache
directory listing. Parse the `<a href="...json">...</a>` entries and
show the user the available report names (without the `.json` suffix).
Common ones: `general`, `sponsoring`, `ubuntu-desktop`, `ubuntu-server-dev`,
`ubuntu-core-dev`, `motu`, `ubuntu-rocm-dev`, `ubuntu-security-sponsors`.

## Step 2 — pick reports

Ask which queues the user wants monitored. For each, collect:

- `name` — the report name without `.json` (e.g. `ubuntu-desktop`).
- `icon` — emoji, optional (default `🧱`).
- `keywords` — list of substrings; if non-empty, only entries whose
  `source_package`, `description`, or `short_description` contains at
  least one keyword survive. Empty = keep all.
- `prompt` — short free-text description of ACT / MONITOR / HANDLED for
  this queue. Optional but strongly recommended (sponsoring queues are
  noisy, and the LLM needs to know which packages are actually theirs).
- `hide_handled` — true/false (default true).

For each report the user picks, sanity-check the name by fetching
`http://sponsoring-reports.ubuntu.com/jsons/<name>.json` — 200 with a
JSON list confirms it. 404 means the name is wrong.

## Step 3 — write config

Append each report as a list entry under `launchpad.reports` in
`triage/config.yaml`. Preserve any existing entries.

If the user wants a single keyword filter applied across **all** reports
(in addition to per-report filters), ask for the list and write it to
`launchpad.keywords`.

Set `launchpad.lookback_hours` (default 24) if they want a different
window — this controls only the `is_recent` flag on each entry; all
queued items are always included since the queue itself represents
pending work.

## Step 4 — verify

`GET http://sponsoring-reports.ubuntu.com/jsons/<one-of-their-reports>.json`
with header `User-Agent: actboard-verify`. 200 + JSON list confirms the
endpoint is reachable and the report name is valid.
