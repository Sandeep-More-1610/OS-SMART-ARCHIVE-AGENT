"""Regression coverage for Windows operation, path parsing and safe extraction."""
import stat
import tarfile
import zipfile

import pytest

from smart_archive_agent import execute_tool, handle_request
from smart_archive_agent.intent import _paths
from smart_archive_agent.planner import plan_local
from smart_archive_agent.security.validation import ValidationError
from smart_archive_agent.tools import archive
from smart_archive_agent.tools.encryption import find_gpg


@pytest.mark.parametrize("extension", ["tar", "tar.gz", "tar.bz2", "tar.xz", "zip"])
def test_every_archive_format_round_trips_with_spaces(tmp_path, extension):
    source = tmp_path / "My Project"
    source.mkdir()
    (source / "notes.txt").write_bytes(b"hello\x00world" * 100)
    packed = tmp_path / ("My Backup." + extension)
    restored = tmp_path / "Restored Files"
    assert handle_request(f'archive "{source}" to "{packed}"')["success"]
    assert execute_tool("inspect_archive", {"archive_path": str(packed)})["success"]
    assert handle_request(f'extract "{packed}" into "{restored}"')["success"]
    assert (restored / source.name / "notes.txt").read_bytes() == (source / "notes.txt").read_bytes()


@pytest.mark.parametrize("algorithm", ["gz", "bz2", "xz"])
@pytest.mark.parametrize("level", ["fast", "normal", "max"])
def test_compressors_round_trip_binary_data(tmp_path, algorithm, level):
    source = tmp_path / "data.bin"
    source.write_bytes(bytes(range(256)) * 100)
    compressed = tmp_path / ("compressed." + algorithm)
    restored = tmp_path / "restored.bin"
    archive.compress_file(str(source), str(compressed), algorithm, level)
    archive.decompress_file(str(compressed), str(restored))
    assert restored.read_bytes() == source.read_bytes()


@pytest.mark.parametrize("extension", ["zip", "tar"])
def test_extraction_never_overwrites_existing_files(tmp_path, extension):
    source = tmp_path / "data.txt"
    source.write_text("archive data")
    packed = tmp_path / ("data." + extension)
    archive.create_archive(str(source), str(packed))
    restored = tmp_path / "restored"
    restored.mkdir()
    existing = restored / source.name
    existing.write_text("keep this")
    with pytest.raises(ValidationError, match="overwrite"):
        archive.extract_archive(str(packed), str(restored))
    assert existing.read_text() == "keep this"


def test_empty_zip_preserves_source_folder(tmp_path):
    source = tmp_path / "empty"
    source.mkdir()
    packed = tmp_path / "empty.zip"
    archive.create_archive(str(source), str(packed))
    archive.extract_archive(str(packed), str(tmp_path / "restored"))
    assert (tmp_path / "restored" / "empty").is_dir()


def test_direct_tool_cannot_archive_filesystem_root(tmp_path):
    result = execute_tool("create_archive", {"source_path": tmp_path.anchor,
                                            "output_path": str(tmp_path / "root.tar")})
    assert not result["success"] and "root filesystem" in result["error"]


def test_zip_symbolic_links_are_rejected_before_extraction(tmp_path):
    packed = tmp_path / "link.zip"
    with zipfile.ZipFile(packed, "w") as zf:
        link = zipfile.ZipInfo("link")
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        zf.writestr(link, "../outside")
    destination = tmp_path / "restored"
    with pytest.raises(ValidationError, match="links"):
        archive.extract_archive(str(packed), str(destination))
    assert not destination.exists()


def test_tar_special_files_are_rejected_before_extraction(tmp_path):
    packed = tmp_path / "device.tar"
    with tarfile.open(packed, "w") as tf:
        member = tarfile.TarInfo("pipe")
        member.type = tarfile.FIFOTYPE
        tf.addfile(member)
    with pytest.raises(ValidationError, match="special files"):
        archive.extract_archive(str(packed), str(tmp_path / "restored"))
    assert not (tmp_path / "restored").exists()


@pytest.mark.parametrize("name", ["../outside", "C:/outside", r"..\outside", "/outside"])
def test_zip_unsafe_paths_are_rejected(tmp_path, name):
    packed = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(packed, "w") as zf:
        zf.writestr(name, "unsafe")
    with pytest.raises(ValidationError, match="escapes"):
        archive.extract_archive(str(packed), str(tmp_path / "restored"))
    assert not (tmp_path / "restored").exists()


def test_quoted_paths_keep_case_spaces_and_keyword_names():
    plan = plan_local('archive "./Encrypt Project" to "./Backup.zip"')
    assert len(plan.steps) == 1
    assert plan.steps[0].tool == "create_archive"
    assert plan.steps[0].args["source_path"] == "./Encrypt Project"
    assert plan.steps[0].args["output_path"] == "./Backup.zip"


def test_windows_drive_paths_are_not_split_at_spaces():
    assert _paths(r"archive C:\Users\Some User\project to C:\Users\Some User\backup.zip") == [
        r"C:\Users\Some User\project", r"C:\Users\Some User\backup.zip"]


def test_case_sensitive_folder_phrase_is_preserved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "MyDocs").mkdir()
    assert plan_local("archive my MyDocs folder").steps[0].args["source_path"] == "./MyDocs"


def test_named_archive_output_without_extension_is_honored(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "source").mkdir()
    plan = plan_local('archive ./source to "./backup"')
    assert plan.steps[0].args["output_path"] == "./backup"


def test_passphrase_callback_failure_returns_error(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("secret")

    def unavailable(tool):
        raise ValidationError("Passphrases did not match.")

    result = handle_request(f'encrypt "{source}"', passphrase=unavailable)
    assert not result["success"]
    assert "did not match" in result["error"]
    assert result["completed_steps"] == 0


@pytest.mark.skipif(find_gpg() is None, reason="GPG not installed")
def test_unicode_passphrase_round_trip_and_existing_output_protection(tmp_path):
    source = tmp_path / "source.txt"
    source.write_bytes(b"secret\x00payload")
    encrypted = tmp_path / "encrypted.gpg"
    restored = tmp_path / "restored.txt"
    secret = "a long passphrase with unicode \u00e9\u03bb\u6f22"
    assert execute_tool("encrypt_file", {"source_path": str(source), "output_path": str(encrypted)}, passphrase=secret)["success"]
    assert execute_tool("decrypt_file", {"source_path": str(encrypted), "output_path": str(restored)}, passphrase=secret)["success"]
    assert restored.read_bytes() == source.read_bytes()
    original = encrypted.read_bytes()
    assert not execute_tool("encrypt_file", {"source_path": str(source), "output_path": str(encrypted)}, passphrase=secret)["success"]
    assert encrypted.read_bytes() == original


@pytest.mark.skipif(find_gpg() is None, reason="GPG not installed")
def test_multiline_passphrase_is_rejected_without_output(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("secret")
    output = tmp_path / "output.gpg"
    result = execute_tool("encrypt_file", {"source_path": str(source), "output_path": str(output)}, passphrase="first\nsecond")
    assert not result["success"] and "newline" in result["error"]
    assert not output.exists()
