# Usage

Start the app with `make run` and open <http://127.0.0.1:8765>. The sidebar
has four views; the status chips (bottom-left) show whether Claude and Zotero
are connected.

> **No keys?** Click **Load demo library** on the Library screen. You get a
> small synthetic library spanning four overlapping research areas so every
> feature is explorable. AI features run in heuristic "demo AI" mode (marked
> with a small badge) until you add a Claude key.

---

## 1. Sync your library

Click **Sync library** in the sidebar (or **Load demo library** on the empty
state). Each Zotero **collection** becomes a **project**; nested collections
keep their full path as the name. Re-syncing refreshes papers while keeping
any categorization you've already generated.

**Active vs excluded:** only collections with **at least 2 papers** are active.
Empty folders, single-paper collections, and **Library (unfiled)** appear in a
separate **Excluded collections** section — visible for reference but left out
of categorization, connections, reading plans, and spec analysis. Add papers or
merge collections in Zotero, then re-sync.

## 2. 📂 Categorize projects — *Library*

Open the **Library** view. Click **✦ Categorize** on an active card (or
**Categorize all** in the top bar). For each project Claude returns:

- a **discipline** and a specific **topic label**
- a 2–3 sentence **summary**
- recurring **themes** and common **methods**
- **keywords** used to match it against other projects

Click any card to see its full paper list and categorization.

## 3. ⁂ Find connections — *Connections*

Open **Connections** and click **Find connections**. Claude reads across all
projects and surfaces:

- **Shared threads** — a concept, method, dataset, or author that links two or
  more projects, each with a strength (strong / moderate / weak)
- **Suggested groupings** — clusters of projects worth reading together, each
  with a *Build a reading plan* shortcut

Connections need at least two projects.

## 4. ↯ Plan your reading — *Strategies*

Open **Strategies**. Either:

- **I choose projects** — tick the projects to combine, or
- **Let the agent decide** — it uses the suggested combination (or your whole
  library)

Add a one-line **goal** (e.g. *"a related-work section linking fairness and
causal inference"*) and click **Generate strategy**. You get:

- an ordered **reading sequence** (foundational/methodological papers first),
  each step explained
- **synthesis prompts** to hold in mind as you read across the set

Plans are saved; open or delete them from the same screen.

## 5. ✦ Find relevant papers — *Project specs*

Open **Project specs**. Use two tabs:

- **Upload & manage** — drop a **PDF, Word (.doc/.docx), Markdown, or text**
  file (grant aim, proposal, or project description) or paste the text.
  Irrelevant uploads (shopping lists, filler text, published papers, admin docs)
  are rejected with a short explanation of what to upload instead.
- **Suggested papers** — after you click **Find relevant papers**, see only the
  library papers that matter for that spec, each with:

  - a **core / supporting** flag
  - a short **why it's relevant** explanation
  - concrete **"use this for…"** suggestions where applicable

The app screens your whole active library but only lists the relevant hits, ranked
so the strongest matches appear first.

---

## Tips

- Every analysis runs as a background job with a **live progress bar** — you
  can keep working while it runs.
- Switching to a different `ANTHROPIC_MODEL` in `.env` (e.g. a faster model for
  bulk spec analysis) only needs a server restart.
- Refreshing suggestions re-screens against the current library, so it's worth
  re-running after you sync new papers.
