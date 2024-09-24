import sys
import logging
import os
from typing import List, Dict
from services import FAISSRetrievalSystem
from models import CodeLocation

# Configure logging to use stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def query_codebase(
    query: str, repo_path: str, top_k: int = 5, similarity_threshold: float = 0.1
) -> List[Dict]:
    """
    Perform a semantic search on the codebase using the given query.

    Args:
        query (str): The search query.
        repo_path (str): The path to the repository to search.
        top_k (int): Number of top results to return. Defaults to 5.
        similarity_threshold (float): Minimum similarity score for results. Defaults to 0.1.

    Returns:
        List[Dict]: A list of dictionaries containing search results.
        Each dictionary includes file path, start line, end line, and score.

    Raises:
        FileNotFoundError: If no index is found for the repository.
        Exception: For any other errors that occur during the search process.
    """

    try:
        repo_identifier = os.path.basename(repo_path)
        logging.info(f"Querying codebase: {repo_identifier}")
        retrieval_system = FAISSRetrievalSystem()
        results = retrieval_system.query_index(
            repo_identifier, query, top_k, similarity_threshold
        )
        logging.info(f"Query results: {results}")

        if results:
            formatted_results = []
            for result in results:
                formatted_result = {
                    "file_path": result["file_path"],
                    "start_line": result["start_line"],
                    "end_line": result["end_line"],
                    "score": result["score"],
                }
                formatted_results.append(formatted_result)

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
