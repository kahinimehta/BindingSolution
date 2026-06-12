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
- a **reading schedule** — estimated time per paper, total hours, and a
  day-by-day layout
- **synthesis prompts** to hold in mind as you read across the set

Plans are saved; open or delete them from the same screen. Plans built from a
project spec show **from spec** in the list and a link back to **Suggested
papers** when you open them.

### Reading time assumptions

Estimates assume a **medium academic reading pace**:

| Assumption | Value |
| --- | --- |
| Reading speed | **~12 pages/hour** (~5 min/page) — careful read of dense PDFs |
| Default paper length | **9 pages** when Zotero has no page count (typical conference/journal article) |
| Longer papers | Surveys/reviews ~18 pages; theses/books ~35 pages; inferred from tags and abstract length when needed |
| Daily budget | **2 hours/day** of focused reading to spread steps across **Day 1**, **Day 2**, … |

These are planning hints, not deadlines. Skim faster or read deeper and your real time will differ. The schedule banner on each plan states the assumptions used.

<p align="center">
  <img src="screenshots/strategies.svg" alt="Reading strategies compose form and spec-mapped plan" width="920" />
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

Click **↯ Build reading plan** to turn the suggested papers into an ordered
reading path in **Strategies**. Only **core** and **supporting** hits are
included — not your whole library. The plan is built with one strategy API call
(see [BILLING.md](BILLING.md)). Each step keeps its **core / supporting** flag
and the **why it's relevant** note from the spec assessment. Open the saved plan
to see a banner linking back to the spec's **Suggested papers** tab.

<p align="center">
  <img src="screenshots/specs.svg" alt="Suggested papers tab with Build reading plan button" width="720" />
</p>

---

## Tips

### Workflow

- Every analysis runs as a background job with a **live progress bar** — you
  can keep working while it runs. Confirmations and progress (spec screening,
  reading plans, connections, bulk categorization) open in the same centered
  dialog so the page does not jump or rescroll behind you.
- Refreshing suggestions re-screens against the current library, so it's worth
  re-running after you sync new papers — but each re-run calls Claude again for
  every active paper (see [BILLING.md](BILLING.md)).
- Saved categorizations, connections, plans, and spec results are **free to
  re-open**; you only pay when you trigger a new analysis.

### Using the Claude API wisely

Full detail: **[docs/BILLING.md](BILLING.md)**. Short version:

1. **Try demo mode first** — no key, or `MOCK_LLM=true`, to learn the UI.
2. **Categorize what you need** — avoid **Categorize all** on a huge shelf until
   you know the output is useful.
3. **Spec screening is the big one** — cost scales with paper count; read the
   confirmation dialog before you start.
4. **Do not repeat heavy jobs** — re-run connections, strategies, or spec
   screening only when your library or goals actually changed.
5. **Tidy Zotero** — active collections need 2+ papers; merge thin folders so
   you are not screening noise.
6. **Pick your model** — default `claude-opus-4-8` is strongest; a faster model
   in `ANTHROPIC_MODEL` can reduce cost for large libraries (restart required).
7. **Set a spend limit** in the [Anthropic Console](https://console.anthropic.com/settings/billing).
