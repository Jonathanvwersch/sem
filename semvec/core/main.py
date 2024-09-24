import sys
import json
import logging
import argparse
import asyncio
from typing import Dict, List
from services.index_repository import index_repository
from services.query_codebase import query_codebase

# Configure logging to use stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def output_json(data: List):
    """Output a JSON object with start and end markers."""
    print("START_JSON_OUTPUT")
    json.dump(data, sys.stdout)
    print("\nEND_JSON_OUTPUT")
    sys.stdout.flush()


async def main():
    parser = argparse.ArgumentParser(description="Local Code Search Tool")
    parser.add_argument("action", choices=["index", "query"], help="Action to perform")
    parser.add_argument(
        "--path", required=True, help="Path to the repository for indexing or querying"
    )
    parser.add_argument("--query", help="Query to search in the codebase")
    args = parser.parse_args()

    try:
        if args.action == "index":
            await index_repository(args.path)
            output_json({"status": "success", "action": "index", "path": args.path})
        elif args.action == "query":
            if not args.query:
                raise ValueError("Please provide a query using the --query argument")
            results = query_codebase(args.query, args.path)
            output_json(results)
        else:
            raise ValueError("Invalid action. Use 'index' or 'query'.")
    except Exception as e:
        output_json({"status": "error", "message": str(e)})
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
