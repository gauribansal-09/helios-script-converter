"""
Agent SDK custom tool: ingest_zip

Claude calls this at the start of the orchestration. It extracts the input zip
and returns categorized file paths. All filesystem work happens here — the agent
never touches the zip directly.
"""

import asyncio
import logging
import tempfile
import zipfile
from pathlib import Path

from claude_agent_sdk import create_sdk_mcp_server
from claude_agent_sdk.types import McpSdkServerConfig
from pydantic import BaseModel

from claude_agent_sdk import tool as sdk_tool

from helios_converter.utils import scan_directory

logger = logging.getLogger(__name__)

# Module-level handle so the temp dir stays alive for the agent's lifetime
_tmp_dir: tempfile.TemporaryDirectory | None = None


class _IngestInput(BaseModel):
    zip_path: str


async def ingest_zip(zip_path: str) -> dict:
    """
    Extract a zip archive of Snowflake scripts and return categorized file paths.

    Args:
        zip_path: Absolute path to the .zip file containing the scripts to convert.

    Returns:
        {
            "extracted_to": str,
            "python_files": [str, ...],
            "sql_files": [str, ...],
            "config_files": [str, ...],
            "total_files": int,
        }
    """
    global _tmp_dir

    _tmp_dir = tempfile.TemporaryDirectory()
    extract_to = Path(_tmp_dir.name)

    logger.info("Extracting %s → %s", zip_path, extract_to)

    def _extract() -> None:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(extract_to)

    await asyncio.to_thread(_extract)
    logger.info("Extraction complete")

    config_exts = [".ini", ".txt", ".yaml", ".yml", ".toml"]
    py_files, sql_files, cfg_files = await asyncio.gather(
        asyncio.to_thread(scan_directory, extract_to, [".py"]),
        asyncio.to_thread(scan_directory, extract_to, [".sql"]),
        asyncio.to_thread(scan_directory, extract_to, config_exts),
    )

    result = {
        "extracted_to": str(extract_to),
        "python_files": [str(f) for f in py_files],
        "sql_files": [str(f) for f in sql_files],
        "config_files": [str(f) for f in cfg_files],
        "total_files": len(py_files) + len(sql_files) + len(cfg_files),
    }

    logger.info(
        "Found %d files: %d .py, %d .sql, %d config",
        result["total_files"], len(py_files), len(sql_files), len(cfg_files),
    )
    return result


def create_ingest_server() -> McpSdkServerConfig:
    """Build an SDK MCP server that exposes ingest_zip as a tool to Claude."""

    @sdk_tool(
        name="ingest_zip",
        description=(
            "Extract a zip archive of Snowflake scripts and return categorized file paths. "
            "Call this first before any conversion work."
        ),
        input_schema=_IngestInput,
    )
    async def _handler(inp: _IngestInput) -> dict:
        return await ingest_zip(inp.zip_path)

    return create_sdk_mcp_server("helios", tools=[_handler])
