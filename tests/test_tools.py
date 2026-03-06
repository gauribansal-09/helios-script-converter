import zipfile
from pathlib import Path

import pytest

from helios_converter.tools import ingest_zip


def _make_zip(tmp_path: Path, files: dict[str, str]) -> Path:
    """Create a zip at tmp_path/input.zip with the given {name: content} entries."""
    zip_path = tmp_path / "input.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return zip_path


@pytest.mark.asyncio
async def test_python_files_categorised(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {"script.py": "print('hello')"})
    result = await ingest_zip(str(zip_path))
    assert len(result["python_files"]) == 1
    assert result["python_files"][0].endswith("script.py")
    assert result["sql_files"] == []
    assert result["config_files"] == []


@pytest.mark.asyncio
async def test_sql_files_categorised(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {"query.sql": "SELECT 1"})
    result = await ingest_zip(str(zip_path))
    assert len(result["sql_files"]) == 1
    assert result["sql_files"][0].endswith("query.sql")


@pytest.mark.asyncio
@pytest.mark.parametrize("filename", ["config.yaml", "config.yml", "config.ini", "config.toml", "notes.txt"])
async def test_config_files_categorised(tmp_path: Path, filename: str) -> None:
    zip_path = _make_zip(tmp_path, {filename: "key=value"})
    result = await ingest_zip(str(zip_path))
    assert len(result["config_files"]) == 1


@pytest.mark.asyncio
async def test_total_files_count(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {
        "a.py": "",
        "b.sql": "",
        "c.yaml": "",
    })
    result = await ingest_zip(str(zip_path))
    assert result["total_files"] == 3


@pytest.mark.asyncio
async def test_nested_directory_structure(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {
        "pkg/module.py": "x = 1",
        "pkg/sub/query.sql": "SELECT 1",
    })
    result = await ingest_zip(str(zip_path))
    assert len(result["python_files"]) == 1
    assert len(result["sql_files"]) == 1


@pytest.mark.asyncio
async def test_empty_zip_returns_empty_lists(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {"readme.md": "# docs"})
    result = await ingest_zip(str(zip_path))
    assert result["python_files"] == []
    assert result["sql_files"] == []
    assert result["config_files"] == []
    assert result["total_files"] == 0


@pytest.mark.asyncio
async def test_extracted_to_is_string(tmp_path: Path) -> None:
    zip_path = _make_zip(tmp_path, {"a.py": ""})
    result = await ingest_zip(str(zip_path))
    assert isinstance(result["extracted_to"], str)
    assert Path(result["extracted_to"]).is_dir()
