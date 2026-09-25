#!/usr/bin/env python3
"""Check every http(s) link in the hand-written content and report broken ones.

Scans content/**/*.md, data/profile.yaml, data/cv.yaml, data/ui.yaml and README.md
(not data/auto/, which is machine-generated). Writes a Markdown report to
link-report.md and exits 1 if any link is broken.

Status handling
  2xx / 3xx        ok
  403, 429         "blocked": the server refuses automated requests (common for
                   publishers and DOI targets); reported as a warning, not a failure
  other / errors   broken
"""
from __future__ import annotations

import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent.parent
SOURCES = [
    *sorted((ROOT / "content").rglob("*.md")),
    ROOT / "data" / "profile.yaml",
    ROOT / "data" / "cv.yaml",
    ROOT / "data" / "ui.yaml",
    ROOT / "README.md",
]
URL_RE = re.compile(r"https?://[^\s<>\"'()\[\]{}]+")
SKIP_HOSTS = ("localhost", "127.0.0.1")
BLOCKED = {403, 429, 999}  # 999 is LinkedIn's answer to any automated request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}


def collect() -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for path in SOURCES:
        if not path.exists():
            continue
        for m in URL_RE.finditer(path.read_text(encoding="utf-8")):
            url = m.group(0).rstrip(".,;:")
            if any(host in url.split("/")[2] for host in SKIP_HOSTS):
                continue
            found.setdefault(url, set()).add(path.relative_to(ROOT).as_posix())
    return found


def make_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=1.5, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET", "HEAD"])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.mount("http://", HTTPAdapter(max_retries=retry))
    s.headers.update(HEADERS)
    return s


def check(session: requests.Session, url: str) -> tuple[str, int | None, str]:
    try:
        r = session.get(url, timeout=30, allow_redirects=True, stream=True)
        r.close()
        return url, r.status_code, r.url
    except requests.RequestException as exc:
        return url, None, type(exc).__name__


def main() -> int:
    found = collect()
    session = make_session()
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(lambda u: check(session, u), sorted(found)))

    broken, blocked, ok = [], [], 0
    for url, status, info in results:
        if status is not None and 200 <= status < 400:
            ok += 1
        elif status in BLOCKED:
            blocked.append((url, status))
        else:
            broken.append((url, status, info))

    lines = [f"# Link check: {len(found)} links, {ok} ok, {len(blocked)} blocked, {len(broken)} broken", ""]
    if broken:
        lines.append("## Broken")
        lines.append("")
        for url, status, info in broken:
            where = ", ".join(sorted(found[url]))
            lines.append(f"- {url} → {status if status is not None else info} (in {where})")
        lines.append("")
    if blocked:
        lines.append("## Blocked for automated requests (verify by hand if unsure)")
        lines.append("")
        for url, status in blocked:
            lines.append(f"- {url} → {status}")
        lines.append("")
    report = "\n".join(lines)
    (ROOT / "link-report.md").write_text(report + "\n", encoding="utf-8")
    print(report)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
