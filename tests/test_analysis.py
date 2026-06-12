"""Analyzer error handling and grouping retries."""
from pydantic import ValidationError

from app.analysis import AnalysisError, Analyzer
from app.config import get_settings


def _analyzer(monkeypatch) -> Analyzer:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("MOCK_LLM", "false")
    return Analyzer(get_settings())


def test_parse_wraps_validation_error(monkeypatch):
    analyzer = _analyzer(monkeypatch)

    class FakeResponse:
        stop_reason = "end_turn"
        parsed_output = None

    def boom(**_kwargs):
        raise ValidationError.from_exception_data(
            "PaperGroupingMapSpec",
            [{
                "type": "json_invalid",
                "loc": (),
                "msg": "EOF while parsing a string at line 1 column 4972",
                "input": '{"overview":"The shelf',
                "ctx": {"error": "EOF while parsing a string"},
            }],
        )

    monkeypatch.setattr(analyzer._client.messages, "parse", boom)

    try:
        analyzer._parse("group my shelf", object, heavy=True, thinking=False)
        assert False, "expected AnalysisError"
    except AnalysisError as exc:
        assert "truncated or invalid JSON" in str(exc)


def test_claude_paper_groups_retries_then_raises(monkeypatch):
    from app.demo_data import demo_projects

    analyzer = _analyzer(monkeypatch)
    projects = list(demo_projects().values())[:3]
    calls: list[dict] = []

    def fake_parse(prompt, schema, **kwargs):
        calls.append({
            "full": "abstract:" in prompt,
            "compact": "titles and tags only" in prompt,
            "brief": "ONE sentence (max 30 words)" in prompt,
        })
        raise AnalysisError("Structured output was truncated or invalid JSON — retrying with a more compact prompt.")

    monkeypatch.setattr(analyzer, "_parse", fake_parse)

    try:
        analyzer._claude_paper_groups(projects)
        assert False, "expected AnalysisError"
    except AnalysisError:
        pass

    assert len(calls) == 3
    assert calls[0] == {"full": True, "compact": False, "brief": False}
    assert calls[1] == {"full": False, "compact": True, "brief": False}
    assert calls[2] == {"full": False, "compact": False, "brief": True}


def test_find_paper_groups_falls_back_on_validation_error(monkeypatch):
    from app.demo_data import demo_projects

    analyzer = _analyzer(monkeypatch)
    projects = list(demo_projects().values())[:3]

    def boom(_projects):
        raise ValidationError.from_exception_data(
            "PaperGroupingMapSpec",
            [{
                "type": "json_invalid",
                "loc": (),
                "msg": "EOF while parsing a string",
                "input": '{"overview":"x',
                "ctx": {"error": "EOF"},
            }],
        )

    monkeypatch.setattr(analyzer, "_claude_paper_groups", boom)

    result = analyzer.find_paper_groups(projects)
    assert result["groups"]
    assert result["_mock"] is True
