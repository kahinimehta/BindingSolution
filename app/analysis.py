"""Claude-powered analysis: categorization, connections, strategies, specs.

Each function returns a plain dict (a validated Pydantic model dumped to
JSON) ready for the store and the UI. Structured outputs are produced with
the Anthropic Python SDK's `messages.parse()` so the model is constrained
to our schema and we get a typed object back.

If no API key is set (or MOCK_LLM=true) every function falls back to a
deterministic heuristic so the whole app stays usable offline.
"""
from __future__ import annotations

import textwrap
from typing import Any, Callable

from pydantic import ValidationError

from .config import Settings
from .reading_schedule import attach_reading_schedule
from .grouping import complete_paper_groups, enrich_group_summaries, heuristic_paper_groups
from .schemas import (
    ConnectionMap,
    PaperGroupingMapSpec,
    PaperRelevance,
    ProjectCategory,
    ReadingStrategy,
    SpecValidation,
)
from . import mock

# Per-paper summarization is high-volume → keep outputs tight.
_MAX_TOKENS_LIGHT = 4000
# Cross-project reasoning and planning → give the model room.
_MAX_TOKENS_HEAVY = 16000
# Paper grouping returns many paper_keys + per-set summaries — avoid parse truncation.
_MAX_TOKENS_GROUPS = 32000
_MAX_TOKENS_CHAT = 4096

_SYSTEM = (
    "You are a meticulous research librarian and methodologist helping a "
    "researcher make sense of their reference library. You read groups of "
    "papers and identify their topics, the threads that connect them, and "
    "how they bear on a researcher's goals. Be specific and grounded in the "
    "titles, abstracts, and tags you are given; never invent papers, "
    "findings, or citations that are not present in the input. When you are "
    "uncertain, say so plainly rather than overstating a connection."
)

_CHAT_SYSTEM = (
    "You are BindingSolution's research assistant. The user has already synced "
    "their Zotero library locally — you receive excerpts from that shelf below "
    "(collection names and counts, categorizations, saved connections, paper "
    "groups, reading plans, spec screenings, and limited paper metadata). "
    "You do NOT have full paper text, PDFs, or abstracts for most papers — only "
    "titles/tags and items explicitly named in saved analyses. Answer using ONLY "
    "that context. Never claim to have read a paper's full text or abstract unless "
    "a short excerpt appears in the context block. Cite collection names and paper "
    "titles when helpful. If something is missing, say so and suggest running the "
    "relevant view (categorize, connections, groups, spec screening). Do not invent "
    "papers, authors, findings, or publication details."
)


class AnalysisError(RuntimeError):
    pass


