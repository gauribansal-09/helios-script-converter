"""Smoke tests for the conversion agent."""

import asyncio
import zipfile
from pathlib import Path

import pytest

from helios_converter.agent import run_conversion


@pytest.fixture
def sample_zip(tmp_path: Path) -> Path:
    """Minimal zip with one Python file and one SQL file."""
    py_content = (
        "import snowflake.connector\n"
        "conn = snowflake.connector.connect(account='test', user='u')\n"
        "query = 'SELECT 1 FROM MY_DB.MY_SCHEMA.MY_TABLE'\n"
    )
    sql_content = "SELECT * FROM MY_DB.MY_SCHEMA.ORDERS WHERE dt = CURRENT_DATE();\n"

    zip_path = tmp_path / "input.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("script.py", py_content)
        zf.writestr("query.sql", sql_content)
    return zip_path


@pytest.mark.asyncio
async def test_run_conversion_creates_output_dir(sample_zip: Path, tmp_path: Path) -> None:
    output_folder = str(tmp_path / "output")
    await run_conversion(str(sample_zip), output_folder)
    assert Path(output_folder).exists()


@pytest.mark.asyncio
async def test_run_conversion_writes_updates_md(sample_zip: Path, tmp_path: Path) -> None:
    output_folder = str(tmp_path / "output")
    await run_conversion(str(sample_zip), output_folder)
    assert (Path(output_folder) / "UPDATES.md").exists()
