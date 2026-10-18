import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent import run, handle_request

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        result = handle_request(query)
        print(result.get("message", ""))
        if result.get("output"):
            print("Output:", result["output"])
        if result.get("entries"):
            for item in result["entries"][:30]:
                print(" -", item)
            if len(result["entries"]) > 30:
                print(f" ... and {len(result['entries']) - 30} more")
        if result.get("error"):
            print("Error:", result["error"])
            sys.exit(1)
    else:
        run()