class Analyzer:
    """Wraps the Anthropic client (or the offline mock)."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = settings.model
        self.use_mock = settings.mock_llm or not settings.anthropic_api_key
        self._client = None
        if not self.use_mock:
            import anthropic  # lazy: demo/test installs may skip the dep

            self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    # ── low-level call ───────────────────────────────────────────────
    def _parse(
        self,
        prompt: str,
        schema,
        *,
        heavy: bool,
        max_tokens: int | None = None,
        thinking: bool | None = None,
    ) -> Any:
        """Single structured-output call returning a validated `schema` instance."""
        import anthropic

        if max_tokens is None:
            max_tokens = _MAX_TOKENS_HEAVY if heavy else _MAX_TOKENS_LIGHT
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": _SYSTEM,
            "messages": [{"role": "user", "content": prompt}],
            "output_format": schema,
        }
        use_thinking = heavy if thinking is None else thinking
        if use_thinking:
            # Cross-project reasoning benefits from adaptive thinking.
            kwargs["thinking"] = {"type": "adaptive"}

        try:
            response = self._client.messages.parse(**kwargs)
        except ValidationError as exc:
            raise AnalysisError(
                "Structured output was truncated or invalid JSON — retrying with a more compact prompt."
            ) from exc
        except anthropic.APIStatusError as exc:
            raise AnalysisError(f"Claude API error ({exc.status_code}): {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise AnalysisError("Could not reach the Claude API. Check your connection.") from exc

        if response.stop_reason == "refusal":
            raise AnalysisError("The model declined to analyze this content.")
        if response.parsed_output is None:
            if response.stop_reason == "max_tokens":
                raise AnalysisError(
                    "Structured output was cut off (max_tokens) — retrying with a more compact prompt."
                )
            raise AnalysisError(
                "The model did not return valid structured output (parse overflow or truncated JSON)."
            )
        try:
            return response.parsed_output
        except ValidationError as exc:
            raise AnalysisError(
                "Structured output was truncated or invalid JSON — retrying with a more compact prompt."
            ) from exc

    def _reply_text(self, response: Any) -> str:
        parts = [
            block.text for block in (response.content or [])
            if getattr(block, "type", None) == "text" and getattr(block, "text", None)
        ]
        text = "\n".join(parts).strip()
        if not text:
            raise AnalysisError("The model returned an empty reply.")
        return text

    # ── chat (multi-turn, free-form) ─────────────────────────────────
    def chat(self, message: str, context: str, history: list[dict]) -> str:
        if self.use_mock:
            return mock.chat_reply(message, context, history)
        import anthropic

        system = f"{_CHAT_SYSTEM}\n\n--- LIBRARY CONTEXT (local store) ---\n{context}"
        messages = [
            {"role": turn["role"], "content": turn["content"]}
            for turn in history[-12:]
            if turn.get("role") in ("user", "assistant") and turn.get("content")
        ]
        messages.append({"role": "user", "content": message})
        try:
            response = self._client.messages.create(
                model=self.model,
                max_tokens=_MAX_TOKENS_CHAT,
                system=system,
                messages=messages,
            )
        except anthropic.APIStatusError as exc:
            raise AnalysisError(f"Claude API error ({exc.status_code}): {exc.message}") from exc
        except anthropic.APIConnectionError as exc:
            raise AnalysisError("Could not reach the Claude API. Check your connection.") from exc
        if response.stop_reason == "refusal":
            raise AnalysisError("The model declined to answer.")
        return self._reply_text(response)

    # ── 1. categorize one project ────────────────────────────────────
    def categorize_project(self, project: dict) -> dict:
        if self.use_mock:
            return mock.categorize_project(project)
        prompt = _categorize_prompt(project)
        result: ProjectCategory = self._parse(prompt, ProjectCategory, heavy=False)
        return result.model_dump()

    # ── 2. connections across projects ───────────────────────────────
    def find_connections(self, projects: list[dict]) -> dict:
        if self.use_mock:
            return mock.find_connections(projects)
        prompt = _connections_prompt(projects)
        result: ConnectionMap = self._parse(prompt, ConnectionMap, heavy=True)
        return result.model_dump()

    # ── 3. cross-project paper groups (no duplication) ───────────────
    def find_paper_groups(self, projects: list[dict]) -> dict:
        used_mock = False
        if self.use_mock:
            data = heuristic_paper_groups(projects)
            used_mock = True
        else:
            try:
                data = self._claude_paper_groups(projects)
            except (AnalysisError, ValidationError):
                data = heuristic_paper_groups(projects)
                used_mock = True
        if used_mock:
            data["_mock"] = True
        else:
            data.pop("_mock", None)
        return data

    def _claude_paper_groups(self, projects: list[dict]) -> dict:
        """Claude grouping with compact retries when structured JSON would overflow."""
        last_error: AnalysisError | None = None
        for compact, brief in ((False, False), (True, False), (True, True)):
            prompt = _paper_groups_prompt(projects, compact=compact, brief=brief)
            try:
                result: PaperGroupingMapSpec = self._parse(
                    prompt,
                    PaperGroupingMapSpec,
                    heavy=True,
                    max_tokens=_MAX_TOKENS_GROUPS,
                    thinking=False,
                )
                data = complete_paper_groups(result.model_dump(), projects)
                return enrich_group_summaries(data, projects)
            except AnalysisError as exc:
                last_error = exc
        raise last_error or AnalysisError("Paper grouping failed.")

    # ── 4. reading strategy over chosen projects ─────────────────────
    def reading_strategy(self, projects: list[dict], goal: str) -> dict:
        if self.use_mock:
            data = mock.reading_strategy(projects, goal)
        else:
            try:
                prompt = _strategy_prompt(projects, goal)
                result: ReadingStrategy = self._parse(prompt, ReadingStrategy, heavy=True)
                data = result.model_dump()
            except AnalysisError:
                data = mock.reading_strategy(projects, goal)
        plan = complete_reading_strategy(data, projects, goal)
        return attach_reading_schedule(plan, projects)

    # ── 5. validate an uploaded project spec ─────────────────────────
    def validate_spec(self, spec_text: str) -> dict:
        if self.use_mock:
            return mock.validate_spec(spec_text)
        prompt = _validate_spec_prompt(spec_text)
        result: SpecValidation = self._parse(prompt, SpecValidation, heavy=False)
        return result.model_dump()

    # ── 6. relevance of one paper to a project spec ──────────────────
    def assess_paper(self, spec_text: str, paper: dict) -> dict:
        if self.use_mock:
            return mock.assess_paper(spec_text, paper)
        prompt = _relevance_prompt(spec_text, paper)
        result: PaperRelevance = self._parse(prompt, PaperRelevance, heavy=False)
        data = result.model_dump()
        data["paper_key"] = paper["key"]  # guard against drift
        return data


# ── prompt builders ──────────────────────────────────────────────────
def _render_papers(
    items: list[dict],
    *,
    abstracts: bool = True,
    abstract_width: int = 600,
    limit: int | None = None,
) -> str:
    lines = []
    for it in (items[:limit] if limit else items):
        head = f"- [{it['key']}] \"{it['title']}\""
        meta = ", ".join(filter(None, [it.get("creators"), it.get("year"), it.get("publication")]))
        if meta:
            head += f" ({meta})"
        lines.append(head)
        if it.get("tags"):
            lines.append(f"    tags: {', '.join(it['tags'][:10])}")
        if abstracts and it.get("abstract"):
            abs = textwrap.shorten(it["abstract"], width=abstract_width, placeholder=" …")
            lines.append(f"    abstract: {abs}")
    return "\n".join(lines)


def _categorize_prompt(project: dict) -> str:
    return (
        f"Characterize this Zotero collection named \"{project['name']}\" "
        f"({project['num_items']} papers).\n\n"
        f"{_render_papers(project['items'])}\n\n"
        "Identify its discipline, a specific topic label, recurring themes, common "
        "methods, and matching keywords. Base everything strictly on the papers shown."
    )


def _paper_groups_prompt(
    projects: list[dict], *, compact: bool = False, brief: bool = False,
) -> str:
    blocks = []
    total = 0
    for proj in projects:
        items = proj.get("items") or []
        total += len(items)
        blocks.append(
            f"### Project [{proj['key']}] — {proj['name']} ({len(items)} papers)\n"
            f"{_render_papers(items, abstracts=not compact, abstract_width=220 if compact else 400)}"
        )
    body = "\n\n".join(blocks)
    compact_note = (
        "\n- Input is compact (titles and tags only) — still return full paper_keys lists "
        "and a 2-3 sentence `summary` per group.\n"
        if compact and not brief
        else ""
    )
    brief_note = (
        "\n- Keep `overview` to 2 short sentences.\n"
        "- Keep each group `summary` to ONE sentence (max 30 words).\n"
        "- Still return every paper_key in full — do not truncate lists.\n"
        if brief
        else ""
    )
    return (
        f"Organize this researcher's Zotero shelf across projects ({total} papers total).\n\n"
        f"{body}\n\n"
        "Propose optimal PAPER groups (not project groups) for reading:\n"
        "- Each paper_key may appear in AT MOST one group.\n"
        "- Each group must contain at least **10 paper_keys** (no maximum). "
        "Place at least **90%** of papers into groups; at most ~10% may remain standalone.\n"
        "- Vary set sizes — do not split the shelf into equal-sized chunks or collapse "
        "everything into one or two mega-sets. Use several thematic sets with naturally "
        "different counts.\n"
        "- Groups may span multiple projects when papers share themes, methods, or goals; "
        "a whole Zotero collection may also form one set when thematically coherent.\n"
        "- Include every paper you can place in a coherent thematic set — list ALL "
        "paper_keys for each group, not just examples.\n"
        "- Do not duplicate the same paper across groups.\n"
        "- Return only paper_keys per group — do NOT echo paper titles in the JSON.\n"
        "- For each group, write a `summary` of **2-3 sentences**: the shared theme, "
        "what the papers cover, and why they belong in one reading set.\n"
        "- Papers you do not group or drop will appear as standalone on the shelf.\n"
        "- In `drops`, flag papers to remove or archive: duplicates filed in multiple "
        "collections, redundant surveys superseded by newer work, weak fits, or outdated "
        "papers that no longer match the shelf.\n"
        f"{compact_note}"
        f"{brief_note}"
        "Use bracketed paper_key and project_key values exactly as given."
    )


def _connections_prompt(projects: list[dict]) -> str:
    blocks = []
    for proj in projects:
        blocks.append(
            f"### Project [{proj['key']}] — {proj['name']} ({proj['num_items']} papers)\n"
            f"{_render_papers(proj['items'], abstracts=True, limit=8)}"
        )
    body = "\n\n".join(blocks)
    return (
        "Here is a researcher's library, organized into projects. Find the genuine "
        "connections ACROSS projects — shared concepts, methods, datasets, recurring "
        "authors, or applications — and propose which projects are most worth reading "
        "or combining together.\n\n"
        f"{body}\n\n"
        "Only assert connections you can point to in the titles, abstracts, or tags. "
        "Use the bracketed project keys exactly as given."
    )


def _strategy_prompt(projects: list[dict], goal: str) -> str:
    blocks = []
    for proj in projects:
        blocks.append(
            f"### Project [{proj['key']}] — {proj['name']}\n"
            f"{_render_papers(proj['items'], abstracts=True)}"
        )
    body = "\n\n".join(blocks)
    goal_line = goal.strip() or "Build a well-sequenced understanding across these projects."
    return (
        f"The researcher's goal:\n\"{goal_line}\"\n\n"
        "Design an ordered reading strategy across the following projects. Sequence "
        "papers so that foundational and methodological work comes before papers that "
        "build on it, and group related papers. Every paper_key and project_key MUST "
        "come from the lists below.\n\n"
        f"{body}\n\n"
        "Produce a sequence that a person could actually follow this week."
    )


def _validate_spec_prompt(spec_text: str) -> str:
    excerpt = textwrap.shorten(spec_text.strip(), width=6000, placeholder=" …")
    return (
        "A researcher is uploading text to BindingSolution's Project specs feature. "
        "That feature scores papers in their reference library against a PROJECT "
        "SPECIFICATION — a grant aim, proposal summary, research plan, or short "
        "description of what they are trying to build or investigate.\n\n"
        "Read the upload below and decide whether it belongs in that feature.\n\n"
        "ACCEPT as project_spec when the text states research goals, questions, "
        "methods, or deliverables — even if informal or only a paragraph.\n\n"
        "REJECT as academic_paper when it is clearly a published paper (abstract, "
        "introduction, results, references) rather than the user's own project brief.\n\n"
        "REJECT as personal_document for resumes, invoices, emails, meeting notes, "
        "recipes, shopping lists, legal forms, or other everyday documents.\n\n"
        "REJECT as unrelated for random text, placeholder filler, or content with "
        "no research project described.\n\n"
        "When rejecting, write message as direct feedback to the user: say what you "
        "think they uploaded and ask for a grant aim, proposal, or project description "
        "instead. Be polite but clear.\n\n"
        f"UPLOADED TEXT:\n{excerpt}"
    )


def _relevance_prompt(spec_text: str, paper: dict) -> str:
    spec = textwrap.shorten(spec_text.strip(), width=4000, placeholder=" …")
    abstract = paper.get("abstract") or "(no abstract available)"
    meta = ", ".join(filter(None, [paper.get("creators"), paper.get("year"), paper.get("publication")]))
    return (
        "PROJECT SPECIFICATION:\n"
        f"{spec}\n\n"
        "PAPER TO ASSESS:\n"
        f"- key: {paper['key']}\n"
        f"- title: {paper['title']}\n"
        f"- {meta}\n"
        f"- tags: {', '.join(paper.get('tags', [])) or '(none)'}\n"
        f"- abstract: {abstract}\n\n"
        "Summarize the paper, then judge how relevant it is to THIS project "
        "specification specifically. Be honest: most papers in a library are only "
        "tangential to any one project. Reserve high scores for papers that truly bear "
        "on the project's questions, methods, or data."
    )


def complete_reading_strategy(result: dict, projects: list[dict], goal: str) -> dict:
    """Ensure every paper appears in the plan — Claude sometimes omits steps when output is tight."""
    all_keys = [it["key"] for p in projects for it in p.get("items") or []]
    if not all_keys:
        return result

    sequence = list(result.get("sequence") or [])
    seen = {step["paper_key"] for step in sequence}
    if len(seen) >= len(all_keys):
        return result

    fallback = mock.reading_strategy(projects, goal)
    for step in fallback.get("sequence", []):
        if step["paper_key"] not in seen:
            sequence.append(step)
            seen.add(step["paper_key"])
    result["sequence"] = sequence
    return result


def get_analyzer(settings: Settings) -> Analyzer:
    return Analyzer(settings)
