import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List
import logging
from models import CodeLocation

DEFAULT_INDEX_PATH = os.path.expanduser("~/.sem/index")


class FAISSRetrievalSystem:
    """
    A class for creating and querying FAISS indexes for semantic code search.
    This system uses sentence transformers for encoding and FAISS for efficient similarity search.
    """

    def __init__(self):
        """
        Initialize the FAISSRetrievalSystem with a pre-trained sentence transformer model.
        """
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.tokenizer = self.model.tokenizer
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index_dir = DEFAULT_INDEX_PATH
        self.index = None

    def create_index(self, chunks: List[dict], identifier: str):
        """
        Create a FAISS index from the given chunks and save it with the specified identifier.

        Args:
            chunks (List[dict]): List of code chunks with metadata.
            identifier (str): Unique identifier for the index.
        """
        texts = [
            f"File: {chunk['metadata']['file']}\n\n{' '.join(str(line) for line in chunk['content'])}"
            for chunk in chunks
        ]
        embeddings = self._encode_texts(texts)

        self.index = self._build_faiss_index(embeddings)
        self._save_index(identifier, embeddings, chunks)

        logging.info(f"Index created and saved for identifier: {identifier}")

    def query_index(
        self,
        identifier: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.1,
    ) -> List[CodeLocation]:
        """
        Query the index with the given identifier and return the top-k most similar results.

        Args:
            identifier (str): Unique identifier for the index to query.
            query (str): The search query.
            top_k (int): Number of top results to return.
            similarity_threshold (float): Minimum similarity score for results.

        Returns:
            List[CodeLocation]: List of CodeLocation objects representing the search results.
        """
        self._load_index(identifier)
        query_embedding = (
            self.model.encode(query, convert_to_tensor=True)
            .cpu()
            .numpy()
            .astype(np.float32)
        )

        distances, indices = self.index.search(
            query_embedding.reshape(1, -1), top_k * 2
        )

        results = self._process_search_results(
            distances[0], indices[0], top_k, similarity_threshold
        )

        logging.info(f"Query completed for identifier: {identifier}")
        return results

    def _encode_texts(self, texts: List[str]) -> np.ndarray:
        """
        Encode a list of texts into embeddings using the sentence transformer model.

        Args:
            texts (List[str]): List of texts to encode.

        Returns:
            np.ndarray: Array of embeddings.
        """
        batch_size = 32
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                batch_embeddings = self.model.encode(batch, show_progress_bar=False)
                embeddings.extend(batch_embeddings)
            except Exception as e:
                logging.error(f"Error encoding batch {i}: {str(e)}")

        return np.array(embeddings, dtype=np.float32)

    def _build_faiss_index(self, embeddings: np.ndarray) -> faiss.Index:
        """
        Build a FAISS index from the given embeddings.

        Args:
            embeddings (np.ndarray): Array of embeddings to index.

        Returns:
            faiss.Index: The constructed FAISS index.
        """
        dimension = embeddings.shape[1]
        n_clusters = min(100, len(embeddings) // 2)

        if len(embeddings) < n_clusters:
            index = faiss.IndexFlatL2(dimension)
        else:
            quantizer = faiss.IndexFlatL2(dimension)
            index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters)
            index.train(embeddings)

        index.add(embeddings)
        return index

    def _save_index(self, identifier: str, embeddings: np.ndarray, chunks: List[dict]):
        """
        Save the FAISS index and associated chunks to disk.

        Args:
            identifier (str): Unique identifier for the index.
            embeddings (np.ndarray): Array of embeddings.
            chunks (List[dict]): List of code chunks with metadata.
        """
        os.makedirs(self.index_dir, exist_ok=True)
        index_filename = os.path.join(self.index_dir, f"{identifier}.index")
        chunks_filename = os.path.join(self.index_dir, f"{identifier}.npy")

        faiss.write_index(self.index, index_filename)
        np.save(chunks_filename, chunks)

    def _load_index(self, identifier: str):
        """
        Load a FAISS index and associated chunks from disk.

        Args:
            identifier (str): Unique identifier for the index to load.

        Raises:
            FileNotFoundError: If the index files are not found.
        """
        index_filename = os.path.join(self.index_dir, f"{identifier}.index")
        chunks_filename = os.path.join(self.index_dir, f"{identifier}.npy")

        if not os.path.exists(index_filename) or not os.path.exists(chunks_filename):
            raise FileNotFoundError(
                f"Index files for {identifier} not found in {self.index_dir}"
            )

        self.index = faiss.read_index(index_filename)
        self.chunks = np.load(chunks_filename, allow_pickle=True)

    def _process_search_results(
        self,
        distances: np.ndarray,
        indices: np.ndarray,
        top_k: int,
        similarity_threshold: float,
    ) -> List[CodeLocation]:
        """
        Process the raw search results from FAISS and convert them to CodeLocation objects.

        Args:
            distances (np.ndarray): Array of distances from the query to each result.
            indices (np.ndarray): Array of indices of the nearest neighbors.
            top_k (int): Number of top results to return.
            similarity_threshold (float): Minimum similarity score for results.

        Returns:
            List[CodeLocation]: List of CodeLocation objects representing the search results.
        """
        results = []
        seen_files = {}

        for distance, idx in zip(distances, indices):
            similarity = 1 / (1 + distance)
            if similarity < similarity_threshold:
                continue

            chunk = self.chunks[idx]
            file_path = chunk["metadata"]["file"]
            start_line = chunk["metadata"]["start_line"]
            end_line = chunk["metadata"]["end_line"]

            # Group by file path to avoid duplicates
            if file_path in seen_files:
                seen_files[file_path]["start_line"] = min(
                    seen_files[file_path]["start_line"], start_line
                )
                seen_files[file_path]["end_line"] = max(
                    seen_files[file_path]["end_line"], end_line
                )
                seen_files[file_path]["score"] = max(
                    seen_files[file_path]["score"], similarity
                )
            else:
                seen_files[file_path] = {
                    "start_line": start_line,
                    "end_line": end_line,
                    "score": similarity,
                }

            if len(seen_files) == top_k:
                break

        for file_path, details in seen_files.items():
            results.append(
                {
                    "file_path": file_path,
                    "start_line": details["start_line"],
                    "end_line": details["end_line"],
                    "score": details["score"],
                }
            )

        return results
