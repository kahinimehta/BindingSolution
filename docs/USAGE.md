# Usage

Start the app with `make run` and open <http://127.0.0.1:8765>. The sidebar
has four views — use them in any order; the status chips (bottom-left) show
whether Claude and Zotero are connected.

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
of categorization, connections, reading plans, and paper suggestions. Add papers or
merge collections in Zotero, then re-sync.

**Purge library:** to wipe everything locally and start over, click **Purge
library** in the sidebar (below **Sync library**). This deletes synced projects,
categorizations, connections, saved reading plans, and project specs from
`./data/library.json`. It does **not** change your Zotero library. Confirm in
the dialog, then sync again or load the demo library. The button is hidden when
the shelf is already empty.

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

<p align="center">
  <img src="screenshots/strategies.svg" alt="Reading strategies compose form" width="920" />
</p>

## 5. ✦ Paper suggestions — *Project specs*

Open **Project specs** in the sidebar. The view has two tabs:

### Upload & manage

1. Drop a **PDF, Word (.doc/.docx), Markdown, or text** file — or paste a grant
   aim, proposal, or one-paragraph project description.
2. Click **Save spec**. Irrelevant uploads (shopping lists, filler text, published
   papers, admin docs) are rejected with a short explanation of what to upload
   instead.
3. Click **Find relevant papers** on a saved spec. A confirmation explains how
   many papers will be screened and that runtime scales with library size.

<p align="center">
  <img src="screenshots/specs-upload.svg" alt="Upload and manage tab with spec dropzone" width="720" />
</p>

### Suggested papers

After screening finishes, the app switches to **Suggested papers** automatically.
You can also open this tab any time to review past results.

- Pick a spec from the dropdown at the top.
- See a count like **4 relevant of 13 screened** — only matches are listed.
- Each row shows the paper title, its collection, a **core / supporting** flag,
  a **why it's relevant** explanation, and optional **"use this for…"** tags.

Non-relevant papers are not shown. Results are ranked so the strongest matches
appear first. Click **Refresh suggestions** to re-screen after syncing new papers.

<p align="center">
  <img src="screenshots/specs.svg" alt="Suggested papers tab with relevance explanations" width="720" />
</p>

---

## Tips

- Every analysis runs as a background job with a **live progress bar** — you
  can keep working while it runs. Confirmations and progress (spec screening,
  reading plans, connections, bulk categorization) open in the same centered
  dialog so the page does not jump or rescroll behind you.
- Switching to a different `ANTHROPIC_MODEL` in `.env` (e.g. a faster model for
  paper screening) only needs a server restart.
- Refreshing suggestions re-screens against the current library, so it's worth
  re-running after you sync new papers.
