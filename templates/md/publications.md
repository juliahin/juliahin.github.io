# {{ ui.publications|t }} · {{ profile.name }}

{{ ui.data_sources|t }} ORCID: https://orcid.org/{{ profile.orcid }}

{% set h = '##' -%}
{% include 'md/_publications_body.md' %}
---

{{ ui.last_updated|t }}: {{ build_date|date }} · {{ site_url }}{{ base }}{{ lang }}/publications/
