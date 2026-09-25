#!/usr/bin/env python3
"""Fetch public data for the website and store it under data/auto/.

Sources (all public, no credentials needed):
  * ORCID public API   -> data/auto/orcid.json    (works, employments, education)
  * Zenodo REST API    -> data/auto/zenodo.json   (records where Julia is a creator)
  * Bluesky public API -> data/auto/bluesky.json  (latest own posts, no replies/reposts)
  * Hypotheses RSS     -> data/auto/blog.json     (blog posts (co-)authored by Julia)

Each source is fetched independently. If a source fails, the previously stored
JSON for that source is kept, so a flaky API never empties the website.
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


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def save(name: str, payload: dict) -> None:
    payload["fetched_at"] = now_iso()
    (AUTO / name).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"  wrote data/auto/{name}")


def get_json(url: str, **kw) -> dict:
    headers = {**UA, "Accept": "application/json", **kw.pop("headers", {})}
    r = requests.get(url, headers=headers, timeout=TIMEOUT, **kw)
    r.raise_for_status()
    return r.json()


# --------------------------------------------------------------------------- ORCID
def _val(d, *path, default=None):
    for p in path:
        if not isinstance(d, dict):
            return default
        d = d.get(p)
    return d if d is not None else default


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
                "url": _val(s, "url", "value") or _val(detail, "url", "value"),
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
                    c.get("orcid") == ORCID
                    or " ".join(c.get("name", "").lower().split()) == FULL_NAME
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
                    "url": h.get("links", {}).get("self_html") or f"https://zenodo.org/records/{rec_id}",
                    "description": re.sub(r"<[^>]+>", "", m.get("description") or "")[:400],
                }
            if len(hits) < 25:
                break
            page += 1
    records = sorted(seen.values(), key=lambda r: r["date"] or "", reverse=True)
    return {"records": records}


# --------------------------------------------------------------------------- Bluesky
def _linkify_facets(text: str, facets: list[dict] | None) -> list[dict]:
    """Turn a post text + facets into a list of segments: {text, href?}."""
    b = text.encode("utf-8")
    spans = []
    for f in facets or []:
        idx = f.get("index", {})
        href = None
        for feat in f.get("features", []):
            t = feat.get("$type", "")
            if t.endswith("#link"):
                href = feat.get("uri")
            elif t.endswith("#mention"):
                href = f"https://bsky.app/profile/{feat.get('did')}"
            elif t.endswith("#tag"):
                href = f"https://bsky.app/hashtag/{feat.get('tag')}"
        if href:
            spans.append((idx.get("byteStart", 0), idx.get("byteEnd", 0), href))
    spans.sort()
    segments, pos = [], 0
    for start, end, href in spans:
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
        embed = p.get("embed") or {}
        external = None
        images: list[dict] = []
        et = embed.get("$type", "")
        if et.endswith("external#view"):
            ext = embed.get("external", {})
            external = {"uri": ext.get("uri"), "title": ext.get("title"), "description": ext.get("description")}
        elif et.endswith("images#view"):
            images = [{"thumb": i.get("thumb"), "alt": i.get("alt", "")} for i in embed.get("images", [])]
        elif et.endswith("recordWithMedia#view"):
            media = embed.get("media", {})
            if media.get("$type", "").endswith("images#view"):
                images = [{"thumb": i.get("thumb"), "alt": i.get("alt", "")} for i in media.get("images", [])]
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
    parsed = feedparser.parse(BLOG_FEED, agent=UA["User-Agent"])
    if parsed.get("bozo") and not parsed.entries:
        raise RuntimeError(f"feed error: {parsed.get('bozo_exception')}")
    posts = []
    for e in parsed.entries:
        author = e.get("author", "") or ""
        if BLOG_AUTHOR.lower() not in author.lower():
            continue
        published = ""
        if e.get("published_parsed"):
            published = datetime(*e.published_parsed[:6]).date().isoformat()
        posts.append(
            {
                "title": e.get("title"),
                "url": e.get("link"),
                "date": published,
                "authors": author,
                "summary": re.sub(r"<[^>]+>", "", e.get("summary", ""))[:300].strip(),
            }
        )
    return {"feed": BLOG_FEED, "blog_title": parsed.feed.get("title"), "posts": posts}


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
            save(name, fn())
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  ! {name} failed, keeping previous data: {exc}", file=sys.stderr)
    # Only fail the job when *every* source failed (likely a network problem).
    return 1 if failures == len(sources) else 0


if __name__ == "__main__":
    sys.exit(main())
