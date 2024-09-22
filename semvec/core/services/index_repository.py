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
    format="%(levelname)s - %(message)s",
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
