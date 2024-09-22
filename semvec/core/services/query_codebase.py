import sys
import logging
import os
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


def query_codebase(query: str, repo_path: str) -> List[Dict]:
    logging.info("Querying codebase...")
    try:
        repo_name = os.path.basename(repo_path)
        retrieval_system = FAISSRetrievalSystem()
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
