from app.intent import classify
from app.tools import archive, encryption

TOOL_MAP = {
    "create_archive": archive.create_archive,
    "extract_archive": archive.extract_archive,
    "list_archive": archive.list_archive,
    "inspect_archive": archive.inspect_archive,
    "compress_file": archive.compress_file,
    "decompress_file": archive.decompress_file,
    "encrypt_file": encryption.encrypt_file,
    "decrypt_file": encryption.decrypt_file,
}

def handle_request(text: str) -> dict:
    intent = classify(text)
    if intent.operation == "exit":
        return {"success": True, "operation": "exit", "message": "Goodbye."}
    if intent.operation == "unrelated":
        return {"success": False, "operation": "unrelated",
                "message": intent.message or "That request is outside the Smart Archive Agent's scope."}
    if intent.operation == "unknown":
        return {"success": False, "operation": "unknown", "message": intent.message}
    if intent.missing:
        return {"success": False, "operation": intent.operation,
                "missing": intent.missing,
                "message": "I recognized an archive-related request, but need these details: " + ", ".join(intent.missing)}
    try:
        result = TOOL_MAP[intent.operation](**intent.args)
        return result
    except Exception as exc:
        return {"success": False, "operation": intent.operation, "error": str(exc),
                "message": "The operation could not be completed. Review the error and try again."}

def run():
    print("Smart Archive Agent (Ubuntu)")
    print("Archive, compress, extract, inspect, encrypt, and decrypt files.")
    print("Type 'exit' to quit. This initial version uses a local intent router.")
    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break
        result = handle_request(text)
        if result.get("operation") == "exit":
            print(result["message"])
            break
        print("\nAgent:")
        print(result.get("message", ""))
        if result.get("success") and result.get("output"):
            print("Output:", result["output"])
        if result.get("entries") is not None:
            for item in result["entries"][:30]:
                print(" -", item)
            if len(result["entries"]) > 30:
                print(f" ... and {len(result['entries']) - 30} more")
        if result.get("error"):
            print("Error:", result["error"])
