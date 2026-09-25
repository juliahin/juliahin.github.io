# {{ ui.projects_title|t }} · {{ profile.name }}

{{ ui.projects_intro|t }}

{% for p in projects -%}
## {{ p.name|t }}

- {{ ui.period|t }}: {{ p|period }}{% if p.period_note %} ({{ p.period_note|t }}){% endif %}
- {{ ui.role|t }}: {{ p.role|t }}
- {{ ui.institution|t }}: {{ p.institution|t }}{% if p.lead %}; {{ p.lead|t }}{% endif %}
{% if p.funding -%}
- {{ ui.funding|t }}: {{ p.funding|t }}
{% endif -%}
{% if p.partners -%}
- {{ ui.partners|t }}: {{ p.partners|t }}
{% endif %}
{{ p.body_md[lang] }}

### {{ ui.links|t }}

{% for l in p.links -%}
- {{ ui['link_' ~ l.kind]|t }}: [{{ l.label|t }}]({{ l.url }})
{% endfor %}
{% if p.subprojects -%}
### {{ ui.subprojects|t }}

{% for s in p.subprojects -%}
- **{{ s.name|t }}** ({{ s|period }}{% if s.funding %}; {{ ui.funding|t }}: {{ s.funding|t }}{% endif %}). {{ s.summary|t|oneline }} {% for l in s.links %}[{{ l.label|t }}]({{ l.url }}){% if not loop.last %}, {% endif %}{% endfor %}
{% endfor %}
{% endif -%}
{% endfor %}
---

{{ ui.last_updated|t }}: {{ build_date|date }} · {{ site_url }}{{ base }}{{ lang }}/projects/
