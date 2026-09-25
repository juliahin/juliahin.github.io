# {{ ui.cv_title|t }} · {{ profile.name }}, {{ profile.degrees }}

{{ profile.tagline|t }} · {{ profile.location|t }}
{% for e in profile.emails %}{{ e }} · {% endfor %}ORCID https://orcid.org/{{ profile.orcid }}
PDF: {{ site_url }}{{ base }}{{ lang }}/{{ pdf_names[lang] }}

## {{ ui.research_interests|t }}

{% for i in profile.research_interests -%}
- {{ i|t }}
{% endfor %}
## {{ ui.positions|t }}

{% for p in cv.positions -%}
- **{{ p|period }}**: {{ p.title|t }}, {{ p.institution|t }}{% if p.project %}. {{ p.project|t }}{% endif %}{% for d in p.details or [] %}
    - {{ d|t }}{% endfor %}
{% endfor %}
## {{ ui.projects|t }}

{% for p in projects -%}
- **{{ p|period }}**: {{ p.name|t }}, {{ p.role_short|t }}, {{ p.institution|t }}{% if p.funding %} ({{ p.funding|t }}){% endif %}. {{ p.links[0].url }}
{% endfor %}
{{ ui.all_projects|t }}: {{ site_url }}{{ base }}{{ lang }}/projects.md

## {{ ui.education|t }}

{% for e in cv.education -%}
- **{{ e|period }}**: {{ e.title|t }}{% if e.note %} ({{ e.note|t }}){% endif %}, {{ e.institution|t }}{% if e.thesis %}. {{ ui.thesis|t }}: „{{ e.thesis }}“{% endif %}
{% endfor %}
## {{ ui.publications|t }}

{% set h = '###' -%}
{% include 'md/_publications_body.md' %}
## {{ ui.organisation|t }}

{% for o in cv.organisation -%}
- {{ o|t }}{% if o.url %} ({{ o.url }}){% endif %}
{% endfor %}
## {{ ui.skills|t }}

{% for s in cv.skills -%}
- {{ s.label|t }}: {% for i in s['items'] %}{{ i|t }}{% if not loop.last %}, {% endif %}{% endfor %}
{% endfor %}
## {{ ui.languages|t }}

{% for l in cv.languages -%}
- {{ l.name|t }}{% if l.level|t %} ({{ l.level|t }}){% endif %}
{% endfor %}
---

{{ ui.last_updated|t }}: {{ build_date|date }} · {{ site_url }}{{ base }}{{ lang }}/cv/
