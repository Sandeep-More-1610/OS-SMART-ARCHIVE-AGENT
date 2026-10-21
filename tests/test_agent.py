"""Tests for planning, chaining, encryption, guardrails and the integration interface."""

import os
import shutil
import tarfile
import zipfile
from pathlib import Path

import pytest

from smart_archive_agent import handle_request, get_tools, execute_tool
from smart_archive_agent.planner import Plan, Step, plan_local, validate_plan
from smart_archive_agent.security.guardrails import check_request

needs_gpg = pytest.mark.skipif(shutil.which("gpg") is None, reason="gpg is not installed")


@pytest.fixture
def project(tmp_path, monkeypatch):
    proj = tmp_path / "project"
    (proj / "src").mkdir(parents=True)
    (proj / "src" / "main.py").write_text("print('hello')\n" * 2000, encoding="utf-8")
    (proj / "README.md").write_text("Smart Archive Agent " * 2000, encoding="utf-8")
    monkeypatch.chdir(proj)
    return proj


# --- Planning: the brief's example and other chained intents -----------------

def test_brief_example_plans_archive_heavy_compression_and_encryption(project):
    plan = plan_local("Zip up my project folder, compress it heavily, and encrypt it.")
    assert plan.status == "ok"
    assert [s.tool for s in plan.steps] == ["create_archive", "encrypt_file", "remove_intermediate"]
    assert plan.steps[0].args["level"] == "max"
    assert plan.steps[0].args["compression"] == "xz"
    assert Path(plan.steps[0].args["source_path"]).resolve() == project
    assert plan.steps[1].args["source_path"] == plan.steps[0].args["output_path"]


def test_user_named_intermediate_archive_is_kept(project):
    plan = plan_local("Archive ./src to ../src.tar.xz and encrypt ../src.tar.xz ../src.tar.xz.gpg")
    assert [s.tool for s in plan.steps] == ["create_archive", "encrypt_file"]
    assert plan.steps[1].args["output_path"] == "../src.tar.xz.gpg"


@pytest.mark.parametrize("text, tool, extra", [
    ("compress ./README.md quickly", "compress_file", {"algorithm": "gz", "level": "fast"}),
    ("create a zip file of ./src", "create_archive", {"compression": "zip"}),
    ("back up ./src with bzip2", "create_archive", {"compression": "bz2"}),
    ("compress ./src heavily into ./src.tar.xz", "create_archive", {"level": "max"}),
    ("Encrypt ./README.md", "encrypt_file", {}),
    ("inspect archive ./demo.tar.xz", "inspect_archive", {}),
    ("what is inside ./demo.zip", "list_archive", {}),
])
def test_single_step_plans(project, text, tool, extra):
    plan = plan_local(text)
    assert plan.status == "ok" and plan.steps[0].tool == tool
    for key, value in extra.items():
        assert plan.steps[0].args[key] == value


def test_keywords_inside_paths_do_not_change_the_plan(project):
    plan = plan_local("Encrypt ./backup.tar.xz ./backup.tar.xz.gpg")
    assert [s.tool for s in plan.steps] == ["encrypt_file"]


def test_missing_source_is_reported(project):
    plan = plan_local("extract the archive please")
    assert plan.status == "missing" and plan.missing == ["archive_path"]


# --- Guardrails and plan validation -----------------------------------------

@pytest.mark.parametrize("text", [
    "rm -rf / please", "Delete everything on my drive", "format the disk and wipe everything",
    "archive ./src; rm -rf ~", "dd if=/dev/zero of=/dev/sda", "compress $(cat /etc/shadow)",
])
def test_destructive_requests_are_blocked(text):
    assert check_request(text) is not None
    result = handle_request(text)
    assert result["success"] is False and result["operation"] == "blocked"


def test_out_of_scope_requests_are_rejected():
    assert handle_request("What is the weather today?")["operation"] == "unrelated"


def test_protected_system_locations_are_refused(project):
    result = execute_tool("create_archive", {"source_path": "./src", "output_path": "/etc/src.tar"})
    assert result["success"] is False and "protected" in result["error"]


def test_plan_cannot_delete_files_it_did_not_create(project):
    plan = Plan("ok", [Step("remove_intermediate", {"path": "./README.md"})])
    assert validate_plan(plan)


def test_cancelled_plan_changes_nothing(project):
    result = handle_request("archive ./src", confirm=lambda plan: False)
    assert result["operation"] == "cancelled"
    assert not any(project.glob("src.tar*"))


# --- Integration interface for the Agentic Shell ----------------------------

