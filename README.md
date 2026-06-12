<div align="center">

<img src="docs/banner.svg" alt="BindingSolution — your AI reading room" width="820" />

**Point it at your Zotero library and it makes sense of it.**

*Categorize collections, find cross-project threads, group papers without duplication, plan what to read, and match papers to a project spec — locally, with Claude.*

Paper groups batch your shelf into **varied thematic sets** (≥10 papers each, **≥90% grouped**, no per-set cap — balanced sizes, not uniform chunks or mega-sets).

</div>

---

## Quick start

```bash
git clone https://github.com/kahinimehta/bindingsolution.git
cd bindingsolution
make setup && make run    # → http://127.0.0.1:8765
```

Add `ANTHROPIC_API_KEY`, `ZOTERO_LIBRARY_ID`, and `ZOTERO_API_KEY` to the gitignored `.env` from setup — see [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

**No keys?** `make run` → **Load demo library** (heuristic “demo AI”, full UI).

## API cost (read this)

Claude usage bills to **your** Anthropic account (per token). Zotero sync and re-opening saved results are free.

| Heavy | Light |
| --- | --- |
| **Find in library** (first run) — one call **per active paper** | Categorize one project, upload spec validation, **PubMed discovery** |
| **Re-screen library** after sync — **new papers only** | One reading plan, connections, paper groups, or **Chat** message |

**Tips:** try demo mode first; tidy Zotero (only collections with **2+ papers** are active); read the spec-screening confirmation before starting; set a [spend limit](https://console.anthropic.com/settings/billing). Full detail: [docs/BILLING.md](docs/BILLING.md).

## Features

Use any view in any order.

- **Large-type layout** — 3× scaled typography and spacing for ultrawide / high-DPI displays; project cards show full summaries (no inner scroll)
- **Zotero sync** — Web API or local Zotero 7; bundled demo library; **Sync library** / **Purge library** in the hero toolbar
- **Running** — sidebar panel tracks background jobs; **indeterminate** bars for single-shot Claude steps (reading plans, categorize) and the **analyze** phase of connections/groups; close the progress window or switch views without stopping work
- **Active vs excluded** — only folders with 2+ papers are analyzed; empty, single-paper, and unfiled collections are reference-only
- **Categorize** — discipline, themes, methods, keywords, summary per collection
- **Connections** — shared threads and suggested groupings across projects; phase-based progress (prepare → analyze → apply)
- **Groups** — thematic paper sets (**≥90% of papers grouped**, min 10 per set, varied sizes), **2–3 sentence summaries** per set, drop suggestions; **Papers** KPI matches Library *(including standalone papers)*; summary line shows unique-item split
- **Chat** — ask Claude about your synced shelf (papers, connections, groups, plans, specs) using the **local store** — no re-upload; **↑** send button or Enter
- **Reading strategies** — ordered path + synthesis prompts; **indeterminate** progress during plan generation; **schedule with estimated hours/days** (medium pace, ~12 pages/h at 2 h/day — see [docs/USAGE.md](docs/USAGE.md#reading-time-assumptions))
- **Spec** — upload a brief (PDF/Word/MD/text); **Find in library** screens your Zotero shelf (core/supporting only); **Re-screen library** is incremental (new papers only after sync); **Suggested papers** returns up to five ranked PubMed hits *not* in your library, with summaries and relevance notes
- **Spec → reading plan** — **Build reading plan** from library matches; steps keep relevance notes; plan links back to the spec
- **Purge library** — wipe local data without touching Zotero (hero toolbar)

<p align="center">
  <img src="docs/screenshots/library.svg" alt="Library view with six sidebar tabs, full-height project cards, hero toolbar, and Running panel (categorize-all 3/13)" width="1000" />
</p>

<p align="center">
  <img src="docs/screenshots/connections.svg" alt="Connections view with shared threads, suggested groupings, and Running panel at Step 2 of 3 indeterminate analyze" width="1000" />
</p>

<p align="center">
  <img src="docs/screenshots/groups.svg" alt="Groups view with 90% grouped coverage, varied set sizes, set summaries, and Running panel at Step 2 of 3 indeterminate analyze" width="1000" />
</p>

<p align="center">
  <img src="docs/screenshots/chat.svg" alt="Chat view with multi-turn replies, up-arrow send button, and context from the local synced library store" width="1000" />
</p>

<p align="center">
  <img src="docs/screenshots/strategies.svg" alt="Reading strategies compose form, saved plans with schedule estimates, and Running panel with indeterminate plan generation" width="1000" />
</p>

<p align="center">
  <img src="docs/screenshots/specs-upload.svg" alt="Spec upload with large-type layout, library matches, and incremental re-screen" width="1000" />
  <br /><br />
  <img src="docs/screenshots/specs.svg" alt="Suggested papers with large-type layout, PubMed discovery tab" width="1000" />
</p>

## Persistence

Data: `./data/library.json` (gitignored). `make run` resumes where you left off.
After `git pull`, restart the server (Ctrl+C, then `make run`) so new API routes load.

| Action | Effect |
| --- | --- |
| **Purge library** (in-app) | Clears projects, analyses, plans, specs, chats — not Zotero |
| **Sync library** (in-app) | Pulls collections and papers from Zotero into `./data/library.json`; keeps categorizations for matching collections — not Zotero, no Claude |
| `make clean` | Full dev reset (`data/`, venv, caches); keeps `.env` |
| `make setup` again | Reinstalls deps only — does **not** wipe your library |

## Docs

[USAGE](docs/USAGE.md) · [CONFIGURATION](docs/CONFIGURATION.md) · [BILLING](docs/BILLING.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) · `make test`

## License

MIT — [LICENSE](LICENSE).
