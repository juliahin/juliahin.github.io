---
id: mhdbdb
order: 1
name: {de: "Mittelhochdeutsche Begriffsdatenbank (MHDBDB)", en: "Middle High German Conceptual Database (MHDBDB)"}
start: 2023-11
end: present
role: {de: "Senior Scientist (seit 11/2023, mit Unterbrechungen)", en: "Senior Scientist (since Nov 2023, with interruptions)"}
role_short: {de: "Senior Scientist", en: "Senior Scientist"}
institution: {de: "Fachbereich Germanistik, Universität Salzburg", en: "Department of German Studies, University of Salzburg"}
funding: {de: "Universität Salzburg; Teilprojekte gefördert durch CLARIAH-AT (BMFWF)", en: "University of Salzburg; sub-projects funded by CLARIAH-AT (BMFWF)"}
teaser:
  de: "Forschungsinfrastruktur zur mittelhochdeutschen Sprache und Literatur. Migration des gesamten Datenbestands von RDF zu TEI, Relaunch der Plattform, offene Daten auf GitHub und Zenodo."
  en: "Research infrastructure for Middle High German language and literature. Migration of the entire data set from RDF to TEI, platform relaunch, open data on GitHub and Zenodo."
links:
  - {kind: website, label: "mhdbdb.plus.ac.at", url: "https://mhdbdb.plus.ac.at/"}
  - {kind: website, label: "MHDBDB Next", url: "https://dhcraft.org/mhdbdb-tei-only/"}
  - {kind: website, label: "MHDBDB Graph", url: "https://mhdbdb.plus.ac.at/graph/"}
  - {kind: code, label: "mhdbdb-tei-only", url: "https://github.com/DigitalHumanitiesCraft/mhdbdb-tei-only"}
  - {kind: code, label: "MHDBDB-next", url: "https://github.com/Middle-High-German-Conceptual-Database/MHDBDB-next"}
  - {kind: code, label: "MHDBDB-graph", url: "https://github.com/Middle-High-German-Conceptual-Database/MHDBDB-graph"}
  - {kind: code, label: {de: "GitHub-Organisation", en: "GitHub organisation"}, url: "https://github.com/Middle-High-German-Conceptual-Database"}
  - {kind: data, label: {de: "TEI-XML-Repositorium (Zenodo)", en: "TEI-XML repository (Zenodo)"}, url: "https://doi.org/10.5281/zenodo.20627657"}
  - {kind: project, label: {de: "Universität Salzburg", en: "University of Salzburg"}, url: "https://www.plus.ac.at/mittelhochdeutsche-begriffsdatenbank/"}
  - {kind: blog, label: "MHDBDB Next: Forschen ohne Datenbankserver", url: "https://doi.org/10.58079/16jkg"}
subprojects:
  - name: "Users First. Optimierung von User Interface, User Experience und Crowdsourcing an der Mittelhochdeutschen Begriffsdatenbank"
    start: 2024-10
    end: 2026-12
    funding: "CLARIAH-AT (BMFWF)"
    summary:
      de: "Stabilisierung von MHDBDB Graph (RDF) und Aufbau von MHDBDB Next (TEI). Nutzer:innen können Belege beitragen und automatisch erzeugte Daten prüfen. Verantwortlich: Katharina Zeppezauer-Wachauer, Julia Hintersteiner, Alan Lena van Beek."
      en: "Stabilising MHDBDB Graph (RDF) and building MHDBDB Next (TEI). Users can contribute records and check automatically generated data. Responsible: Katharina Zeppezauer-Wachauer, Julia Hintersteiner, Alan Lena van Beek."
    links:
      - {kind: project, label: "CLARIAH-AT", url: "https://clariah.at/en/projects/users-first-optimierung-von-user-interface-user-experience-und-crowdsourcing-an-der-mittelhochdeutschen-begriffsdatenbank/"}
      - {kind: website, label: {de: "Belege beitragen", en: "Contribute records"}, url: "https://dhcraft.org/mhdbdb-tei-only/hilfe-belege-beitragen.html"}
  - name: "MHDBDB goes AI. Datenaufbereitung für das OER-LLM ParzivAI"
    start: 2024-10
    end: 2026-12
    funding: "CLARIAH-AT (BMFWF)"
    summary:
      de: "Aufbereitung der MHDBDB-Daten in offenen Formaten (TEI, RDF, JSON, Plain Text) und eine offene API für Lemma-Abfragen als Material für ParzivAI, ein LLM zur Übersetzung mittelhochdeutscher Texte (Prototyp: Florian Nieser und Thomas Renkert, Heidelberg). Verantwortlich: Katharina Zeppezauer-Wachauer, Julia Hintersteiner, Alan Lena van Beek. Dazu der Hackathon „Von historischen Daten zu KI“ (Salzburg, Oktober 2025)."
      en: "Preparing the MHDBDB data in open formats (TEI, RDF, JSON, plain text) and an open API for lemma queries as material for ParzivAI, an LLM for translating Middle High German texts (prototype: Florian Nieser and Thomas Renkert, Heidelberg). Responsible: Katharina Zeppezauer-Wachauer, Julia Hintersteiner, Alan Lena van Beek. Includes the hackathon “Von historischen Daten zu KI” (Salzburg, October 2025)."
    links:
      - {kind: project, label: "CLARIAH-AT", url: "https://clariah.at/en/projects/mhdbdb-goes-ai/"}
      - {kind: code, label: "plain-txt-Texte", url: "https://github.com/Middle-High-German-Conceptual-Database/plain-txt-Texte"}
      - {kind: blog, label: {de: "Hackathon-Bericht, DH Salzburg", en: "Hackathon report, DH Salzburg"}, url: "https://dhsalzburg.hypotheses.org/6295"}
---

Die MHDBDB ist eine seit 1992 aufgebaute Forschungsinfrastruktur zur mittelhochdeutschen Sprache und Literatur, begonnen von Horst P. Pütz (Kiel) und Klaus M. Schmidt (Bowling Green) und seit 2002 an der Universität Salzburg. Sie enthält 667 Texte mit Lemmatisierung, Wortartenangaben und Anbindung an ein Begriffssystem. 2024 bis 2026 wurde der gesamte Datenbestand von RDF nach TEI migriert. Die Daten liegen offen auf GitHub und Zenodo; die neue Oberfläche MHDBDB Next arbeitet ohne Datenbankserver direkt auf den TEI-Dateien, MHDBDB Graph bleibt als RDF-Zugang bestehen.

**Meine Aufgaben:** Datenmigration und Kuratierung des TEI-Bestands, User Acceptance Testing für MHDBDB Next, Projektkoordination und Drittmittelanträge, TEI-Dokumentation, XPath- und XSLT-Skripting.