def test_tool_definitions_in_every_style():
    names = {t["name"] for t in get_tools()}
    assert {"create_archive", "extract_archive", "compress_file", "encrypt_file", "decrypt_file"} <= names
    assert all(t["type"] == "function" and "parameters" in t["function"] for t in get_tools("openai"))
    assert all("input_schema" in t for t in get_tools("anthropic"))


@pytest.mark.parametrize("name, args", [
    ("rm_rf", {"path": "/"}),
    ("create_archive", {"source_path": "./src"}),
    ("create_archive", {"source_path": "./src", "output_path": "./a.tar", "shell": "rm -rf /"}),
    ("create_archive", {"source_path": "./src", "output_path": "./a.tar", "level": "insane"}),
])
def test_invalid_model_tool_calls_are_rejected_without_running(project, name, args):
    result = execute_tool(name, args)
    assert result["success"] is False
    assert result["message"] == "The tool call was rejected before execution."
    assert not (project / "a.tar").exists()


def test_execute_tool_runs_a_valid_call(project):
    result = execute_tool("create_archive", {"source_path": "./src", "output_path": "./src.zip"})
    assert result["success"] is True and zipfile.is_zipfile(project / "src.zip")


# --- Real execution ---------------------------------------------------------

def test_heavy_compression_is_smaller_than_fast(project):
    fast = execute_tool("create_archive", {"source_path": "./src", "output_path": "../fast.tar.gz", "level": "fast"})
    heavy = execute_tool("create_archive", {"source_path": "./src", "output_path": "../heavy.tar.xz", "level": "max"})
    assert fast["success"] and heavy["success"]
    assert heavy["archive_bytes"] < fast["archive_bytes"]


def test_zip_round_trip(project, tmp_path):
    assert handle_request("create a zip file of ./src")["success"]
    result = handle_request(f"extract ./src.zip into {tmp_path / 'restored'}")
    assert result["success"]
    assert (tmp_path / "restored" / "src" / "main.py").read_text(encoding="utf-8").startswith("print")


def test_archive_cannot_be_written_inside_its_own_source(project):
    result = execute_tool("create_archive", {"source_path": ".", "output_path": "./self.tar.xz"})
    assert result["success"] is False


@needs_gpg
def test_brief_example_end_to_end_and_decrypt(project):
    result = handle_request("Zip up my project folder, compress it heavily, and encrypt it.",
                            passphrase="correct horse battery staple")
    assert result["success"], result
    encrypted = Path(result["output"])
    assert encrypted.name == "project.tar.xz.gpg" and encrypted.exists()
    assert not (project.parent / "project.tar.xz").exists()  # plaintext copy removed

    wrong = handle_request(f"decrypt {encrypted} {project.parent / 'x.tar.xz'}", passphrase="wrong")
    assert wrong["success"] is False and "wrong passphrase" in wrong["error"]
    assert not (project.parent / "x.tar.xz").exists()

    restored = handle_request(f"decrypt {encrypted} and extract it", passphrase="correct horse battery staple")
    assert restored["success"], restored
    assert (project.parent / "project-extracted" / "project" / "README.md").exists()


@needs_gpg
def test_encryption_without_passphrase_fails_safely(project):
    from smart_archive_agent.security.validation import ValidationError
    from smart_archive_agent.tools.encryption import encrypt_file
    with pytest.raises(ValidationError):
        encrypt_file("./README.md", "./README.md.gpg", passphrase=None)
    assert not (project / "README.md.gpg").exists()


def test_zip_slip_archive_is_refused(project, tmp_path):
    evil = tmp_path / "evil.tar"
    payload = tmp_path / "payload.txt"
    payload.write_text("owned")
    with tarfile.open(evil, "w") as tf:
        tf.add(payload, arcname="../../escaped.txt")
    result = execute_tool("extract_archive", {"archive_path": str(evil), "destination_path": str(tmp_path / "out")})
    assert result["success"] is False and "escapes" in result["error"]
    assert not (tmp_path.parent / "escaped.txt").exists()
    assert not (tmp_path / "out").exists()  # nothing is created before the scan passes


@pytest.mark.parametrize("text, tools", [
    ("unpack ./demo.tar.xz", ["extract_archive"]),
    ("squeeze ./src as small as possible, then lock it with a password",
     ["create_archive", "encrypt_file", "remove_intermediate"]),
    ("password-protect ./README.md", ["encrypt_file"]),
])
def test_everyday_phrasings(project, text, tools):
    assert [s.tool for s in plan_local(text).steps] == tools


def test_root_filesystem_is_blocked():
    assert handle_request("archive / to ./root.tar.xz")["operation"] == "blocked"
