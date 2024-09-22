import sys
import json
import logging
import argparse
import os
import asyncio
from typing import List, Dict
from services import (
    chunk_parsed_code,
    traverse_codebase_from_path,
    FAISSRetrievalSystem,
)

# Configure logging to use stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


async def index_repository(repo_path: str):
    try:
        logging.info(f"Processing repository: {repo_path}")
        codebase_dict = await traverse_codebase_from_path(repo_path)
        logging.info(f"Codebase traversal complete. Files found: {len(codebase_dict)}")
        logging.info("Chunking code...")
        chunks = chunk_parsed_code(codebase_dict)
        logging.info(f"Number of chunks: {len(chunks)}")
        if not chunks:
            logging.warning("No chunks were created. Check the chunking process.")
            return
        logging.info("Initializing FAISS retrieval system...")
        retrieval_system = FAISSRetrievalSystem(chunks)
        logging.info("Retrieval system initialized")
        repo_name = os.path.basename(repo_path)
        retrieval_system.save_index(repo_name)
        logging.info(f"Repository {repo_name} indexed successfully")
    except Exception as e:
        logging.exception(f"Unexpected error in index_repository: {str(e)}")
        sys.exit(1)


def query_codebase(query: str, repo_path: str) -> List[Dict]:
    logging.info("Querying codebase...")
    try:
        repo_name = os.path.basename(repo_path)
        retrieval_system = FAISSRetrievalSystem()
        retrieval_system.ensure_index_loaded(repo_name)
        results = retrieval_system.semantic_search(query, k=5, similarity_threshold=0.1)
        if results:
            formatted_results = []
            for result in results:
                formatted_result = {
                    "file_path": result.file_path,
                    "start_line": result.start_line,
                    "end_line": result.end_line,
                    "score": result.score,
                }
                formatted_results.append(formatted_result)
                logging.info(f"File: {result.file_path}")
                logging.info(f"Lines: {result.start_line} - {result.end_line}")
                logging.info(f"Score: {result.score}")
                logging.info("---")
            return formatted_results
        else:
            logging.info("No results found.")
            return []
    except FileNotFoundError:
        logging.error(f"No index found for repository: {repo_path}")
        return []
    except Exception as e:
        logging.exception(f"An error occurred during querying: {e}")
        return []


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
        print("START_JSON")
        json.dump(results, sys.stdout)
        print("\nEND_JSON")
        sys.stdout.flush()
    else:
        logging.error("Invalid action. Use 'index' or 'query'.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
