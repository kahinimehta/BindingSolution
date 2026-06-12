"""Analyzer error handling and grouping retries."""
from pydantic import ValidationError

from app.analysis import AnalysisError, Analyzer
from app.config import get_settings


def _analyzer(monkeypatch) -> Analyzer:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("MOCK_LLM", "false")
    return Analyzer(get_settings())


def test_needs_streaming_for_large_grouping_budget(monkeypatch):
    analyzer = _analyzer(monkeypatch)
    assert analyzer._needs_streaming(_MAX_TOKENS_GROUPS := 32000) is True
    assert analyzer._needs_streaming(16000) is False
    assert analyzer._needs_streaming(4000) is False


def test_structured_response_uses_stream_for_large_max_tokens(monkeypatch):
    from app.analysis import _MAX_TOKENS_GROUPS
    from app.schemas import PaperGroupingMapSpec

    analyzer = _analyzer(monkeypatch)
    stream_calls: list[dict] = []
    parse_calls: list[dict] = []

    class FakeParsed:
        stop_reason = "end_turn"
        parsed_output = PaperGroupingMapSpec(overview="ok", groups=[], drops=[])

    class FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get_final_message(self):
            return FakeParsed()

    def fake_stream(**kwargs):
        stream_calls.append(kwargs)
        return FakeStream()

    def fake_parse(**kwargs):
        parse_calls.append(kwargs)
        raise ValueError(
            "Streaming is required for operations that may take longer than 10 minutes."
        )

    monkeypatch.setattr(analyzer._client.messages, "stream", fake_stream)
    monkeypatch.setattr(analyzer._client.messages, "parse", fake_parse)

    result = analyzer._structured_response({
        "model": analyzer.model,
        "max_tokens": _MAX_TOKENS_GROUPS,
        "system": "sys",
        "messages": [{"role": "user", "content": "hi"}],
        "output_format": PaperGroupingMapSpec,
    })
    assert result.parsed_output.overview == "ok"
    assert stream_calls and not parse_calls


def test_structured_response_polls_cancel_check_during_stream(monkeypatch):
    from app.schemas import ConnectionMap

    analyzer = _analyzer(monkeypatch)
    cancel_checks: list[int] = []

    class FakeParsed:
        stop_reason = "end_turn"
        parsed_output = ConnectionMap(
            overview="ok",
            shared_threads=[],
            clusters=[],
            suggested_combination=[],
        )

    class FakeStream:
        def __iter__(self):
            yield from range(3)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def get_final_message(self):
            return FakeParsed()

    parse_calls: list[dict] = []

    monkeypatch.setattr(analyzer._client.messages, "stream", lambda **_kwargs: FakeStream())
    monkeypatch.setattr(
        analyzer._client.messages,
        "parse",
        lambda **kwargs: parse_calls.append(kwargs),
    )

    result = analyzer._structured_response({
        "model": analyzer.model,
        "max_tokens": 4000,
        "system": "sys",
        "messages": [{"role": "user", "content": "hi"}],
        "output_format": ConnectionMap,
    }, cancel_check=lambda: cancel_checks.append(1))
    assert result.parsed_output.overview == "ok"
    assert cancel_checks == [1, 1, 1]
    assert not parse_calls


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
