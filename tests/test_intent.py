from app.intent import classify

def test_unrelated_request_is_rejected():
    assert classify("What is the weather today?").operation == "unrelated"

def test_archive_request_is_recognized():
    result = classify("Create an archive of ./demo")
    assert result.operation == "create_archive"

def test_extract_request_is_recognized():
    result = classify("Extract ./backup.tar.xz into ./out")
    assert result.operation == "extract_archive"

def test_empty_request():
    assert classify("").operation == "unknown"


def test_archive_paths_are_not_confused_with_instruction_words():
    result = classify("Create an archive of ./demo ./demo.tar.xz")
    assert result.operation == "create_archive"
    assert result.args["source_path"] == "./demo"
    assert result.args["output_path"] == "./demo.tar.xz"

def test_extract_paths_are_mapped_correctly():
    result = classify("Extract ./backup.tar.xz into ./out")
    assert result.operation == "extract_archive"
    assert result.args["archive_path"] == "./backup.tar.xz"
    assert result.args["destination_path"] == "./out"

def test_encrypt_paths_are_mapped_correctly():
    result = classify("Encrypt ./backup.tar.xz ./backup.tar.xz.gpg")
    assert result.operation == "encrypt_file"
    assert result.args["source_path"] == "./backup.tar.xz"
    assert result.args["output_path"] == "./backup.tar.xz.gpg"
