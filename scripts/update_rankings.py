#!/usr/bin/env python3
"""Collect OTAN player scores from the public Empire rankings API.

No game account credentials or automated gameplay are used.
If the API is unavailable or a category cannot be fully read, the existing
published snapshot is left unchanged.
"""
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "rankings.json"
API = os.environ.get("GGE_API_URL", "https://empire-api.fly.dev").rstrip("/")
SERVER = os.environ.get("GGE_SERVER", "EmpireEx_2")
ALLIANCE = os.environ.get("GGE_ALLIANCE", "OTAN").strip().casefold()
EVENT_IDS = [int(x.strip()) for x in os.environ.get("GGE_EVENTS", "40,44,46").split(",") if x.strip()]
MAX_PAGES = int(os.environ.get("GGE_MAX_PAGES", "2000"))
TIMEOUT = 25
RETRIES = 2


def get_json(url):
    for attempt in range(RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "OTAN-Imperial-Rankings/1.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
            if attempt == RETRIES:
                raise RuntimeError(f"Request failed: {url}: {exc}") from exc
            time.sleep(2 * (attempt + 1))


def ranking_url(event_id, category_id, search_rank):
    params = f'"LT":{event_id},"LID":{category_id},"SV":"{search_rank}"'
    return f"{API}/{SERVER}/hgh/{urllib.parse.quote(params, safe=':,')}"


def parse_player(row, offset):
    if not isinstance(row, list) or len(row) <= offset + 2:
        raise ValueError("Unexpected player row")
    details = row[offset + 2]
    if not isinstance(details, dict) or "N" not in details or "AN" not in details:
        raise ValueError("Player name or alliance missing")
    rank, points = row[offset], row[offset + 1]
    if not isinstance(rank, int) or not isinstance(points, (int, float)):
        raise ValueError("Rank or points invalid")
    return {"name": str(details["N"]), "alliance": str(details["AN"]), "points": int(points), "source_rank": rank}


def collect_category(event_id, category, offset):
    cid = category["id"]
    found = {}
    search_rank = 1
    last_rank = None
    seen = set()
    for page in range(MAX_PAGES):
        payload = get_json(ranking_url(category.get("eventid", event_id), cid, search_rank))
        if str(payload.get("return_code")) != "0":
            raise RuntimeError(f"API returned failure for event {event_id}, category {cid}")
        content = payload.get("content")
        if not isinstance(content, dict) or not isinstance(content.get("L"), list):
            raise RuntimeError("Malformed ranking response")
        rows = content["L"]
        if not rows:
            if last_rank is None or search_rank > last_rank:
                return found
            raise RuntimeError("Unexpected empty ranking page")
        last_rank = int(content["LR"])
        parsed = [parse_player(row, offset) for row in rows]
        ranks = [p["source_rank"] for p in parsed]
        if ranks != sorted(ranks):
            raise RuntimeError("Unsorted ranking page")
        for p in parsed:
            if p["alliance"].strip().casefold() == ALLIANCE:
                found[p["name"].casefold()] = p
        max_rank = max(ranks)
        if max_rank >= last_rank:
            return found
        if max_rank in seen or max_rank < search_rank:
            raise RuntimeError("Pagination did not advance")
        seen.add(max_rank)
        search_rank = max_rank + 1
        time.sleep(0.15)
    raise RuntimeError(f"Exceeded page safety limit in category {cid}")


def main():
    assets = get_json("https://raw.githubusercontent.com/danadum/ggs-assets/main/gge/events.json")
    definitions = assets.get("player", {})
    events = {}
    for event_id in EVENT_IDS:
        matches = [(name, spec) for name, spec in definitions.items() if spec.get("id") == event_id and not spec.get("global")]
        if len(matches) != 1:
            raise RuntimeError(f"Event {event_id} not uniquely defined")
        name, spec = matches[0]
        offset = int(spec.get("offset", 0)) - int(spec.get("nopoints", 0))
        if spec.get("nopoints"):
            raise RuntimeError(f"Event {event_id} does not have points")
        if not spec.get("categories"):
            raise RuntimeError(f"Event {event_id} has no categories")
        combined = {}
        for category in spec["categories"]:
            print(f"Scanning event {event_id}, category {category['id']}", flush=True)
            combined.update(collect_category(event_id, category, offset))
        players = sorted(combined.values(), key=lambda p: (-p["points"], p["name"].casefold()))
        events[str(event_id)] = {"name": name.replace("_", " ").title(), "players": players}
        print(f"Event {event_id}: {len(players)} OTAN players", flush=True)
    if not events:
        raise RuntimeError("No events processed")
    snapshot = {"updated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "server": SERVER, "events": events}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temp = OUTPUT.with_suffix(".tmp")
    temp.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(OUTPUT)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Collection failed; preserving previous data: {exc}", file=sys.stderr)
        sys.exit(1)
