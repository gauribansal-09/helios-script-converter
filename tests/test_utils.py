from pathlib import Path
from unittest.mock import patch

import pytest

from helios_converter.utils import read_file, scan_directory, write_file


class TestReadFile:
    def test_reads_content(self, tmp_path: Path) -> None:
        f = tmp_path / "hello.txt"
        f.write_text("hello world", encoding="utf-8")
        assert read_file(f) == "hello world"

    def test_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_file(tmp_path / "missing.txt")

    def test_raises_runtime_error_on_os_error(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("data", encoding="utf-8")
        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            with pytest.raises(RuntimeError, match="Error reading"):
                read_file(f)


class TestWriteFile:
    def test_creates_file(self, tmp_path: Path) -> None:
        f = tmp_path / "out.txt"
        write_file(f, "content")
        assert f.read_text(encoding="utf-8") == "content"

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        f = tmp_path / "a" / "b" / "c.txt"
        write_file(f, "nested")
        assert f.exists()

    def test_raises_runtime_error_on_os_error(self, tmp_path: Path) -> None:
        f = tmp_path / "out.txt"
        with patch.object(Path, "write_text", side_effect=OSError("disk full")):
            with pytest.raises(RuntimeError, match="Error writing"):
                write_file(f, "data")


class TestScanDirectory:
    def test_returns_all_files_when_no_filter(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").touch()
        (tmp_path / "b.sql").touch()
        result = scan_directory(tmp_path)
        assert len(result) == 2

    def test_filters_by_extension(self, tmp_path: Path) -> None:
        (tmp_path / "a.py").touch()
        (tmp_path / "b.sql").touch()
        result = scan_directory(tmp_path, [".py"])
        assert len(result) == 1
        assert result[0].suffix == ".py"

    def test_recursive(self, tmp_path: Path) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "nested.py").touch()
        result = scan_directory(tmp_path, [".py"])
        assert len(result) == 1
        assert result[0].name == "nested.py"

    def test_returns_empty_for_missing_directory(self, tmp_path: Path) -> None:
        result = scan_directory(tmp_path / "nonexistent")
        assert result == []

    def test_returns_sorted_paths(self, tmp_path: Path) -> None:
        (tmp_path / "c.py").touch()
        (tmp_path / "a.py").touch()
        (tmp_path / "b.py").touch()
        result = scan_directory(tmp_path, [".py"])
        names = [f.name for f in result]
        assert names == sorted(names)

    def test_excludes_directories(self, tmp_path: Path) -> None:
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.py").touch()
        result = scan_directory(tmp_path, [".py"])
        assert all(f.is_file() for f in result)
