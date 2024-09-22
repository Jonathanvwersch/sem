import sys
import json
import logging
import argparse
import asyncio
from typing import List, Dict
from semvec.core.services import index_repository, query_codebase
from services.chunk_codebase import chunk_parsed_code
from services.codebase_traversal import traverse_codebase_from_path

# Configure logging to use stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def main():
    parser = argparse.ArgumentParser(description="Local Code Search Tool")
    parser.add_argument("action", choices=["index", "query"], help="Action to perform")
    parser.add_argument(
        "--path", required=True, help="Path to the repository for indexing or querying"
    )
    parser.add_argument("--query", help="Query to search in the codebase")
    args = parser.parse_args()

    if args.action == "index":
        await index_repository(args.path)
    elif args.action == "query":
        if not args.query:
            logging.error("Please provide a query using the --query argument")
            sys.exit(1)
        results = query_codebase(args.query, args.path)
        json.dump(results, sys.stdout)
        sys.stdout.flush()
    else:
        logging.error("Invalid action. Use 'index' or 'query'.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
