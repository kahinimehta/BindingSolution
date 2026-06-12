"""Pydantic schemas for Claude's structured (JSON) outputs.

These double as the request schema we hand to the Anthropic SDK
(`client.messages.parse(output_format=...)`) and the response contract the
frontend renders. Keep field names stable — the UI reads them directly.

Schema notes for structured outputs: every object needs
`additionalProperties: false` (Pydantic models emit this by default) and
all listed properties are treated as required. Avoid numeric/length
constraints (minimum/maxLength/etc.) — the API ignores them and the SDK
strips them, so enforce ranges in prose in the field description instead.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class ProjectCategory(BaseModel):
    """One Zotero collection, characterized."""

    discipline: str = Field(description="Broad field, e.g. 'Machine Learning', 'Molecular Biology'.")
    category: str = Field(description="A specific 2-5 word topic label for this collection.")
    summary: str = Field(description="2-3 sentences describing what this body of work is about.")
    themes: list[str] = Field(description="3-6 recurring conceptual themes across the papers.")
    methods: list[str] = Field(description="2-5 methods, techniques, or data types frequently used.")
    keywords: list[str] = Field(description="4-8 short keywords for matching against other projects.")
    maturity: str = Field(
        description="One of: 'emerging', 'developing', 'established' — how settled the collection's focus looks."
    )


class SharedThread(BaseModel):
    """A concept, method, or author that links two or more projects."""

    label: str = Field(description="The shared concept, method, dataset, or author.")
    kind: str = Field(description="One of: 'theme', 'method', 'author', 'application'.")
    project_keys: list[str] = Field(description="Keys of the projects this thread connects (2 or more).")
    explanation: str = Field(description="1-2 sentences on how the thread shows up in each project.")
    strength: str = Field(description="One of: 'strong', 'moderate', 'weak'.")


class ProjectCluster(BaseModel):
    """A group of projects worth reading or combining together."""

    name: str = Field(description="A short name for the cluster.")
    project_keys: list[str] = Field(description="Keys of the projects in this cluster.")
    rationale: str = Field(description="Why these belong together and what a combined reading yields.")


class ConnectionMap(BaseModel):
    """Cross-project analysis of a whole library."""

    overview: str = Field(description="2-4 sentences on how the projects relate as a whole.")
    shared_threads: list[SharedThread] = Field(description="Concrete links between projects.")
    clusters: list[ProjectCluster] = Field(description="Suggested groupings of projects to combine.")
    suggested_combination: list[str] = Field(
        description="Project keys for the single most promising combination to read together."
    )


class GroupedPaperRef(BaseModel):
    paper_key: str = Field(description="Key of the paper in this group.")
    title: str = Field(description="Paper title for display.")
    project_key: str = Field(description="Project the paper belongs to.")


class PaperGroupSpec(BaseModel):
    """Lean group shape for Claude structured output — keys + summary only (no paper rows)."""

    name: str = Field(description="Short name for this reading set.")
    paper_keys: list[str] = Field(
        description=(
            "Paper keys in this group (10–30 items). Each paper_key may appear in at most one group."
        ),
    )
    project_keys: list[str] = Field(description="Project keys the papers come from.")
    summary: str = Field(
        description=(
            "Exactly 2-3 sentences: the shared theme, what the papers cover, "
            "and why read them together."
        ),
    )


class PaperGroup(BaseModel):
    """A non-overlapping set of papers worth reading together across projects."""

    name: str = Field(description="Short name for this reading set.")
    paper_keys: list[str] = Field(
        description="Paper keys in this group. Each paper_key may appear in at most one group."
    )
    papers: list[GroupedPaperRef] = Field(
        default_factory=list,
        description="Optional display refs; the server fills these from paper_keys when missing.",
    )
    project_keys: list[str] = Field(description="Project keys the papers come from.")
    summary: str = Field(
        description="2-3 sentences on the shared theme, what the papers cover, and why read them together.",
    )
    rationale: str = Field(
        default="",
        description="Optional short tagline; prefer `summary` for the main blurb.",
    )


class PaperDropSuggestion(BaseModel):
    """A paper the user may want to remove or archive from their shelf."""

    paper_key: str = Field(description="Key of the paper to consider dropping.")
    title: str = Field(description="Paper title for display.")
    project_key: str = Field(description="Project/collection the paper currently lives in.")
    drop_kind: str = Field(
        description="One of: 'duplicate', 'redundant', 'weak_fit', 'outdated'."
    )
    reason: str = Field(description="1-2 sentences explaining why to drop or archive it.")


class PaperGroupingMapSpec(BaseModel):
    """Lean map for Claude structured output — server fills paper rows and standalone list."""

    overview: str = Field(
        description="2-4 sentences summarizing how the shelf was organized and what to prune."
    )
    groups: list[PaperGroupSpec] = Field(
        description=(
            "Non-overlapping paper sets across projects; each paper appears at most once. "
            "Each set has 10–30 paper_keys — minimize standalone papers."
        ),
    )
    drops: list[PaperDropSuggestion] = Field(
        description="Papers to consider removing — duplicates across collections, redundant surveys, or weak fits."
    )


class PaperGroupingMap(BaseModel):
    """Optimal cross-project paper groups with no duplication plus prune suggestions."""

    overview: str = Field(
        description="2-4 sentences summarizing how the shelf was organized and what to prune."
    )
    groups: list[PaperGroup] = Field(
        description="Non-overlapping paper sets across projects; each paper appears at most once."
    )
    drops: list[PaperDropSuggestion] = Field(
        description="Papers to consider removing — duplicates across collections, redundant surveys, or weak fits."
    )
    ungrouped: list[GroupedPaperRef] = Field(
        default_factory=list,
        description="Active papers not placed in any thematic group or drop list (filled by server).",
    )


class ReadingStep(BaseModel):
    paper_key: str = Field(description="The key of the paper to read at this step.")
    title: str = Field(description="The paper's title (copied for display).")
    project_key: str = Field(description="Which project this paper comes from.")
    reason: str = Field(description="Why it sits at this point in the sequence.")


class ReadingStrategy(BaseModel):
    """An ordered reading plan over a chosen set of projects."""

    title: str = Field(description="A short title for this reading plan.")
    goal_restatement: str = Field(description="The reader's goal, restated in one sentence.")
    approach: str = Field(description="2-4 sentences describing the overall strategy and sequencing logic.")
    sequence: list[ReadingStep] = Field(description="Papers in recommended reading order (foundational first).")
    synthesis_prompts: list[str] = Field(
        description="3-5 questions to hold in mind to synthesize across these papers."
    )


class SpecValidation(BaseModel):
    """Whether uploaded text is a usable project specification."""

    is_project_spec: bool = Field(
        description="True only if this text describes a research project, grant aim, or proposal "
        "the user wants to match papers against."
    )
    detected_kind: str = Field(
        description="One of: 'project_spec', 'academic_paper', 'personal_document', 'unrelated'."
    )
    message: str = Field(
        description="If is_project_spec is false, a plain-language explanation for the user "
        "(1-2 sentences) saying what was detected and what to upload instead. "
        "If true, a brief confirmation such as 'Looks like a project specification.'"
    )


class PaperRelevance(BaseModel):
    """How one paper relates to an uploaded project specification."""

    paper_key: str = Field(description="The key of the paper being assessed.")
    relevance: str = Field(description="One of: 'core', 'supporting', 'tangential', 'not_relevant'.")
    score: int = Field(description="Relevance from 0 (unrelated) to 100 (essential). Use the full range.")
    summary: str = Field(description="2-3 sentence summary of the paper itself.")
    relevance_explanation: str = Field(description="1-2 sentences: how it bears on THIS project spec.")
    use_for: list[str] = Field(description="1-3 specific ways the project could use this paper.")
