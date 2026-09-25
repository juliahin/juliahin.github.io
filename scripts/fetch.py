#!/usr/bin/env python3
"""Fetch public data for the website and store it under data/auto/.

Sources (all public, no credentials needed):
  * ORCID public API   -> data/auto/orcid.json    (works, employments, education)
  * Zenodo REST API    -> data/auto/zenodo.json   (records where Julia is a creator)
  * Bluesky public API -> data/auto/bluesky.json  (latest own posts, no replies/reposts)
  * Hypotheses RSS     -> data/auto/blog.json     (blog posts (co-)authored by Julia)

Robustness rules
  * Every request is retried (3 attempts, exponential backoff) and has a timeout.
  * A source that fails keeps its previously stored JSON.
  * A source that answers successfully but implausibly (empty list, or ORCID/Zenodo
    shrinking by more than half) is rejected and the previous JSON is kept.
  * Blog posts are merged with the stored ones, because the RSS feed only carries the
    newest ten posts of the whole blog.
  * Only http(s) URLs are kept; anything else is dropped.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
AUTO = DATA / "auto"
AUTO.mkdir(parents=True, exist_ok=True)

PROFILE = yaml.safe_load((DATA / "profile.yaml").read_text(encoding="utf-8"))
ORCID = PROFILE["orcid"]
BSKY_HANDLE = PROFILE["bluesky"]["handle"]
BLOG_FEED = PROFILE["blog"]["feed"]
BLOG_AUTHOR = PROFILE["blog"]["author_match"]
SURNAME = PROFILE["name"].split()[-1]
GIVEN = " ".join(PROFILE["name"].split()[:-1])
FULL_NAME = f"{SURNAME}, {GIVEN}".lower()

UA = {"User-Agent": f"{PROFILE['site_url']} (personal website build)"}
TIMEOUT = 30
BLOG_KEEP = 25

# The list that decides whether a fetched payload is plausible
LIST_KEY = {"orcid.json": "works", "zenodo.json": "records", "bluesky.json": "posts", "blog.json": "posts"}

SESSION = requests.Session()
SESSION.headers.update(UA)
_retry = Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
SESSION.mount("https://", HTTPAdapter(max_retries=_retry))
SESSION.mount("http://", HTTPAdapter(max_retries=_retry))


# --------------------------------------------------------------------------- helpers
def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def safe_url(value) -> str | None:
    """Return the URL if it is an absolute http(s) URL, else None."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    return value if re.match(r"^https?://[^\s]+$", value, re.I) else None


def load_previous(name: str) -> dict:
    path = AUTO / name
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def plausible(name: str, new: dict, old: dict) -> tuple[bool, str]:
    key = LIST_KEY[name]
    n_new, n_old = len(new.get(key) or []), len(old.get(key) or [])
    if n_old and n_new == 0:
        return False, f"{key} is empty (previously {n_old})"
    if name in ("orcid.json", "zenodo.json") and n_old and n_new < n_old / 2:
        return False, f"{key} shrank from {n_old} to {n_new}"
    return True, ""


def save(name: str, payload: dict) -> bool:
    old = load_previous(name)
    ok, why = plausible(name, payload, old)
    if not ok:
        print(f"  ! {name} rejected, keeping previous data: {why}", file=sys.stderr)
        return False
    payload["fetched_at"] = now_iso()
    (AUTO / name).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  wrote data/auto/{name} ({len(payload.get(LIST_KEY[name]) or [])} {LIST_KEY[name]})")
    return True


