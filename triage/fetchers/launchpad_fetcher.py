"""Ubuntu sponsoring-reports fetcher — public JSON, no auth required.

Each report at http://sponsoring-reports.ubuntu.com/jsons/<name>.json is a
list of merge proposals waiting for review by a given Ubuntu sponsor team
(e.g. ubuntu-desktop, ubuntu-rocm-dev, motu, general)."""

import sys
from datetime import datetime, timedelta, timezone

import requests

LP_BASE = "http://sponsoring-reports.ubuntu.com/jsons"
USER_AGENT = "ActBoard Triage Bot 1.0"


def _parse_queued(date_str: str) -> datetime | None:
    """Reports use MM/DD/YY in date_queued/date_created."""
    if not date_str:
        return None
    for fmt in ("%m/%d/%y", "%d/%m/%y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _matches_keywords(item: dict, keywords: list[str]) -> bool:
    text = " ".join([
        item.get("source_package", ""),
        item.get("description", ""),
        item.get("short_description", ""),
    ]).lower()
    return any(kw in text for kw in keywords)


def _fetch_report(session: requests.Session, name: str) -> list[dict]:
    url = f"{LP_BASE}/{name}.json"
    resp = session.get(url, timeout=30)
    if resp.status_code != 200:
        print(f"  [launchpad] {url} returned {resp.status_code}", file=sys.stderr)
        return []
    try:
        data = resp.json()
    except ValueError:
        print(f"  [launchpad] {url} returned invalid JSON", file=sys.stderr)
        return []
    if not isinstance(data, list):
        return []
    return data


def fetch_launchpad(config: dict) -> dict:
    """
    Fetch Ubuntu sponsoring queues. Returns: {"lp/<report>": [items]}.
    Each item is a merge proposal awaiting sponsor review.
    """
    lp_cfg = config.get("launchpad")
    if not lp_cfg:
        return {}

    reports = lp_cfg.get("reports", [])
    if not reports:
        return {}

    lookback = lp_cfg.get("lookback_hours", 24)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback)

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    global_keywords = [k.lower() for k in lp_cfg.get("keywords", [])]

    results = {}
    for rep_cfg in reports:
        name = rep_cfg["name"]
        per_keywords = [k.lower() for k in rep_cfg.get("keywords", [])]
        all_keywords = global_keywords + per_keywords

        print(f"  Scanning launchpad/{name}...")
        raw = _fetch_report(session, name)

        items = []
        for entry in raw:
            queued = _parse_queued(entry.get("date_queued") or entry.get("date_created", ""))
            is_recent = bool(queued and queued >= cutoff)
            items.append({
                "source_package": entry.get("source_package", ""),
                "description": entry.get("description", ""),
                "short_description": entry.get("short_description", ""),
                "link": entry.get("link", ""),
                "components": entry.get("components", []),
                "sets": entry.get("sets", []),
                "severity": entry.get("severity", ""),
                "s_types": entry.get("s_types", []),
                "date_queued": entry.get("date_queued", ""),
                "date_created": entry.get("date_created", ""),
                "is_recent": is_recent,
            })

        if all_keywords:
            filtered = [it for it in items if _matches_keywords(it, all_keywords)]
            print(f"    launchpad/{name}: {len(filtered)}/{len(items)} entries matched keywords")
        else:
            filtered = items
            print(f"    launchpad/{name}: {len(filtered)} entries")
        results[f"lp/{name}"] = filtered

    return results
