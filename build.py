#!/usr/bin/env python3
"""Build the static website into _site/.

Inputs
  data/profile.yaml       identity, links, bio
  data/cv.yaml            curated CV (education, positions, publications, talks, ...)
  data/ui.yaml            interface strings (de/en)
  data/auto/*.json        fetched by scripts/fetch.py (ORCID, Zenodo, Bluesky, blog)
  content/projects/*.md   one Markdown file per project: <id>.md holds the front matter
                          (dates, role, links, ...) and the German text, <id>.en.md the
                          English text. Missing translations fall back to German.
  templates/              Jinja2 templates (HTML pages, plus templates/md/ for the
                          Markdown twins and llms.txt)
  static/                 css, fonts, images (copied verbatim)

Outputs (per language)
  <lang>/index.html, <lang>/projects/, <lang>/cv/, <lang>/publications/
  <lang>/index.md, <lang>/projects.md, <lang>/cv.md, <lang>/publications.md
  <lang>/julia-hintersteiner-cv-<lang>.pdf
plus /index.html (language redirect), /llms.txt, /sitemap.xml, /robots.txt, /404.html

Usage
  python build.py [--out _site] [--base /] [--theme codex] [--require-pdf] [--no-pdf]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader, pass_context, select_autoescape

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
CONTENT = ROOT / "content"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"

MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Map record types from ORCID / Zenodo to ui.yaml keys
TYPE_KEYS = {
    "journal-article": "type_journal_article",
    "conference-paper": "type_conference_paper",
    "conference-poster": "type_conference_poster",
    "software": "type_software",
    "data-set": "type_dataset",
    "dataset": "type_dataset",
    "image": "type_image",
    "presentation": "type_presentation",
    "poster": "type_poster",
    "publication": "type_publication",
    "publication/conferencepaper": "type_conference_paper",
    "publication/article": "type_journal_article",
    "lesson": "type_lesson",
    "other": "type_other",
}

# (html template, url path, nav key, markdown slug)
PAGES = [
    ("index.html", "", "nav_home", "index"),
    ("projects.html", "projects/", "nav_projects", "projects"),
    ("cv.html", "cv/", "nav_cv", "cv"),
    ("publications.html", "publications/", "nav_publications", "publications"),
]

FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.S)


# ----------------------------------------------------------------------------- helpers
def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def split_front_matter(text: str) -> tuple[dict, str]:
    m = FRONT_MATTER.match(text)
    if not m:
        return {}, text
    return (yaml.safe_load(m.group(1)) or {}), text[m.end():]


def render_markdown(text: str) -> str:
    return markdown.markdown(text, extensions=["sane_lists", "attr_list"], output_format="html5")


def load_projects(langs: list[str]) -> list[dict]:
    """Read content/projects/*.md into project dicts with body_md / body_html per language."""
    projects = []
    folder = CONTENT / "projects"
    for path in sorted(folder.glob("*.md")):
        if re.search(r"\.[a-z]{2}\.md$", path.name):
            continue  # translation file, picked up below
        meta, body = split_front_matter(path.read_text(encoding="utf-8"))
        if "id" not in meta:
            raise SystemExit(f"{path}: front matter needs an 'id'")
        default_lang = "de"
        bodies = {default_lang: body.strip()}
        for lang in langs:
            tr = folder / f"{meta['id']}.{lang}.md"
            if tr.exists():
                _, tr_body = split_front_matter(tr.read_text(encoding="utf-8"))
                bodies[lang] = tr_body.strip()
        for lang in langs:
            bodies.setdefault(lang, bodies[default_lang])
        meta["body_md"] = bodies
        meta["body_html"] = {lang: render_markdown(b) for lang, b in bodies.items()}
        meta["source"] = path.relative_to(ROOT).as_posix()
        projects.append(meta)
    projects.sort(key=lambda p: (p.get("order", 999), str(p.get("start", ""))))
    return projects


def localized(value, lang: str):
    """Pick the language variant of a {de:..., en:...} mapping; pass other values through."""
    if isinstance(value, dict) and ("de" in value or "en" in value):
        return value.get(lang) or value.get("en") or value.get("de") or ""
    return "" if value is None else value


def fmt_date(value, lang: str) -> str:
    """Format 'YYYY', 'YYYY-MM' or 'YYYY-MM-DD' (or ISO datetime) for the language."""
    if not value:
        return ""
    s = str(value)[:10]
    parts = s.split("-")
    y = parts[0]
    m = int(parts[1]) if len(parts) > 1 and parts[1] else None
    d = int(parts[2]) if len(parts) > 2 and parts[2] else None
    if lang == "de":
        if d:
            return f"{d:02d}.{m:02d}.{y}"
        if m:
            return f"{m:02d}/{y}"
        return y
    if d:
        return f"{d} {MONTHS_EN[m - 1]} {y}"
    if m:
        return f"{MONTHS_EN[m - 1]} {y}"
    return y


def norm_title(s: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").lower())


def norm_doi(s: str | None) -> str:
    s = (s or "").strip().lower()
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", s)


def titles_match(a: str, b: str) -> bool:
    if len(a) < 20 or len(b) < 20:
        return a == b
    return a.startswith(b[:30]) or b.startswith(a[:30])


# ----------------------------------------------------------------------------- publications
def curated_publication_entries(cv: dict) -> list[dict]:
    entries = []
    for cat, items in (cv.get("publications") or {}).items():
        for p in items:
            entries.append({**p, "category": cat})
    for x in cv.get("talks") or []:
        entries.append({**x, "category": "talk"})
    for x in cv.get("teaching") or []:
        entries.append({**x, "category": "teaching"})
    return entries


def merge_auto_publications(cv: dict, orcid: dict, zenodo: dict) -> list[dict]:
    """Return records from ORCID / Zenodo that are not covered by the curated CV."""
    known_dois: set[str] = set()
    known_titles: list[str] = []
    for e in curated_publication_entries(cv):
        if e.get("doi"):
            known_dois.add(norm_doi(e["doi"]))
        known_titles.append(norm_title(e.get("title")))
        for alias in e.get("aliases") or []:
            if re.match(r"^10\.\d{4,}", alias):
                known_dois.add(norm_doi(alias))
            else:
                known_titles.append(norm_title(alias))

    def is_known(dois: list[str], title: str) -> bool:
        if any(norm_doi(d) in known_dois for d in dois if d):
            return True
        nt = norm_title(title)
        return any(titles_match(nt, kt) for kt in known_titles if kt)

    merged: list[dict] = []

    def already_merged(dois: list[str], title: str) -> dict | None:
        nt = norm_title(title)
        for m in merged:
            if any(norm_doi(d) in m["dois"] for d in dois if d):
                return m
            if titles_match(nt, m["norm_title"]):
                return m
        return None

    # Zenodo first (richer: URL, creators, full date)
    for r in zenodo.get("records") or []:
        dois = [r.get("doi"), r.get("concept_doi")]
        if is_known(dois, r.get("title")) or already_merged(dois, r.get("title")):
            continue
        subtype_key = f"{r.get('type')}/{r.get('subtype')}" if r.get("subtype") else r.get("type")
        type_key = TYPE_KEYS.get(subtype_key) or TYPE_KEYS.get(r.get("type") or "") or "type_other"
        if (r.get("doi") or "").startswith("10.58079/"):  # Hypotheses blog DOI prefix
            type_key = "type_blog_post"
        merged.append(
            {
                "title": r.get("title"),
                "date": r.get("date") or "",
                "year": (r.get("date") or "")[:4],
                "type_key": type_key,
                "doi": r.get("doi"),
                "url": r.get("url"),
                "creators": r.get("creators") or [],
                "source": "Zenodo",
                "dois": {norm_doi(d) for d in dois if d},
                "norm_title": norm_title(r.get("title")),
            }
        )
    for w in orcid.get("works") or []:
        dois = w.get("dois") or []
        if is_known(dois, w.get("title")) or already_merged(dois, w.get("title")):
            continue
        date = w.get("year") or ""
        if w.get("month"):
            date += f"-{w['month']}"
        merged.append(
            {
                "title": w.get("title"),
                "date": date,
                "year": w.get("year") or "",
                "type_key": TYPE_KEYS.get(w.get("type") or "") or "type_other",
                "doi": dois[0] if dois else None,
                "url": w.get("url") or (f"https://doi.org/{dois[0]}" if dois else orcid.get("url")),
                "creators": w.get("contributors") or [],
                "journal": w.get("journal"),
                "source": "ORCID",
                "dois": {norm_doi(d) for d in dois},
                "norm_title": norm_title(w.get("title")),
            }
        )
    merged.sort(key=lambda m: m["date"], reverse=True)
    return merged


def recent_publications(cv: dict, auto: list[dict], limit: int = 4) -> list[dict]:
    items = []
    for cat, pubs in (cv.get("publications") or {}).items():
        for p in pubs:
            items.append({**p, "category": cat, "sort": f"{p.get('year', '')}-00"})
    for a in auto:
        items.append({**a, "category": "auto", "sort": a["date"] or "0000"})
    items.sort(key=lambda x: x["sort"], reverse=True)
    return items[:limit]


# ----------------------------------------------------------------------------- build
def make_env(ui: dict, text: bool = False) -> Environment:
    """HTML templates trim block-tag newlines; text (Markdown) templates control whitespace
    explicitly with `-%}` so that list lines and blank lines come out exactly as written."""
    env = Environment(
        loader=FileSystemLoader(TEMPLATES),
        autoescape=select_autoescape(["html", "xml"]),  # .md / .txt templates are not escaped
        trim_blocks=not text,
        lstrip_blocks=not text,
    )

    @pass_context
    def t_filter(ctx, value):
        return localized(value, ctx["lang"])

    @pass_context
    def date_filter(ctx, value):
        return fmt_date(value, ctx["lang"])

    @pass_context
    def period_filter(ctx, item):
        lang = ctx["lang"]
        start, end, single = item.get("start"), item.get("end"), item.get("date")
        if single:
            return fmt_date(single, lang)
        if start and end == "present":
            return f"{localized(ui['since'], lang)} {fmt_date(start, lang)}"
        if start and end:
            return f"{fmt_date(start, lang)} – {fmt_date(end, lang)}"
        if start:
            return f"{localized(ui['since'], lang)} {fmt_date(start, lang)}"
        if end:
            return f"{localized(ui['until'], lang)} {fmt_date(end, lang)}"
        return ""

    def oneline(value) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip()

    env.filters["t"] = t_filter
    env.filters["date"] = date_filter
    env.filters["period"] = period_filter
    env.filters["oneline"] = oneline
    return env


def tidy_markdown(text: str) -> str:
    """Collapse runs of blank lines left behind by template logic."""
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def build(out: Path, base: str, theme: str, pdf_mode: str) -> None:
    profile = load_yaml(DATA / "profile.yaml")
    cv = load_yaml(DATA / "cv.yaml")
    ui = load_yaml(DATA / "ui.yaml")
    langs = profile.get("languages") or ["en", "de"]
    projects = load_projects(langs)
    orcid = load_json(DATA / "auto" / "orcid.json")
    zenodo = load_json(DATA / "auto" / "zenodo.json")
    bluesky = load_json(DATA / "auto" / "bluesky.json")
    blog = load_json(DATA / "auto" / "blog.json")

    auto_pubs = merge_auto_publications(cv, orcid, zenodo)
    recent = recent_publications(cv, auto_pubs)
    build_time = datetime.now(timezone.utc)
    env = make_env(ui)
    md_env = make_env(ui, text=True)

    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    shutil.copytree(STATIC, out / "static")

    pdf_names = {lang: f"julia-hintersteiner-cv-{lang}.pdf" for lang in langs}
    common = {
        "profile": profile,
        "cv": cv,
        "ui": ui,
        "projects": projects,
        "orcid": orcid,
        "zenodo": zenodo,
        "bluesky": bluesky,
        "blog": blog,
        "auto_pubs": auto_pubs,
        "recent": recent,
        "base": base,
        "theme": theme,
        "build_time": build_time.isoformat(timespec="minutes"),
        "build_date": build_time.date().isoformat(),
        "langs": langs,
        "pdf_names": pdf_names,
        "site_url": profile["site_url"].rstrip("/"),
        "pages": PAGES,
    }

    for lang in langs:
        for template_name, path, nav_key, slug in PAGES:
            ctx = {**common, "lang": lang, "page_path": path, "nav_key": nav_key, "md_slug": slug}
            html = env.get_template(template_name).render(**ctx)
            target = out / lang / path / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(html, encoding="utf-8")
            md = md_env.get_template(f"md/{slug}.md").render(**ctx)
            (out / lang / f"{slug}.md").write_text(tidy_markdown(md), encoding="utf-8")

        # printable CV (+ PDF)
        print_html = env.get_template("cv_print.html").render(
            **common, lang=lang, page_path="cv/", nav_key="nav_cv", md_slug="cv"
        )
        (out / lang / "cv-print.html").write_text(print_html, encoding="utf-8")
        if pdf_mode != "no":
            write_pdf(print_html, out / lang / pdf_names[lang], base_url=str(out / lang) + "/", required=(pdf_mode == "require"))

    # root redirect, 404, llms.txt, sitemap, robots
    default_lang = profile.get("default_lang", "en")
    (out / "index.html").write_text(env.get_template("root.html").render(**common, lang=default_lang), encoding="utf-8")
    (out / "404.html").write_text(env.get_template("404.html").render(**common, lang="en"), encoding="utf-8")
    llms = md_env.get_template("md/llms.txt").render(**common, lang=default_lang)
    (out / "llms.txt").write_text(tidy_markdown(llms), encoding="utf-8")
    urls = [f"{common['site_url']}{base}{lang}/{path}" for lang in langs for _, path, _, _ in PAGES]
    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    sitemap += [f"  <url><loc>{u}</loc><lastmod>{common['build_date']}</lastmod></url>" for u in urls]
    sitemap.append("</urlset>\n")
    (out / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")
    (out / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {common['site_url']}{base}sitemap.xml\n", encoding="utf-8")
    (out / ".nojekyll").write_text("", encoding="utf-8")

    print(
        f"built {len(langs) * len(PAGES)} pages (+ Markdown twins, llms.txt), "
        f"{len(projects)} projects, {len(auto_pubs)} auto-imported records -> {out}"
    )


def write_pdf(html: str, target: Path, base_url: str, required: bool) -> None:
    try:
        from weasyprint import HTML  # optional dependency; needs system libraries
    except Exception as exc:  # noqa: BLE001 - missing system libs raise OSError
        msg = f"PDF skipped ({target.name}): WeasyPrint not available: {exc}"
        if required:
            raise SystemExit(msg) from exc
        print("  ! " + msg, file=sys.stderr)
        return
    HTML(string=html, base_url=base_url).write_pdf(str(target))
    print(f"  wrote {target.name}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="_site", help="output directory (default: _site)")
    ap.add_argument("--base", default="/", help="URL prefix the site is served from (default: /)")
    ap.add_argument("--theme", default="codex", help="theme name -> static/css/theme-<name>.css")
    ap.add_argument("--require-pdf", action="store_true", help="fail if the PDF cannot be generated")
    ap.add_argument("--no-pdf", action="store_true", help="skip PDF generation entirely")
    args = ap.parse_args()
    base = args.base if args.base.endswith("/") else args.base + "/"
    pdf_mode = "no" if args.no_pdf else ("require" if args.require_pdf else "try")
    build(Path(args.out).resolve(), base, args.theme, pdf_mode)


if __name__ == "__main__":
    main()
