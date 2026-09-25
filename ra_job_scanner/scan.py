#!/usr/bin/env python3
"""
RA/Research Associate job scanner for Dhaka-based institutes and CSE departments.

Checks each URL in sites.json for text matching keywords (Research Assistant /
Research Associate / etc). When a page's content changes AND still contains a
keyword match, it's included in an email digest sent to the configured address.

Usage:
    python scan.py            # normal run: check sites, email digest if anything new
    python scan.py --dry-run  # check sites, print what WOULD be emailed, send nothing
    python scan.py --force    # ignore stored hashes, treat every keyword match as new
"""
import argparse
import hashlib
import json
import re
import smtplib
import sys
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

import requests
from bs4 import BeautifulSoup

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
SITES_FILE = BASE_DIR / "sites.json"
CONFIG_FILE = BASE_DIR / "config.json"
STATE_FILE = BASE_DIR / "state.json"
LOG_FILE = BASE_DIR / "scan_log.txt"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
}
REQUEST_TIMEOUT = 25
SNIPPET_RADIUS = 120
MAX_SNIPPETS_PER_SITE = 3


def log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] {msg}"
    print(line)
    with LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(line + "\n")


def load_json(path: Path, required: bool = True):
    if not path.exists():
        if required:
            raise FileNotFoundError(
                f"{path.name} not found. Copy config.example.json to config.json "
                f"and fill in your details." if path == CONFIG_FILE else f"{path} not found."
            )
        return None
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def fetch_text(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def find_snippets(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    hits = []
    seen_spans = []
    for kw in keywords:
        for m in re.finditer(re.escape(kw.lower()), lower):
            start, end = m.start(), m.end()
            if any(abs(start - s) < SNIPPET_RADIUS for s, _ in seen_spans):
                continue
            seen_spans.append((start, end))
            snip_start = max(0, start - SNIPPET_RADIUS)
            snip_end = min(len(text), end + SNIPPET_RADIUS)
            snippet = text[snip_start:snip_end].replace("\n", " ").strip()
            hits.append(snippet)
    return hits[:MAX_SNIPPETS_PER_SITE]


SCAN_LABEL = "RA/Research job scan"


def send_digest_email(config: dict, results: list[dict], is_first_run: bool) -> None:
    subject = (
        f"{SCAN_LABEL}: initial baseline"
        if is_first_run
        else f"{SCAN_LABEL}: {len(results)} site(s) with updates"
    )
    lines = []
    if is_first_run:
        lines.append(
            "First run - this is a baseline of everything currently matching your "
            "keywords on the watched pages. Future emails will only cover NEW changes.\n"
        )
    for r in results:
        lines.append(f"=== {r['name']} ===")
        lines.append(r["url"])
        for snip in r["snippets"]:
            lines.append(f"  - ...{snip}...")
        lines.append("")
    body = "\n".join(lines)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = config["gmail_address"]
    msg["To"] = config["to_email"]

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
        server.login(config["gmail_address"], config["gmail_app_password"])
        server.sendmail(config["gmail_address"], [config["to_email"]], msg.as_string())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Don't send email, just print")
    parser.add_argument("--force", action="store_true", help="Treat all keyword matches as new")
    args = parser.parse_args()

    sites_cfg = load_json(SITES_FILE)
    keywords = sites_cfg["keywords"]
    sites = sites_cfg["sites"]

    state = load_json(STATE_FILE, required=False) or {}
    is_first_run = not STATE_FILE.exists()

    results = []
    new_state = dict(state)

    for site in sites:
        name, url = site["name"], site["url"]
        try:
            text = fetch_text(url)
        except Exception as e:
            log(f"FAILED  {name} ({url}): {e}")
            continue

        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        prev = state.get(url, {})
        changed = args.force or prev.get("hash") != content_hash

        snippets = find_snippets(text, keywords) if changed else []
        if snippets:
            results.append({"name": name, "url": url, "snippets": snippets})
            log(f"MATCH   {name}: {len(snippets)} snippet(s)")
        else:
            log(f"OK      {name}: no new keyword matches" if changed else f"OK      {name}: unchanged")

        new_state[url] = {
            "hash": content_hash,
            "last_checked": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }

    STATE_FILE.write_text(json.dumps(new_state, indent=2), encoding="utf-8")

    if not results:
        log("No new matches this run. No email sent.")
        return

    if args.dry_run:
        log(f"[DRY RUN] Would email {len(results)} result(s):")
        for r in results:
            print(f"\n=== {r['name']} ===\n{r['url']}")
            for s in r["snippets"]:
                print(f"  - ...{s}...")
        return

    config = load_json(CONFIG_FILE)
    send_digest_email(config, results, is_first_run)
    log(f"Emailed digest with {len(results)} site(s) to {config['to_email']}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL: {e}")
    finally:
        if getattr(sys, "frozen", False):
            input("\nPress Enter to close this window...")
