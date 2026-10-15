"""End-to-end tests for SmartArchiveAgent."""

from pathlib import Path
from app.agent import SmartArchiveAgent


def test_agent_archive_and_extract(tmp_path):
    src = tmp_path / "data"
    src.mkdir()
    (src / "sample.txt").write_text("Hello agent!", encoding="utf-8")

    archive_target = tmp_path / "test_out.zip"
    extract_target = tmp_path / "extracted_data"

    agent = SmartArchiveAgent()

    # 1. Archive
    res_arch = agent.execute(
        f"archive {src} to {archive_target}"
    )
    assert res_arch.success is True
    assert archive_target.exists()
    assert len(agent.audit_log) >= 1

    # 2. Verify
    res_ver = agent.execute(f"verify {archive_target}")
    assert res_ver.success is True

    # 3. List
    res_list = agent.execute(f"list {archive_target}")
    assert res_list.success is True
    assert res_list.metrics["count"] >= 1

    # 4. Extract
    res_ext = agent.execute(
        f"extract {archive_target} into {extract_target}"
    )
    assert res_ext.success is True
    assert (extract_target / "data" / "sample.txt").exists()


def test_agent_archive_encrypt_and_decrypt_pipeline(tmp_path):
    src = tmp_path / "confidential"
    src.mkdir()
    (src / "classified.txt").write_text("Top secret material", encoding="utf-8")

    enc_archive = tmp_path / "secure_archive.zip.enc"
    restore_dir = tmp_path / "restored_secure"

    agent = SmartArchiveAgent()

    # 1. Archive and Encrypt in one command
    res_arch = agent.execute(
        f"archive {src} to {enc_archive} and encrypt with password AgentSecretPass42!"
    )
    assert res_arch.success is True
    assert enc_archive.exists()

    # 2. Extract and Decrypt
    res_ext = agent.execute(
        f"extract {enc_archive} into {restore_dir} with password AgentSecretPass42!"
    )
    assert res_ext.success is True
    assert (restore_dir / "confidential" / "classified.txt").read_text(encoding="utf-8") == "Top secret material"


def test_agent_dry_run(tmp_path):
    src = tmp_path / "dummy"
    src.mkdir()
    target = tmp_path / "should_not_exist.zip"

    agent = SmartArchiveAgent()
    res = agent.execute(f"archive {src} to {target} --dry-run")

    assert res.success is True
    assert res.metrics.get("dry_run") is True
    assert not target.exists()
    assert len(res.plan) > 0
