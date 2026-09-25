{% for cat, key in [('journal', 'pub_journal'), ('proceedings', 'pub_proceedings'), ('editions', 'pub_editions'), ('blog', 'pub_blog')] -%}
{% if cv.publications[cat] -%}
{{ h }} {{ ui[key]|t }}

{% for p in cv.publications[cat] -%}
- {{ p.year_label|t if p.year_label else p.year }}: {{ p.title }}{% if p.venue %}. {{ p.venue|t }}{% endif %}{% if p.coauthors %} ({{ ui.with|t }} {{ p.coauthors|join(', ') }}){% endif %}{% if p.doi %}. DOI: https://doi.org/{{ p.doi }}{% elif p.url %}. {{ p.url }}{% endif %}
{% endfor %}
{% endif -%}
{% endfor -%}
{{ h }} {{ ui.talks|t }}

{% for x in cv.talks -%}
- {{ x.date|date }}: {{ x.title }} ({{ ui['type_' ~ x.type]|t }}, {{ x.venue|t }}){% if x.coauthors %}, {{ ui.with|t }} {{ x.coauthors|join(', ') }}{% endif %}{% if x.doi %}. DOI: https://doi.org/{{ x.doi }}{% endif %}
{% endfor %}
{{ h }} {{ ui.teaching|t }}

{% for x in cv.teaching -%}
- {{ x.date|date }}: {{ x.title }} ({{ ui['type_' ~ x.type]|t }}, {{ x.venue|t }}){% if x.doi %}. DOI: https://doi.org/{{ x.doi }}{% endif %}{% if x.code %}. Code: {{ x.code }}{% endif %}
{% endfor %}
{% if auto_pubs -%}
{{ h }} {{ ui.pub_auto|t }}

{{ ui.pub_auto_note|t }}

{% for a in auto_pubs -%}
- {{ a.date|date }}: {{ a.title }} ({{ ui[a.type_key]|t }}{% if a.creators %}; {{ a.creators|join('; ') }}{% endif %}; {{ a.source }}){% if a.doi %}. DOI: https://doi.org/{{ a.doi }}{% elif a.url %}. {{ a.url }}{% endif %}
{% endfor %}
{% endif %}
