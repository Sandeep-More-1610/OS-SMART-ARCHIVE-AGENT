"""Tests for archive creation, extraction, listing, and verification."""

import pytest
from app.tools.archive import (
    create_archive,
    detect_format,
    extract_archive,
    inspect_archive,
    list_archive,
    verify_archive,
)
from app.security.validation import PathTraversalError


def test_detect_format():
    assert detect_format("backup.zip") == "zip"
    assert detect_format("backup.tar.gz") == "tar.gz"
    assert detect_format("backup.tgz") == "tar.gz"
    assert detect_format("backup.tar.bz2") == "tar.bz2"
    assert detect_format("backup.tar.xz") == "tar.xz"
    assert detect_format("backup.tar") == "tar"


def test_zip_create_and_extract(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "file1.txt").write_text("file 1 content", encoding="utf-8")
    (src_dir / "file2.py").write_text("print('hello')", encoding="utf-8")

    archive_out = tmp_path / "bundle.zip"
    created = create_archive(src_dir, archive_out)
    assert created.exists()

    dest_dir = tmp_path / "extracted"
    extracted = extract_archive(created, dest_dir)
    assert len(extracted) == 2

    # Check extracted content
    content1 = (dest_dir / "src" / "file1.txt").read_text(encoding="utf-8")
    assert content1 == "file 1 content"


def test_tar_gz_create_and_extract(tmp_path):
    src_dir = tmp_path / "src_tar"
    src_dir.mkdir()
    (src_dir / "data.csv").write_text("col1,col2\n1,2", encoding="utf-8")

    archive_out = tmp_path / "bundle.tar.gz"
    created = create_archive(src_dir, archive_out, format="tar.gz")
    assert created.exists()

    dest_dir = tmp_path / "extracted_tar"
    extracted = extract_archive(created, dest_dir)
    assert len(extracted) == 1
    assert (dest_dir / "src_tar" / "data.csv").read_text(encoding="utf-8") == "col1,col2\n1,2"


def test_archive_filtering(tmp_path):
    src_dir = tmp_path / "mixed"
    src_dir.mkdir()
    (src_dir / "script.py").write_text("code", encoding="utf-8")
    (src_dir / "notes.txt").write_text("notes", encoding="utf-8")
    (src_dir / "temp.log").write_text("log", encoding="utf-8")

    archive_out = tmp_path / "filtered.zip"
    # Filter only python files
    created = create_archive(
        src_dir,
        archive_out,
        filter_criteria={"include_extensions": [".py"]},
    )

    items = list_archive(created)
    filenames = [i["filename"] for i in items]
    assert any("script.py" in f for f in filenames)
    assert not any("notes.txt" in f for f in filenames)
    assert not any("temp.log" in f for f in filenames)


def test_list_and_verify_archive(tmp_path):
    src_file = tmp_path / "verify_me.txt"
    src_file.write_text("Verify test", encoding="utf-8")

    archive_out = tmp_path / "test_ver.zip"
    create_archive(src_file, archive_out)

    assert verify_archive(archive_out) is True

    items = list_archive(archive_out)
    assert len(items) == 1
    assert items[0]["filename"] == "verify_me.txt"

    inspection = inspect_archive(archive_out)
    assert inspection["is_safe"] is True
    assert inspection["file_count"] == 1
