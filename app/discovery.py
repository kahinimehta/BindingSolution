"""Discover papers outside the local library via PubMed (and mock fallback)."""
from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

MAX_DISCOVERIES = 5
MIN_RELEVANCE_SCORE = 55
PUBMED_FETCH_BUFFER = 14

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


def _pubmed_fetch(query: str, max_results: int = PUBMED_FETCH_BUFFER) -> list[dict]:
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


def _matched_terms(hit: dict, terms: list[str]) -> list[str]:
    blob = f"{hit.get('title', '')} {hit.get('abstract', '')}".lower()
    return [t for t in terms if t in blob]


def _score_hit(hit: dict, query_terms: list[str]) -> int:
    matched = _matched_terms(hit, query_terms)
    if not matched:
        return 30
    score = 36 + len(matched) * 14
    title = (hit.get("title") or "").lower()
    score += sum(8 for t in matched if t in title)
    return min(98, score)


def _first_sentence(text: str, max_len: int = 160) -> str:
    text = " ".join((text or "").split())
    if not text:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    sent = parts[0]
    if len(sent) > max_len:
        sent = sent[:max_len].rsplit(" ", 1)[0] + "…"
    return sent


def _brief_summary(hit: dict) -> str:
    sent = _first_sentence(hit.get("abstract") or "")
    if sent:
        return sent
    journal = hit.get("journal") or "the literature"
    year = hit.get("year") or ""
    yr = f" ({year})" if year else ""
    return f"Article in {journal}{yr}."


def _relevance_explanation(hit: dict, terms: list[str]) -> str:
    matched = _matched_terms(hit, terms)
    if len(matched) >= 2:
        return (
            f"Strong match on {', '.join(matched[:3])} from your spec — "
            "not already in your library."
        )
    if len(matched) == 1:
        return (
            f"Touches {matched[0]} from your spec — worth reviewing; "
            "not already in your library."
        )
    return "Surfaced by your PubMed query — skim the summary to confirm fit."


def _enrich_hit(hit: dict, terms: list[str]) -> dict:
    row = dict(hit)
    row["score"] = row.get("score") or _score_hit(row, terms)
    row["summary"] = row.get("summary") or _brief_summary(row)
    row["relevance_explanation"] = row.get("relevance_explanation") or _relevance_explanation(row, terms)
    return row


def _select_relevant(hits: list[dict], terms: list[str], exclude: set[str]) -> list[dict]:
    """Keep up to MAX_DISCOVERIES hits above MIN_RELEVANCE_SCORE, ranked by fit."""
    candidates: list[dict] = []
    for hit in hits:
        if _norm_title(hit.get("title", "")) in exclude:
            continue
        row = _enrich_hit(hit, terms)
        if row["score"] < MIN_RELEVANCE_SCORE:
            continue
        candidates.append(row)

    candidates.sort(key=lambda r: -(r.get("score") or 0))

    selected: list[dict] = []
    for i, row in enumerate(candidates):
        if i >= MAX_DISCOVERIES:
            break
        if i > 0:
            prev = candidates[i - 1]["score"]
            if row["score"] < MIN_RELEVANCE_SCORE + 8 or row["score"] < prev - 18:
                break
        selected.append(row)
    return selected


def _mock_discoveries(spec_text: str, projects: list[dict], exclude: set[str]) -> list[dict]:
    seeds = build_pubmed_query(spec_text, projects).replace(" AND ", " ").split()[:4]
    topic = " ".join(seeds) or "computational neuroscience"
    templates = [
        ("Novel {t} framework for cross-species comparison", "Neuron", 2024, 92),
        ("Benchmarking {t} methods on open neurophysiology data", "Nature Communications", 2023, 84),
        ("A survey of {t} in systems neuroscience", "Trends in Cognitive Sciences", 2022, 76),
        ("Scalable pipelines for {t} with multimodal recordings", "eLife", 2024, 68),
        ("Causal inference meets {t}: open problems", "PNAS", 2023, 60),
        ("Peripheral notes on unrelated clinical trials", "Lancet", 2021, 42),
    ]
    out: list[dict] = []
    for i, (title_t, journal, year, score) in enumerate(templates):
        title = title_t.format(t=topic)
        if _norm_title(title) in exclude:
            continue
        abstract = (
            f"We propose a new angle on {topic}, motivated by recent grant aims "
            f"in this area. Results highlight {topic} as a central theme."
        )
        out.append({
            "id": f"mock:{i}",
            "pmid": "",
            "title": title,
            "authors": "Demo Author et al.",
            "year": str(year),
            "journal": journal,
            "abstract": abstract,
            "url": "https://pubmed.ncbi.nlm.nih.gov/",
            "source": "pubmed",
            "score": score,
            "_mock": True,
        })
    return out


def discover_for_spec(
    spec: dict,
    projects: list[dict],
    *,
    use_mock: bool = False,
    max_results: int = MAX_DISCOVERIES,
) -> list[dict]:
    """Return up to max_results ranked external suggestions not already in the library."""
    exclude = library_titles({p["key"]: p for p in projects})
    query = build_pubmed_query(spec.get("text", ""), projects)
    terms = [t for t in re.split(r"\W+", query.lower()) if t and t not in _STOP]

    if use_mock:
        hits = _mock_discoveries(spec.get("text", ""), projects, exclude)
    else:
        try:
            hits = _pubmed_fetch(query, max_results=PUBMED_FETCH_BUFFER)
        except Exception:
            hits = _mock_discoveries(spec.get("text", ""), projects, exclude)
            for h in hits:
                h["_fallback"] = True

    cap = min(max_results, MAX_DISCOVERIES)
    return _select_relevant(hits, terms, exclude)[:cap]
