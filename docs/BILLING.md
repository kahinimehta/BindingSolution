# Claude API billing & wise use

BindingSolution is free and open source. **You pay Anthropic directly** for
Claude API usage when a real API key is configured. Zotero sync, local storage,
and the bundled demo library do not use your Claude account.

Set spending limits and review invoices in the [Anthropic Console](https://console.anthropic.com/settings/billing).

---

## What costs money

Every AI action sends text (paper titles, abstracts, tags, your project spec,
etc.) to Claude and bills **input + output tokens** to the API key in `.env`.
Pricing depends on the model you set in `ANTHROPIC_MODEL` — see
[Anthropic pricing](https://www.anthropic.com/pricing) for current rates.

| Feature | API calls | Relative cost | Notes |
| --- | --- | --- | --- |
| **Categorize one project** | 1 per project | Low | One structured call per collection. |
| **Categorize all** | 1 per active project | Low–medium | Same as clicking every card. |
| **Find connections** | 1 | Medium | One heavy cross-library call (adaptive thinking). |
| **Group papers** | 1 | Medium | One cross-library call; non-overlapping paper sets + drop list. |
| **Reading strategy** | 1 per plan | Medium | One heavy call; grows with papers in chosen projects. |
| **Build reading plan** (from spec) | 1 per plan | Medium | Same as a manual strategy, but only spec-relevant papers are included — not a per-paper screen. |
| **Upload spec** (validation) | 1 per upload | Low | Checks the text is a real project brief. |
| **Find in library** (spec screen) | **1 per paper screened** | **High at scale** | Scales linearly with active-library size. |
| **Discover new papers** (PubMed) | 0 | Free | Up to 5 ranked hits via NCBI eutils; no Claude call. |

**Zotero sync**, **re-opening saved results**, and **browsing the UI** do not
call Claude. Neither does **demo AI mode** (no key, or `MOCK_LLM=true`).

---

## What is cached (no extra charge)

Results are saved in `./data/library.json`:

- **Categorizations** survive a Zotero re-sync (for collections that still exist).
- **Connections**, **paper groups**, **reading plans**, **library matches**, and **PubMed discoveries**
  stay until you delete them or **Purge library**.
- Opening a saved plan or spec tab does **not** call the API again.

You only pay again when you explicitly re-run an analysis.

---

## Tips for using the API wisely

### 1. Learn the app before spending

Use **Load demo library** with no `ANTHROPIC_API_KEY` (or set `MOCK_LLM=true`)
to walk through every view. Demo AI is heuristic, not Claude, but the workflow
is the same.

### 2. Tidy Zotero first

Only collections with **2+ papers** are active. Merge or fill thin folders in
Zotero so you are not paying to screen papers you would never combine anyway.
Excluded collections are visible but skipped in analysis.

### 3. Categorize selectively

**✦ Categorize** individual cards you care about instead of **Categorize all**
on a huge library. You need categorization before connections are useful, but
not every folder needs it on day one.

### 4. Treat spec screening as the main cost driver

**Find in library** runs once **per paper** in your active library. A library
with 200 papers means ~200 API calls. The confirmation dialog shows how many
papers will be screened — use it.

- Run library screening when you have a real grant aim or proposal, not on a whim.
- **Re-screen library** is incremental — only papers not screened before are sent
  to Claude (typical after a Zotero sync adds new items).
- **Discover new papers** on PubMed is separate and does not use your Anthropic key.
- For very large libraries, consider a faster/cheaper model in `.env` for
  screening (see below).

### 5. Do not repeat heavy jobs unnecessarily

| Action | Re-run when… |
| --- | --- |
| Connections | You added/merged projects or want a fresh cross-library read |
| Group papers | You synced new papers or reorganized collections |
| Reading strategy | Your goal or project set changed |
| Build reading plan (spec) | You re-screened library matches or want a new ordering |
| Find in library | You synced new papers or changed the spec text |
| PubMed discovery | You updated the spec or categorized more projects |
| Categorize | Papers in that collection changed materially |

Otherwise, use what is already saved.

### 6. Choose the right model

Default: `claude-opus-4-8` (strongest, most capable, typically highest cost).

In `.env` you can point `ANTHROPIC_MODEL` at a faster or cheaper model for
bulk work — useful for large spec screens. Restart the server after changing it.
Check the [model overview](https://docs.anthropic.com/en/docs/about-claude/models)
for IDs and trade-offs.

Example (uncomment and adjust in `.env`):

```bash
#ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

There is no per-feature model setting yet; one model is used for everything.

### 7. Set guardrails in the Anthropic Console

- [Usage](https://console.anthropic.com/settings/usage) — watch token trends.
- [Billing](https://console.anthropic.com/settings/billing) — payment method and invoices.
- **Spend limits** — cap monthly usage so experiments cannot run away.

### 8. Keep the key local

The server defaults to `127.0.0.1`. Your key stays in gitignored `.env` on your
machine. Do not expose the server to the public internet with a live API key.

---

## Rough mental model

Think in **number of Claude calls**, not number of button clicks:

```
Low cost session:
  sync Zotero → categorize 2–3 projects → find connections once

Higher cost session:
  categorize all (20 projects) → spec screen 150 papers → re-screen after every small sync
```

When in doubt, start small: one project, one connection pass, one spec — then
scale up once the results look useful.

---

## Related docs

- [CONFIGURATION.md](CONFIGURATION.md) — keys, models, `MOCK_LLM`
- [USAGE.md](USAGE.md) — what each view does
- [README.md](../README.md) — persistence and purge
