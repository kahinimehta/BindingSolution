# Usage

Start the app with `make run` and open <http://127.0.0.1:8765>. The **sidebar**
has six views — use them in any order. On wide screens the whole interface
(sidebar + content) is **centered** as one panel with **large-type** typography
and spacing tuned for ultrawide and high-DPI displays (see
[CONFIGURATION.md](CONFIGURATION.md#display)). **Sync library** and **Purge
library** live in the **hero toolbar** (top right). At the bottom of the sidebar,
**Running** lists background tasks (sync, categorization, spec screening, and
similar). Status chips below that show whether Claude and Zotero are connected.

**Background jobs:** long tasks (sync, categorize, connections, groups, reading
plans, spec screening, PubMed discovery) start a server-side job and return
immediately. You can close the progress window (✕), switch sidebar views, or
refresh the page — work continues until it finishes. Open **Running** to see
live progress; click a row to reopen the progress window. Dismissing a row only
hides it from the list — it does not stop the job. The only way to stop work is
to interrupt the server process in your terminal (e.g. Ctrl+C on `make run`).
Progress bars are **indeterminate** (animated) during steps that are one long
operation — a single Claude call or PubMed search — and **step-based** when work
can be counted (sync per collection, spec screening per paper, categorize-all
per project). **Chat** is synchronous (one request per message) — it does not
appear in **Running**. After pulling app updates, **restart the server**
(Ctrl+C, then `make run`) so new API routes (e.g. chat) are loaded — the browser
can show new UI while an old process is still answering on port 8765.

> **No keys?** Click **Load demo library** on the Library screen. You get a
> small synthetic library spanning overlapping research areas (including a
> 12-paper neural population dynamics collection for Groups) so every feature
> is explorable. AI features run in heuristic "demo AI" mode (marked
> with a small badge) until you add a Claude key.

---

## 1. Sync your library

Click **Sync library** in the top toolbar (or **Load demo library** on the empty
state). Each Zotero **collection** becomes a **project**; nested collections
keep their full path as the name. Re-syncing refreshes papers while keeping
any categorization you've already generated.

**Active vs excluded:** only collections with **at least 2 papers** are active.
Empty folders, single-paper collections, and **Library (unfiled)** appear in a
separate **Excluded collections** section — visible for reference but left out
of categorization, connections, paper groups, reading plans, and spec screening. Add papers or
merge collections in Zotero, then re-sync.

**Purge library:** to wipe everything locally and start over, click **Purge
library** in the top toolbar (next to **Sync library**). This deletes synced projects,
categorizations, connections, paper groups, chat threads, saved reading plans, and project specs from
`./data/library.json`. It does **not** change your Zotero library. Confirm in
the dialog, then sync again or load the demo library. The button is hidden when
the shelf is already empty.

**Sync library:** pulls your latest Zotero **collections and papers** into the
local store (`./data/library.json`) — via the Zotero Web API or local Zotero 7,
depending on your `.env` setup. Each collection becomes a project; paper lists
and counts refresh to match Zotero. Existing **categorizations** for collections
that still exist are kept. Sync does **not** call Claude and does **not** change
anything in Zotero. With no Zotero credentials, use **Load demo library** on the
empty state instead (same sync endpoint, bundled sample data).

<p align="center">
  <img src="screenshots/library.svg" alt="Library view with six sidebar tabs, large-type layout, full-height project cards, Running panel, and hero toolbar" width="1000" />
</p>

## 2. 📂 Categorize projects — *Library*

Open the **Library** view. Click **✦ Categorize** on an active card (or
**Categorize all** in the top bar). For each project Claude returns:

- a **discipline** and a specific **topic label**
- a 2–3 sentence **summary**
- recurring **themes** and common **methods**
- **keywords** used to match it against other projects

Click any card to see its full paper list and categorization. Project cards grow
to show the full summary — no inner scroll box.

The **Papers** KPI counts papers in **active** collections (same number you will
see on **Groups**). If the same Zotero item is filed in multiple folders, it can
count more than once; the subtitle then shows how many **unique** items that is.

## 3. ⁂ Find connections — *Connections*

Open **Connections** and click **Find connections**. Progress is **phase-based**
(prepare → analyze → apply) with an **indeterminate** bar during the analyze step
because connections are one Claude pass across your projects, not one call per
collection. Claude reads across all projects and surfaces:

- **Shared threads** — a concept, method, dataset, or author that links two or
  more projects, each with a strength (strong / moderate / weak)
- **Suggested groupings** — clusters of projects worth reading together, each
  with a *Build a reading plan* shortcut

Connections need at least two projects.

## 4. ◎ Group papers — *Groups*

Open **Groups** and click **◎ Group papers**. BindingSolution reads **every**
active paper across your projects (deduplicated by Zotero item key). Progress is
**phase-based** (prepare → analyze → apply; e.g. *Step 2 of 3 — Analyzing 115
unique papers (184 collection entries in 13 active projects)*) with an
**indeterminate** bar during the analyze step because grouping is one Claude pass
over the whole shelf, not one API call per paper. Track it in the dialog or
**Running** panel. It returns:

- **Optimal paper sets** — thematic reading groups that may span multiple
  Zotero collections. The grouper places **at least 90%** of papers into sets
  (minimum **10 papers** per set, **no maximum**). Set sizes are **varied** —
  not uniform chunks and not one or two mega-sets. Each set shows a
  **2–3 sentence summary** of what the set contains and why to read it together,
  a **paper count**, and a flat list (no bullets). A paper appears in **at most
  one** set. Summaries are filled by Claude
  when possible; the server synthesizes a blurb from titles/tags if a run was
  truncated or you are viewing an older saved result — **re-run ◎ Group papers**
  after a sync for fresh summaries. The **demo AI** badge only appears when no
  Claude key is configured (re-run grouping after adding a key).
- **Papers** — same KPI as **Library** (`184` in the screenshot), with smaller
  subtitle *(including standalone papers)*. Below the overview, a summary line
  splits **unique** Zotero items (`N unique papers — … in sets · … standalone · …
  to drop`) because grouping deduplicates by item key.
- **Standalone papers** — at most ~10% of groupable papers stay ungrouped; the
  rest land in varied thematic sets. Single-paper collections and unfiled items
  also appear here (they skip grouping). An **All accounted for** badge means
  every unique paper is in a set, standalone, or drop. The overview line shows
  coverage (e.g. *Grouped 104 of 115 papers (90%)*).
- **Suggested drops** — papers to remove or archive: duplicates filed in more
  than one collection, redundant surveys, weak fits, or entries that no longer
  match your shelf.

**Connections vs Groups:** *Connections* links **projects** (shared threads and
which collections to combine). *Groups* organizes **individual papers** without
duplication and tells you what to prune.

Demo mode uses deterministic heuristics (title deduping, whole-collection sets,
tag clustering, and coverage balancing); with a Claude key the same schema is
filled by the model.

<p align="center">
  <img src="screenshots/groups.svg" alt="Groups view with large-type layout, 90% grouped coverage, varied set sizes, Papers KPI matching Library, set summaries, standalone papers, and drop suggestions" width="1000" />
</p>

## 5. 💬 Chat — *Chat*

Open **Chat** after syncing your library. Type a question and press **Enter**
or click the **↑** send button in the compose box. BindingSolution assembles
context from your **local store** —
synced papers, categorizations, saved connections, paper groups, reading
strategies, and spec screenings — and sends it to Claude with your message.
**Nothing is re-uploaded**; the server reads what is already in
`./data/library.json`.

- **Multi-turn** — replies stay in one thread until you click **New chat**.
- **Grounded answers** — the assistant is instructed to cite only what is in
  your shelf context and to suggest running a view (categorize, connections,
  groups, spec screening) when data is missing.
- **Cost** — one Claude call per message (lightweight compared to per-paper
  spec screening). Demo mode uses heuristic replies when no API key is set.

Example questions: *How do my fairness and causal collections overlap?* · *What
should I read first for population coding?* · *Which papers matched my spec?*

<p align="center">
  <img src="screenshots/chat.svg" alt="Chat view with multi-turn replies, up-arrow send button, and context from the local synced library store" width="1000" />
</p>

## 6. ↯ Plan your reading — *Strategies*

Open **Strategies**. Either:

- **I choose projects** — tick the projects to combine, or
- **Let the agent decide** — it uses the suggested combination (or your whole
  library)

Add a one-line **goal** (e.g. *"a related-work section linking fairness and
causal inference"*) and click **Generate strategy**. Progress is a single
**indeterminate** bar while Claude designs the plan (one API call, not per-project
steps). You get:

- an ordered **reading sequence** (foundational/methodological papers first),
  each step explained
- a **reading schedule** — estimated time per paper, total hours, and a
  day-by-day layout
- **synthesis prompts** to hold in mind as you read across the set

Plans are saved; open or delete them from the same screen. Plans built from a
spec show **from spec** in the list and a link back to the spec's **Library
matches** when you open them.

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
  <img src="screenshots/strategies.svg" alt="Reading strategies with large-type layout, compose form, and schedule estimates" width="1000" />
</p>

## 7. ✦ Spec — upload, screen library, discover on PubMed

Open **Spec** in the sidebar. The view has two tabs with different jobs:

| Tab | What it does | Uses Claude? |
| --- | --- | --- |
| **Upload & manage** | Save a brief and **Find in library** (screen your synced Zotero shelf); **Re-screen** is incremental | Yes — one call per paper screened (new papers only on re-screen) |
| **Suggested papers** | **Discover new papers** on PubMed that are *not* already in your library | No — PubMed eutils (free) |

### Upload & manage

1. Drop a **PDF, Word (.doc/.docx), Markdown, or text** file — or paste a grant
   aim, proposal, or one-paragraph project description.
2. Click **Save spec**. Irrelevant uploads (shopping lists, filler text, published
   papers, admin docs) are rejected with a short explanation of what to upload
   instead.
3. Click **Find in library** on a saved spec. A confirmation explains how many
   papers will be screened and that runtime scales with library size. **Re-screen
   library** is incremental: after a sync, only papers you have not screened yet
   are sent to Claude; existing library matches are kept. Track progress under
   **Running** in the sidebar — the spec row no longer shows an “analyzing” badge.
4. Scroll to **Library matches** on the same tab. Pick a spec, review core /
   supporting hits with **why it's relevant** notes, and click **↯ Build reading
   plan** to turn them into an ordered path in **Strategies**.

<p align="center">
  <img src="screenshots/specs-upload.svg" alt="Spec upload with large-type layout, library matches, and incremental re-screen" width="1000" />
</p>

### Suggested papers (PubMed)

Switch to **Suggested papers** when you want *new* literature — papers you do
not already have in Zotero.

- Pick a spec from the dropdown.
- Click **✦ Discover new papers**. BindingSolution builds a PubMed query from your
  spec text and categorized project keywords, searches NCBI eutils, and filters
  out titles already in your synced library.
- You get **up to five** hits, ranked by keyword overlap with your spec. Each row
  links to PubMed, shows a **one-sentence summary** (from the abstract when
  available), and a short **why it's relevant** note. Papers below a relevance
  cutoff are dropped, so you may see fewer than five if the tail is weak.
- Re-run discovery after you update the spec or categorize more projects.

Demo mode (`MOCK_LLM=true`) uses deterministic mock PubMed hits so you can try
the flow offline.

<p align="center">
  <img src="screenshots/specs.svg" alt="Suggested papers with large-type layout, PubMed discovery tab" width="1000" />
</p>

---

## Tips

### Workflow

- Every analysis runs as a **background job**. Progress opens in a centered
  dialog; you can close it (✕), switch views, or refresh — work continues until
  done. Track jobs in the sidebar **Running** panel (badge shows active count).
- **Find in library** saves results after the first run. **Re-screen library**
  only assesses **new** papers added since the last screen (e.g. after a Zotero
  sync) — already-screened papers are skipped (see [BILLING.md](BILLING.md)).
  PubMed discovery is separate and does not use your Anthropic key.
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
