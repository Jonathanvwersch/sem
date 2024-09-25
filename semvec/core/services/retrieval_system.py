import os
import numpy as np
import faiss
import json
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import logging

DEFAULT_INDEX_PATH = os.path.expanduser("~/.sem/index")


class FAISSRetrievalSystem:
    def __init__(self):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.tokenizer = self.model.tokenizer
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index_dir = DEFAULT_INDEX_PATH
        self.index = None
        self.metadata = None

    def create_index(self, chunks: List[dict], identifier: str):
        texts = [
            f"File: {chunk['metadata']['file']}\n\n{' '.join(str(line) for line in chunk['content'])}"
            for chunk in chunks
        ]
        embeddings = self._encode_texts(texts)
        self.index = self._build_faiss_index(embeddings)

        # Extract only necessary metadata
        metadata = [
            {
                "file": chunk["metadata"]["file"],
                "start_line": chunk["metadata"]["start_line"],
                "end_line": chunk["metadata"]["end_line"],
            }
            for chunk in chunks
        ]

        self._save_index(identifier, metadata)
        logging.info(f"Index created and saved for identifier: {identifier}")

    def query_index(
        self,
        identifier: str,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.1,
    ) -> List[Dict]:
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

    def check_index_exists(self, identifier: str) -> bool:
        index_filename = os.path.join(self.index_dir, f"{identifier}.index")
        metadata_filename = os.path.join(self.index_dir, f"{identifier}_metadata.json")
        return os.path.exists(index_filename) and os.path.exists(metadata_filename)

    def _save_index(self, identifier: str, metadata: List[Dict]):
        os.makedirs(self.index_dir, exist_ok=True)
        index_filename = os.path.join(self.index_dir, f"{identifier}.index")
        metadata_filename = os.path.join(self.index_dir, f"{identifier}_metadata.json")

        faiss.write_index(self.index, index_filename)
        with open(metadata_filename, "w") as f:
            json.dump(metadata, f)

    def _load_index(self, identifier: str):
        index_filename = os.path.join(self.index_dir, f"{identifier}.index")
        metadata_filename = os.path.join(self.index_dir, f"{identifier}_metadata.json")

        if not os.path.exists(index_filename) or not os.path.exists(metadata_filename):
            raise FileNotFoundError(
                f"Index files for {identifier} not found in {self.index_dir}"
            )

        self.index = faiss.read_index(index_filename)
        with open(metadata_filename, "r") as f:
            self.metadata = json.load(f)

    def _process_search_results(
        self,
        distances: np.ndarray,
        indices: np.ndarray,
        top_k: int,
        similarity_threshold: float,
    ) -> List[Dict]:
        results = []
        seen_files = {}

        for distance, idx in zip(distances, indices):
            similarity = 1 / (1 + distance)
            if similarity < similarity_threshold:
                continue

            metadata = self.metadata[idx]
            file_path = metadata["file"]
            start_line = metadata["start_line"]
            end_line = metadata["end_line"]

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
