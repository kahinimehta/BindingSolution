"""Discover papers outside the local library via PubMed (and mock fallback)."""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

_STOP = {
    "a", "an", "the", "and", "or", "for", "to", "of", "in", "on", "with", "we", "our",
    "this", "that", "will", "are", "is", "be", "by", "from", "as", "at", "it", "their",
}


def _norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").lower()).strip()


def library_titles(projects: dict[str, dict]) -> set[str]:
    titles: set[str] = set()
    for proj in projects.values():
        for item in proj.get("items") or []:
            t = _norm_title(item.get("title", ""))
            if t:
                titles.add(t)
    return titles


def build_pubmed_query(spec_text: str, projects: list[dict] | None = None) -> str:
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-+]{2,}", (spec_text or "").lower())
    freq: dict[str, int] = {}
    for w in words:
        if w in _STOP or len(w) < 4:
            continue
        freq[w] = freq.get(w, 0) + 1
    for proj in projects or []:
        cat = proj.get("category") or {}
        for kw in (cat.get("keywords") or [])[:4]:
            k = kw.lower().strip()
            if k and k not in _STOP:
                freq[k] = freq.get(k, 0) + 2
    ranked = sorted(freq, key=lambda k: (-freq[k], k))[:8]
    if not ranked:
        ranked = ["research", "neuroscience"]
    return " AND ".join(ranked[:5])


def _pubmed_fetch(query: str, max_results: int = 12) -> list[dict]:
    params = urllib.parse.urlencode({
        "db": "pubmed",
        "term": query,
        "retmax": str(max_results),
        "retmode": "json",
        "sort": "relevance",
    })
    with urllib.request.urlopen(
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?{params}",
        timeout=20,
    ) as resp:
        import json
        data = json.loads(resp.read().decode())
    ids = data.get("esearchresult", {}).get("idlist") or []
    if not ids:
        return []

    summary_params = urllib.parse.urlencode({
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml",
    })
    with urllib.request.urlopen(
        f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?{summary_params}",
        timeout=25,
    ) as resp:
        root = ET.fromstring(resp.read())

    out: list[dict] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = (article.findtext(".//PMID") or "").strip()
        title = " ".join((article.findtext(".//ArticleTitle") or "").split())
        journal = (article.findtext(".//Journal/Title") or "").strip()
        year = (article.findtext(".//PubDate/Year") or article.findtext(".//DateCompleted/Year") or "").strip()
        abstract_parts = [el.text or "" for el in article.findall(".//AbstractText")]
        abstract = " ".join(" ".join(abstract_parts).split())
        authors = []
        for au in article.findall(".//Author")[:4]:
            last = au.findtext("LastName") or ""
            initials = au.findtext("Initials") or ""
            if last:
                authors.append(f"{last} {initials}".strip())
        if not title or not pmid:
            continue
        out.append({
            "id": f"pmid:{pmid}",
            "pmid": pmid,
            "title": title,
            "authors": ", ".join(authors) or "Unknown",
            "year": year,
            "journal": journal,
            "abstract": abstract[:800],
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            "source": "pubmed",
        })
    return out


def _mock_discoveries(spec_text: str, projects: list[dict], exclude: set[str]) -> list[dict]:
    seeds = build_pubmed_query(spec_text, projects).replace(" AND ", " ").split()[:4]
    topic = " ".join(seeds) or "computational neuroscience"
    templates = [
        ("Novel {t} framework for cross-species comparison", "Neuron", 2024),
        ("Benchmarking {t} methods on open neurophysiology data", "Nature Communications", 2023),
        ("A survey of {t} in systems neuroscience", "Trends in Cognitive Sciences", 2022),
        ("Scalable pipelines for {t} with multimodal recordings", "eLife", 2024),
        ("Causal inference meets {t}: open problems", "PNAS", 2023),
    ]
    out: list[dict] = []
    for i, (title_t, journal, year) in enumerate(templates):
        title = title_t.format(t=topic)
        if _norm_title(title) in exclude:
            continue
        out.append({
            "id": f"mock:{i}",
            "pmid": "",
            "title": title,
            "authors": "Demo Author et al.",
            "year": str(year),
            "journal": journal,
            "abstract": f"We propose a new angle on {topic}, motivated by recent grant aims in this area.",
            "url": "https://pubmed.ncbi.nlm.nih.gov/",
            "source": "pubmed",
            "relevance_explanation": f"Touches {topic} themes from your spec but is not in your Zotero library.",
            "score": 92 - i * 7,
            "_mock": True,
        })
    return out


def _score_hit(hit: dict, query_terms: list[str]) -> int:
    blob = f"{hit.get('title', '')} {hit.get('abstract', '')}".lower()
    score = 40
    for term in query_terms:
        if term in blob:
            score += 12
    return min(98, score)


def discover_for_spec(
    spec: dict,
    projects: list[dict],
    *,
    use_mock: bool = False,
    max_results: int = 10,
) -> list[dict]:
    """Return ranked external paper suggestions not already in the library."""
    exclude = library_titles({p["key"]: p for p in projects})
    query = build_pubmed_query(spec.get("text", ""), projects)
    terms = [t for t in re.split(r"\W+", query.lower()) if t and t not in _STOP]

    if use_mock:
        hits = _mock_discoveries(spec.get("text", ""), projects, exclude)
    else:
        try:
            hits = _pubmed_fetch(query, max_results=max_results + 8)
        except Exception:
            hits = _mock_discoveries(spec.get("text", ""), projects, exclude)
            for h in hits:
                h["_fallback"] = True

    filtered: list[dict] = []
    for hit in hits:
        if _norm_title(hit.get("title", "")) in exclude:
            continue
        row = dict(hit)
        if "relevance_explanation" not in row:
            row["relevance_explanation"] = (
                "Found on PubMed for your project spec — not present in your synced library."
            )
        row["score"] = row.get("score") or _score_hit(row, terms)
        filtered.append(row)
        if len(filtered) >= max_results:
            break
    filtered.sort(key=lambda r: -(r.get("score") or 0))
    return filtered
