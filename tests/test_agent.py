"""Unit tests for agent.py — no live SDK calls."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from helios_converter.agent import _build_prompt, _parse_results, _print_summary, run_conversion
from helios_converter.exceptions import ConversionError
from helios_converter.models import ConversionResult


# ---------------------------------------------------------------------------
# _build_prompt
# ---------------------------------------------------------------------------

class TestBuildPrompt:
    def test_injects_zip_path(self) -> None:
        prompt = _build_prompt("/data/input.zip", "/data/output")
        assert "/data/input.zip" in prompt
        assert "{{ZIP_PATH}}" not in prompt

    def test_injects_output_folder(self) -> None:
        prompt = _build_prompt("/data/input.zip", "/data/output")
        assert "/data/output" in prompt
        assert "{{OUTPUT_FOLDER}}" not in prompt

    def test_prompt_file_exists(self) -> None:
        # Verifies the template file is present — catches missing file early.
        prompt = _build_prompt("zip", "out")
        assert len(prompt) > 0


# ---------------------------------------------------------------------------
# _parse_results
# ---------------------------------------------------------------------------

class TestParseResults:
    def _result_json(self, **kwargs) -> str:
        defaults = {
            "file": "script.py",
            "file_type": "Python",
            "output": "out/script.py",
            "queries_processed": 1,
            "success": True,
            "error": None,
            "changes": ["removed snowflake import"],
        }
        defaults.update(kwargs)
        return json.dumps({"results": [defaults]})

    def test_parses_clean_json(self) -> None:
        raw = self._result_json()
        results = _parse_results(raw)
        assert len(results) == 1
        assert isinstance(results[0], ConversionResult)
        assert results[0].file == "script.py"

    def test_parses_json_with_markdown_fences(self) -> None:
        raw = "```json\n" + self._result_json() + "\n```"
        results = _parse_results(raw)
        assert len(results) == 1

    def test_empty_results_key(self) -> None:
        raw = json.dumps({"results": []})
        assert _parse_results(raw) == []

    def test_missing_results_key(self) -> None:
        raw = json.dumps({})
        assert _parse_results(raw) == []

    def test_multiple_results(self) -> None:
        data = {
            "results": [
                {"file": "a.py", "file_type": "Python", "success": True, "output": "a.py",
                 "queries_processed": 0, "error": None, "changes": []},
                {"file": "b.sql", "file_type": "SQL", "success": False, "output": None,
                 "queries_processed": 0, "error": "parse error", "changes": []},
            ]
        }
        results = _parse_results(json.dumps(data))
        assert len(results) == 2
        assert results[1].success is False


# ---------------------------------------------------------------------------
# _print_summary
# ---------------------------------------------------------------------------

class TestPrintSummary:
    def _make_results(self) -> list[ConversionResult]:
        return [
            ConversionResult(file="a.py", file_type="Python", success=True,
                             output="out/a.py", queries_processed=2),
            ConversionResult(file="b.sql", file_type="SQL", success=False,
                             output=None, error="parse error"),
        ]

    def test_shows_total_counts(self, capsys: pytest.CaptureFixture) -> None:
        _print_summary(self._make_results(), "/out")
        out = capsys.readouterr().out
        assert "Total Files:      2" in out
        assert "Converted:        1" in out
        assert "Failed:           1" in out

    def test_shows_query_count(self, capsys: pytest.CaptureFixture) -> None:
        _print_summary(self._make_results(), "/out")
        out = capsys.readouterr().out
        assert "Queries:          2" in out

    def test_shows_ok_and_fail_status(self, capsys: pytest.CaptureFixture) -> None:
        _print_summary(self._make_results(), "/out")
        out = capsys.readouterr().out
        assert "[OK]" in out
        assert "[FAIL]" in out

    def test_shows_output_folder(self, capsys: pytest.CaptureFixture) -> None:
        _print_summary([], "/my/output")
        out = capsys.readouterr().out
        assert "/my/output" in out


# ---------------------------------------------------------------------------
# run_conversion
# ---------------------------------------------------------------------------

def _fake_result_message(payload: dict) -> SimpleNamespace:
    return SimpleNamespace(type="result", result=json.dumps(payload))


def _mock_query(*messages):
    """Return an async generator that yields the given messages."""
    async def _gen(**kwargs):
        for msg in messages:
            yield msg
    return _gen


def _patches(query_mock):
    """Context manager that patches both query and create_ingest_server."""
    from unittest.mock import MagicMock
    from contextlib import ExitStack

    stack = ExitStack()
    stack.enter_context(patch("helios_converter.agent.query", query_mock))
    stack.enter_context(patch("helios_converter.agent.create_ingest_server", return_value=MagicMock()))
    return stack


class TestRunConversion:
    @pytest.mark.asyncio
    async def test_creates_output_directory(self, tmp_path: Path) -> None:
        output_folder = str(tmp_path / "out")
        msg = _fake_result_message({"results": []})

        with _patches(_mock_query(msg)):
            await run_conversion("input.zip", output_folder)

        assert Path(output_folder).exists()

    @pytest.mark.asyncio
    async def test_parses_result_message(self, tmp_path: Path) -> None:
        output_folder = str(tmp_path / "out")
        payload = {
            "results": [{
                "file": "script.py",
                "file_type": "Python",
                "output": "out/script.py",
                "queries_processed": 1,
                "success": True,
                "error": None,
                "changes": [],
            }]
        }
        msg = _fake_result_message(payload)

        with _patches(_mock_query(msg)):
            await run_conversion("input.zip", output_folder)

    @pytest.mark.asyncio
    async def test_wraps_exception_in_conversion_error(self, tmp_path: Path) -> None:
        output_folder = str(tmp_path / "out")

        async def _failing_query(**kwargs):
            raise RuntimeError("SDK exploded")
            yield  # make it an async generator

        with _patches(_failing_query):
            with pytest.raises(ConversionError, match="Agent failed"):
                await run_conversion("input.zip", output_folder)

    @pytest.mark.asyncio
    async def test_ignores_non_result_messages(self, tmp_path: Path) -> None:
        output_folder = str(tmp_path / "out")
        non_result = SimpleNamespace(type="assistant", content="thinking...")
        result = _fake_result_message({"results": []})

        with _patches(_mock_query(non_result, result)):
            await run_conversion("input.zip", output_folder)
