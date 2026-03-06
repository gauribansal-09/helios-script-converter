"""
Orchestrator: single query() entry point.

Python's only job here:
  1. Load the orchestrator prompt and inject runtime values
  2. Register the ingest_zip custom tool
  3. Start the agent loop and parse the structured JSON result
  4. Print the terminal summary

All conversion work, filesystem writes, and report generation are done by
Claude via tools, subagents, and skills.
"""

import json
import logging
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, query

from helios_converter.exceptions import ConversionError
from helios_converter.models import ConversionResult
from helios_converter.tools import create_ingest_server

logger = logging.getLogger(__name__)

_PROMPT_FILE = Path(__file__).parent.parent.parent / "prompts" / "orchestrator.md"


def _build_prompt(zip_path: str, output_folder: str) -> str:
    template = _PROMPT_FILE.read_text(encoding="utf-8")
    return template.replace("{{ZIP_PATH}}", zip_path).replace("{{OUTPUT_FOLDER}}", output_folder)


def _parse_results(raw: str) -> list[ConversionResult]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        data = json.loads(clean)
    return [ConversionResult(**r) for r in data.get("results", [])]


def _print_summary(results: list[ConversionResult], output_folder: str) -> None:
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    total_queries = sum(r.queries_processed for r in results if r.success)

    print(f"""
Conversion Complete
-------------------
Total Files:      {len(results)}
Converted:        {successful}
Failed:           {failed}
Queries:          {total_queries}
Output:           {output_folder}
""")
    for r in results:
        status = "OK" if r.success else "FAIL"
        out = Path(r.output).name if r.output else "—"
        print(f"  [{status}] {r.file_type:6} | {r.file:30} → {out}")


async def run_conversion(zip_path: str, output_folder: str) -> None:
    Path(output_folder).mkdir(parents=True, exist_ok=True)

    prompt = _build_prompt(zip_path, output_folder)
    results: list[ConversionResult] = []

    try:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                allowed_tools=["Task", "Read", "Write", "Glob", "helios__ingest_zip"],
                mcp_servers={"helios": create_ingest_server()},
                max_turns=100,
                setting_sources=["project"],
            ),
        ):
            if message.type == "result":
                results = _parse_results(message.result)

    except Exception as e:
        raise ConversionError("Agent failed to complete conversion run", cause=e) from e

    _print_summary(results, output_folder)