def get_json(url: str, **kw) -> dict:
    headers = {"Accept": "application/json", **kw.pop("headers", {})}
    r = SESSION.get(url, headers=headers, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


def _val(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p)
    return d if d is not None else default


# --------------------------------------------------------------------------- ORCID
def fetch_orcid() -> dict:
    base = f"https://pub.orcid.org/v3.0/{ORCID}"
    works_raw = get_json(f"{base}/works")
    works = []
    for group in works_raw.get("group", []):
        summaries = group.get("work-summary", [])
        if not summaries:
            continue
        # Prefer the summary with the most external ids (usually the richest record)
        s = max(summaries, key=lambda x: len(_val(x, "external-ids", "external-id", default=[])))
        put_code = s.get("put-code")
        detail = {}
        try:
            detail = get_json(f"{base}/work/{put_code}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ! ORCID work {put_code} detail failed: {exc}", file=sys.stderr)
        ids = _val(s, "external-ids", "external-id", default=[])
        dois = sorted({i["external-id-value"].lower() for i in ids if i.get("external-id-type") == "doi"})
        contributors = [
            _val(c, "credit-name", "value")
            for c in _val(detail, "contributors", "contributor", default=[])
            if _val(c, "credit-name", "value")
        ]
        works.append(
            {
                "put_code": put_code,
                "title": _val(s, "title", "title", "value"),
                "subtitle": _val(s, "title", "subtitle", "value"),
                "type": s.get("type"),
                "year": _val(s, "publication-date", "year", "value"),
                "month": _val(s, "publication-date", "month", "value"),
                "journal": _val(s, "journal-title", "value") or _val(detail, "journal-title", "value"),
                "dois": dois,
                "url": safe_url(_val(s, "url", "value") or _val(detail, "url", "value")),
                "contributors": contributors,
                "source": _val(s, "source", "source-name", "value"),
            }
        )
    works.sort(key=lambda w: (w["year"] or "0", w["month"] or "00"), reverse=True)

    def affiliations(section: str) -> list[dict]:
        raw = get_json(f"{base}/{section}")
        out = []
        for grp in raw.get("affiliation-group", []):
            for item in grp.get("summaries", []):
                key = next(iter(item))  # e.g. "employment-summary"
                a = item[key]

                def ymd(which: str) -> str:
                    parts = [_val(a, which, "year", "value"), _val(a, which, "month", "value")]
                    return "-".join(p for p in parts if p)

                out.append(
                    {
                        "role": a.get("role-title"),
                        "department": a.get("department-name"),
                        "organization": _val(a, "organization", "name"),
                        "city": _val(a, "organization", "address", "city"),
                        "start": ymd("start-date"),
                        "end": ymd("end-date"),
                    }
                )
        return out

    return {
        "orcid": ORCID,
        "url": f"https://orcid.org/{ORCID}",
        "works": works,
        "employments": affiliations("employments"),
        "educations": affiliations("educations"),
    }


# --------------------------------------------------------------------------- Zenodo
def fetch_zenodo() -> dict:
    api = "https://zenodo.org/api/records"
    seen: dict[str, dict] = {}
    queries = [f'creators.orcid:"{ORCID}"', f"creators.name:{SURNAME}"]
    for q in queries:
        page = 1
        while True:
            data = get_json(api, params={"q": q, "size": 25, "page": page, "sort": "mostrecent"})
            hits = data.get("hits", {}).get("hits", [])
            for h in hits:
                m = h["metadata"]
                creators = m.get("creators", [])
                mine = any(
                    c.get("orcid") == ORCID or " ".join(c.get("name", "").lower().split()) == FULL_NAME
                    for c in creators
                )
                if not mine:
                    continue
                rec_id = str(h["id"])
                if rec_id in seen:
                    continue
                rt = m.get("resource_type", {})
                seen[rec_id] = {
                    "id": rec_id,
                    "title": m.get("title"),
                    "date": m.get("publication_date"),
                    "type": rt.get("type"),
                    "subtype": rt.get("subtype"),
                    "doi": (h.get("doi") or m.get("doi") or "").lower(),
                    "concept_doi": (h.get("conceptdoi") or "").lower(),
                    "creators": [c.get("name") for c in creators],
                    "url": safe_url(h.get("links", {}).get("self_html")) or f"https://zenodo.org/records/{rec_id}",
                    "description": re.sub(r"<[^>]+>", "", m.get("description") or "")[:400],
                }
            if len(hits) < 25:
                break
            page += 1
    records = sorted(seen.values(), key=lambda r: r["date"] or "", reverse=True)
    return {"records": records}


# --------------------------------------------------------------------------- Bluesky
def _linkify_facets(text: str, facets: list[dict] | None) -> list[dict]:
    """Turn a post text + facets into a list of segments: {text, href?}. Unsafe hrefs are dropped."""
    b = text.encode("utf-8")
    spans = []
    for f in facets or []:
        idx = f.get("index", {})
        href = None
        for feat in f.get("features", []):
            t = feat.get("$type", "")
            if t.endswith("#link"):
                href = safe_url(feat.get("uri"))
            elif t.endswith("#mention") and re.match(r"^did:[a-z0-9:.%-]+$", str(feat.get("did", ""))):
                href = f"https://bsky.app/profile/{feat['did']}"
            elif t.endswith("#tag") and re.match(r"^[\w\-]+$", str(feat.get("tag", ""))):
                href = f"https://bsky.app/hashtag/{feat['tag']}"
        if href:
            spans.append((idx.get("byteStart", 0), idx.get("byteEnd", 0), href))
    spans.sort()
    segments, pos = [], 0
    for start, end, href in spans:
        if start < pos:
            continue  # overlapping facet
        if start > pos:
            segments.append({"text": b[pos:start].decode("utf-8", "ignore")})
        segments.append({"text": b[start:end].decode("utf-8", "ignore"), "href": href})
        pos = end
    if pos < len(b):
        segments.append({"text": b[pos:].decode("utf-8", "ignore")})
    return segments


def fetch_bluesky(limit: int = 6) -> dict:
    api = "https://public.api.bsky.app/xrpc"
    profile = get_json(f"{api}/app.bsky.actor.getProfile", params={"actor": BSKY_HANDLE})
    feed = get_json(
        f"{api}/app.bsky.feed.getAuthorFeed",
        params={"actor": BSKY_HANDLE, "limit": 30, "filter": "posts_no_replies"},
    )
    posts = []
    for item in feed.get("feed", []):
        if item.get("reason"):  # repost of someone else's post
            continue
        p = item["post"]
        if p["author"]["handle"] != BSKY_HANDLE:
            continue
        rec = p["record"]
        rkey = p["uri"].rsplit("/", 1)[-1]
        if not re.match(r"^[a-z0-9]+$", rkey):
            continue
        embed = p.get("embed") or {}
        external = None
        images: list[dict] = []
        et = embed.get("$type", "")
        if et.endswith("external#view"):
            ext = embed.get("external", {})
            if safe_url(ext.get("uri")):
                external = {"uri": ext["uri"], "title": ext.get("title"), "description": ext.get("description")}
        elif et.endswith("images#view"):
            images = [{"thumb": safe_url(i.get("thumb")), "alt": i.get("alt", "")} for i in embed.get("images", [])]
        elif et.endswith("recordWithMedia#view"):
            media = embed.get("media", {})
            if media.get("$type", "").endswith("images#view"):
                images = [{"thumb": safe_url(i.get("thumb")), "alt": i.get("alt", "")} for i in media.get("images", [])]
        posts.append(
            {
                "uri": p["uri"],
                "url": f"https://bsky.app/profile/{BSKY_HANDLE}/post/{rkey}",
                "created_at": rec.get("createdAt"),
                "text": rec.get("text", ""),
                "segments": _linkify_facets(rec.get("text", ""), rec.get("facets")),
                "external": external,
                "images": images,
                "likes": p.get("likeCount", 0),
                "reposts": p.get("repostCount", 0),
            }
        )
        if len(posts) >= limit:
            break
    return {
        "handle": BSKY_HANDLE,
        "did": profile.get("did"),
        "display_name": profile.get("displayName"),
        "url": f"https://bsky.app/profile/{BSKY_HANDLE}",
        "followers": profile.get("followersCount"),
        "posts_count": profile.get("postsCount"),
        "posts": posts,
    }


# --------------------------------------------------------------------------- Blog
def fetch_blog() -> dict:
    r = SESSION.get(BLOG_FEED, timeout=TIMEOUT, headers={"Accept": "application/rss+xml, application/xml, text/xml"})
    r.raise_for_status()
    parsed = feedparser.parse(r.content)
    if parsed.get("bozo") and not parsed.entries:
        raise RuntimeError(f"feed error: {parsed.get('bozo_exception')}")
    posts = []
    for e in parsed.entries:
        author = e.get("author", "") or ""
        if BLOG_AUTHOR.lower() not in author.lower():
            continue
        url = safe_url(e.get("link"))
        if not url:
            continue
        published = ""
        if e.get("published_parsed"):
            published = datetime(*e.published_parsed[:6]).date().isoformat()
        posts.append(
            {
                "title": e.get("title"),
                "url": url,
                "date": published,
                "authors": author,
                "summary": re.sub(r"<[^>]+>", "", e.get("summary", ""))[:300].strip(),
            }
        )
    # The feed only carries the newest posts of the whole blog: merge with what we already have.
    previous = load_previous("blog.json").get("posts") or []
    by_url = {p["url"]: p for p in previous}
    by_url.update({p["url"]: p for p in posts})
    merged = sorted(by_url.values(), key=lambda p: p.get("date") or "", reverse=True)[:BLOG_KEEP]
    return {"feed": BLOG_FEED, "blog_title": parsed.feed.get("title"), "posts": merged}


# --------------------------------------------------------------------------- main
def main() -> int:
    sources = {
        "orcid.json": fetch_orcid,
        "zenodo.json": fetch_zenodo,
        "bluesky.json": fetch_bluesky,
        "blog.json": fetch_blog,
    }
    failures = 0
    for name, fn in sources.items():
        print(f"fetching {name} ...")
        try:
            if not save(name, fn()):
                failures += 1
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  ! {name} failed, keeping previous data: {exc}", file=sys.stderr)
    # Only fail the job when *every* source failed (likely a network problem).
    return 1 if failures == len(sources) else 0


if __name__ == "__main__":
    sys.exit(main())
