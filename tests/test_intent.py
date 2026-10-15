"""Tests for intent parser."""

from app.intent import ActionType, IntentParser


def test_parse_archive_intent():
    parser = IntentParser()
    intent = parser.parse("archive folder src into backup.zip")

    assert intent.action == ActionType.ARCHIVE
    assert "src" in intent.sources or "backup.zip" == intent.destination
    assert intent.destination == "backup.zip"
    assert intent.format == "zip"


def test_parse_tar_gz_intent():
    parser = IntentParser()
    intent = parser.parse("compress data folder to archive.tar.gz")

    assert intent.action == ActionType.ARCHIVE
    assert intent.format == "tar.gz"
    assert intent.destination == "archive.tar.gz"


def test_parse_extract_intent():
    parser = IntentParser()
    intent = parser.parse("extract package.zip into ./output_dir")

    assert intent.action == ActionType.EXTRACT
    assert intent.destination == "./output_dir"


def test_parse_archive_with_encryption():
    parser = IntentParser()
    intent = parser.parse("archive logs to backup.zip and encrypt with password SecretPassword99")

    assert intent.action == ActionType.ARCHIVE
    assert intent.encrypt is True
    assert intent.password == "SecretPassword99"


def test_parse_decrypt_intent():
    parser = IntentParser()
    intent = parser.parse("decrypt confidential.enc to plain.zip with password my_pass")

    assert intent.action == ActionType.DECRYPT
    assert intent.password == "my_pass"


def test_parse_list_and_verify():
    parser = IntentParser()
    intent_list = parser.parse("list contents of bundle.zip")
    assert intent_list.action == ActionType.LIST

    intent_ver = parser.parse("verify integrity of backup.tar.gz")
    assert intent_ver.action == ActionType.VERIFY


def test_parse_dry_run_flag():
    parser = IntentParser()
    intent = parser.parse("archive src to dist.zip --dry-run")
    assert intent.dry_run is True


def test_parse_filters():
    parser = IntentParser()
    intent = parser.parse("archive all .py files from src to py_bundle.zip")
    assert ".py" in intent.filters.get("include_extensions", [])
