# {{ profile.name }}, {{ profile.degrees }}

{{ profile.tagline|t }} · {{ profile.location|t }}

{{ profile.intro|t|oneline }}

## {{ ui.current_roles|t }}

{% for r in profile.current_roles -%}
- **{{ r.title|t }}**, [{{ r.org|t }}]({{ r.url }})
{% endfor %}
## {{ ui.research_interests|t }}

{% for i in profile.research_interests -%}
- {{ i|t }}
{% endfor %}
## {{ ui.projects|t }}

{% for p in projects -%}
- **{{ p.name|t }}** ({{ p|period }}, {{ p.role_short|t }}): {{ p.teaser|t|oneline }} {% for l in p.links[:2] %}[{{ l.label|t }}]({{ l.url }}){% if not loop.last %}, {% endif %}{% endfor %}
{% endfor %}
[{{ ui.all_projects|t }}]({{ site_url }}{{ base }}{{ lang }}/projects.md)

## {{ ui.latest_posts|t }}

{% for p in bluesky.posts[:3] -%}
- {{ p.created_at|date }}: {{ p.text|oneline }} ([{{ ui.view_on_bluesky|t }}]({{ p.url }}))
{% endfor %}
[{{ ui.follow_on_bluesky|t }}](https://bsky.app/profile/{{ profile.bluesky.handle }})

## {{ ui.latest_blog|t }}

{% for p in blog.posts[:3] -%}
- {{ p.date|date }}: [{{ p.title }}]({{ p.url }}) ({{ p.authors }})
{% endfor %}
## {{ ui.latest_publications|t }}

{% for p in recent -%}
{% if p.category == 'auto' -%}
- {{ p.date|date }}: {{ p.title }} ({{ ui[p.type_key]|t }}{% if p.creators %}; {{ p.creators|join('; ') }}{% endif %}){% if p.doi %}. DOI: https://doi.org/{{ p.doi }}{% elif p.url %}. {{ p.url }}{% endif %}
{% else -%}
- {{ p.year_label|t if p.year_label else p.year }}: {{ p.title }}{% if p.venue %}. {{ p.venue|t }}{% endif %}{% if p.coauthors %} ({{ ui.with|t }} {{ p.coauthors|join(', ') }}){% endif %}{% if p.doi %}. DOI: https://doi.org/{{ p.doi }}{% elif p.url %}. {{ p.url }}{% endif %}
{% endif -%}
{% endfor %}
[{{ ui.all_publications|t }}]({{ site_url }}{{ base }}{{ lang }}/publications.md)

## {{ ui.contact|t }}

{% for e in profile.emails -%}
- {{ ui.email|t }}: {{ e }}
{% endfor -%}
- ORCID: https://orcid.org/{{ profile.orcid }}
- Bluesky: https://bsky.app/profile/{{ profile.bluesky.handle }}
- LinkedIn: {{ profile.linkedin }}
- GitHub: https://github.com/{{ profile.github }}

---

{{ ui.data_sources|t }} {{ ui.last_updated|t }}: {{ build_date|date }}. HTML: {{ site_url }}{{ base }}{{ lang }}/
