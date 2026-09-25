# juliahin.github.io

Personal academic website of Julia Hintersteiner, published with GitHub Pages at
<https://juliahin.github.io>. Bilingual (English `/en/`, German `/de/`), with a
printable CV that is also rendered to PDF, and publication / activity lists that
refresh themselves every day from public sources.

## How it works

```
data/profile.yaml      identity, links, bio, research interests, projects   (edit by hand)
data/cv.yaml           the curated CV: positions, education, publications,
                       talks, teaching, skills, languages                    (edit by hand)
data/ui.yaml           interface strings, DE/EN                              (edit by hand)
data/projects.yaml     research projects with roles, funding, partners and links (edit by hand)
data/auto/*.json       fetched automatically – do not edit
scripts/fetch.py       pulls ORCID, Zenodo, Bluesky and the Hypotheses blog feed
build.py               renders templates/ + data/ + static/  ->  _site/
templates/             Jinja2 templates (base, index, projects, cv, publications, cv_print)
static/css             base.css + one theme file (theme-codex.css is live)
static/fonts           self-hosted Source Serif 4 / Source Sans 3 (SIL OFL 1.1)
.github/workflows      build-deploy.yml: fetch -> commit data -> build -> PDF -> deploy
```

The GitHub Actions workflow runs on every push to `main`, **daily at 05:17 UTC**, and
on demand (Actions tab -> "Build and deploy" -> Run workflow). Each run:

1. fetches the public data (`scripts/fetch.py`) and commits `data/auto/` if anything changed,
2. builds the site and the two CV PDFs (`build.py --require-pdf`, PDF via WeasyPrint),
3. deploys `_site/` to GitHub Pages.

If one source is down, its previous JSON is kept, so the site never loses content.

### Data sources

| Source | What is used | Where it appears |
| --- | --- | --- |
| ORCID public API (`0009-0008-8333-3658`) | works | publications ("Further records" for anything not in `cv.yaml`) |
| Zenodo REST API (records with this ORCID / exact name) | talks, posters, datasets, software | same as above |
| Bluesky public API (`@juliekovsky.bsky.social`) | latest own posts, no replies / reposts | home page "Latest" |
| Hypotheses RSS (`dhsalzburg.hypotheses.org`) | posts whose author field contains "Hintersteiner" | home page "Latest" |
| LinkedIn | link only (no public API) | header / contact |

Records found via ORCID or Zenodo are de-duplicated against `cv.yaml` by DOI and by
title. To move an auto-imported record into a proper category, add it to `cv.yaml`
(with its `doi`); it disappears from "Further records" on the next build. Use
`aliases:` to list further DOIs or title variants of the same work.

## Editing the CV

Everything visible comes from `data/cv.yaml` and `data/profile.yaml`. Text fields have
`de` and `en` variants; publication and talk titles are never translated. Dates are
`YYYY-MM`; `end: present` marks a current position. Values containing commas must be
quoted when written inline (`{de: "A, B", en: "A, B"}`).

The home address, birth date and the original Word CV are deliberately not in this
repository (`.gitignore`).

## Local build

```powershell
pip install -r requirements.txt
python scripts/fetch.py            # optional: refresh data/auto/
python build.py --no-pdf           # PDF needs WeasyPrint + GTK on Windows; CI builds it
python -m http.server 8000 -d _site
```

Then open <http://localhost:8000/en/>. Other themes can be previewed with
`python build.py --no-pdf --theme sidebar` or `--theme dark`; to switch the live site,
change the `--theme` default in `build.py`.

## Privacy

The site sets no cookies and makes no third-party requests: fonts are self-hosted and
Bluesky / blog content is baked into the HTML at build time.
