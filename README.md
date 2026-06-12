<div align="center">

<img src="docs/banner.svg" alt="BindingSolution — your AI reading room" width="820" />

**Point it at your Zotero library and it makes sense of it.**

*Categorize collections, find cross-project threads, group papers without duplication, plan what to read, and match papers to a project spec — locally, with Claude.*

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
| **Find in library** (spec screen) — one call **per active paper** | Categorize one project, upload spec validation, **PubMed discovery** |
| Re-screening after every small sync | One reading plan, connections, or paper groups pass |

**Tips:** try demo mode first; tidy Zotero (only collections with **2+ papers** are active); read the spec-screening confirmation before starting; set a [spend limit](https://console.anthropic.com/settings/billing). Full detail: [docs/BILLING.md](docs/BILLING.md).

## Features

Use any view in any order.

- **Zotero sync** — Web API or local Zotero 7; bundled demo library
- **Active vs excluded** — only folders with 2+ papers are analyzed; empty, single-paper, and unfiled collections are reference-only
- **Categorize** — discipline, themes, methods, keywords, summary per collection
- **Connections** — shared threads and suggested groupings across projects
- **Groups** — optimal non-overlapping paper sets across collections; flags duplicates and weak fits to drop
- **Reading strategies** — ordered path + synthesis prompts; **schedule with estimated hours/days** (medium pace, ~12 pages/h at 2 h/day — see [docs/USAGE.md](docs/USAGE.md#reading-time-assumptions))
- **Spec** — upload a brief (PDF/Word/MD/text); **Find in library** screens your Zotero shelf (core/supporting only); **Suggested papers** returns up to five ranked PubMed hits *not* in your library, with summaries and relevance notes
- **Spec → reading plan** — **Build reading plan** from library matches; steps keep relevance notes; plan links back to the spec
- **Purge library** — wipe local data without touching Zotero (sidebar)

<p align="center">
  <img src="docs/screenshots/library.svg" alt="Library view" width="920" />
</p>

<p align="center">
  <img src="docs/screenshots/groups.svg" alt="Groups view with paper sets and prune suggestions" width="920" />
</p>

<p align="center">
  <img src="docs/screenshots/strategies.svg" alt="Reading strategies with schedule" width="920" />
</p>

<p align="center">
  <img src="docs/screenshots/specs-upload.svg" alt="Spec upload and library matches" width="920" />
  <br /><br />
  <img src="docs/screenshots/specs.svg" alt="Suggested papers PubMed discovery" width="920" />
</p>

## Persistence

Data: `./data/library.json` (gitignored). `make run` resumes where you left off.

| Action | Effect |
| --- | --- |
| **Purge library** (in-app) | Clears projects, analyses, plans, specs — not Zotero |
| `make clean` | Full dev reset (`data/`, venv, caches); keeps `.env` |
| `make setup` again | Reinstalls deps only — does **not** wipe your library |

## Docs

[USAGE](docs/USAGE.md) · [CONFIGURATION](docs/CONFIGURATION.md) · [BILLING](docs/BILLING.md) · [ARCHITECTURE](docs/ARCHITECTURE.md) · `make test`

## License

MIT — [LICENSE](LICENSE).
