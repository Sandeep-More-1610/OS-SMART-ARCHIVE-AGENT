"""End-to-end integration tests for Smart Archive Agent in WSL."""

import shutil
from pathlib import Path
import pytest

from app.security.validation import (
    resolve_existing_path,
    resolve_output_path,
    reject_same_path,
    ValidationError,
)
from app.tools import archive
from app.agent import handle_request


def test_validation_rules(tmp_path):
    # Non-existent path
    with pytest.raises(ValidationError):
        resolve_existing_path(str(tmp_path / "does_not_exist"))

    # Empty path
    with pytest.raises(ValidationError):
        resolve_existing_path("")

    # Same path rejection
    sample = tmp_path / "sample.txt"
    sample.write_text("data")
    with pytest.raises(ValidationError):
        reject_same_path(sample, sample)


def test_archive_creation_listing_extraction(tmp_path):
    source_dir = tmp_path / "my_source"
    source_dir.mkdir()
    (source_dir / "file1.txt").write_text("Hello WSL", encoding="utf-8")
    (source_dir / "file2.txt").write_text("Team 12", encoding="utf-8")

    archive_path = tmp_path / "backup.tar.xz"

    # 1. Create Archive
    res_create = archive.create_archive(str(source_dir), str(archive_path), compression="xz")
    assert res_create["success"] is True
    assert archive_path.exists()

    # 2. List Archive
    res_list = archive.list_archive(str(archive_path))
    assert res_list["success"] is True
    assert any("file1.txt" in e for e in res_list["entries"])

    # 3. Inspect Archive
    res_inspect = archive.inspect_archive(str(archive_path))
    assert res_inspect["success"] is True
    assert res_inspect["entries_count"] >= 2

    # 4. Extract Archive
    dest_dir = tmp_path / "extracted"
    res_extract = archive.extract_archive(str(archive_path), str(dest_dir))
    assert res_extract["success"] is True
    assert (dest_dir / "my_source" / "file1.txt").read_text(encoding="utf-8") == "Hello WSL"


def test_compress_and_decompress_file(tmp_path):
    single_file = tmp_path / "large_log.txt"
    single_file.write_text("A" * 1000, encoding="utf-8")

    compressed_file = tmp_path / "large_log.txt.xz"
    res_comp = archive.compress_file(str(single_file), str(compressed_file), algorithm="xz")
    assert res_comp["success"] is True
    assert compressed_file.exists()

    decompressed_file = tmp_path / "restored_log.txt"
    res_decomp = archive.decompress_file(str(compressed_file), str(decompressed_file))
    assert res_decomp["success"] is True
    assert decompressed_file.read_text(encoding="utf-8") == "A" * 1000


def test_agent_handle_request_pipeline(tmp_path):
    data_dir = tmp_path / "docs_folder"
    data_dir.mkdir()
    (data_dir / "doc.txt").write_text("Project content", encoding="utf-8")

    out_tar = tmp_path / "project.tar.xz"

    # Test agent request
    cmd = f"archive {data_dir} to {out_tar}"
    res = handle_request(cmd)
    assert res["success"] is True
    assert out_tar.exists()

    # Test inspect via agent
    inspect_cmd = f"inspect archive {out_tar}"
    res_insp = handle_request(inspect_cmd)
    assert res_insp["success"] is True

    # Test list via agent
    list_cmd = f"list archive {out_tar}"
    res_list = handle_request(list_cmd)
    assert res_list["success"] is True

    # Test exit command
    res_exit = handle_request("exit")
    assert res_exit["operation"] == "exit"

    # Test unrelated query
    res_unrel = handle_request("What is the weather in Delhi?")
    assert res_unrel["operation"] == "unrelated"


def test_calculate_checksum(tmp_path):
    from app.security.validation import calculate_checksum
    test_file = tmp_path / "checksum_test.txt"
    test_file.write_text("Integrity validation content", encoding="utf-8")
    digest = calculate_checksum(test_file)
    assert len(digest) == 64
    assert isinstance(digest, str)


def test_output_already_exists_rejection(tmp_path):
    src = tmp_path / "src.txt"
    src.write_text("hello", encoding="utf-8")
    existing_out = tmp_path / "existing.tar.xz"
    existing_out.write_text("existing content", encoding="utf-8")

    with pytest.raises(ValidationError) as exc:
        archive.create_archive(str(src), str(existing_out))
    assert "Output already exists" in str(exc.value)


def test_missing_argument_prompt():
    res = handle_request("archive ./some_folder")
    assert res["success"] is False
    assert "missing" in res
    assert "output_path" in res["missing"]

