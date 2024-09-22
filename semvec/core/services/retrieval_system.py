import logging
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List
import traceback
from models import CodeLocation


DEFAULT_INDEX_PATH = os.path.expanduser("~/.sem/index")


class FAISSRetrievalSystem:
    def __init__(self, chunks=None):
        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.tokenizer = self.model.tokenizer
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index_dir = DEFAULT_INDEX_PATH
        self.current_identifier = None

        if chunks:
            self.chunks = chunks
            self._build_index()

    def _build_index(self):
        texts = [
            f"File: {chunk['metadata']['file']}\n\n{' '.join(str(line) for line in chunk['content'])}"
            for chunk in self.chunks
        ]
        batch_size = 32
        embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                tokenized_batch = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt",
                )

                for j, sentence in enumerate(batch):
                    try:
                        sentence_embedding = self.model.encode(
                            sentence, show_progress_bar=False
                        )
                        if sentence_embedding.ndim == 1:
                            sentence_embedding = sentence_embedding.reshape(1, -1)
                        embeddings.append(sentence_embedding)
                    except Exception as e:
                        logging.error(f"  Error encoding item {i+j}: {str(e)}")

            except Exception as e:
                logging.error(f"Error processing batch {i}: {str(e)}")
                continue

        if not embeddings:
            raise ValueError(
                "No valid embeddings were generated. Check your input data."
            )

        embeddings = np.vstack(embeddings).astype(np.float32)

        dimension = embeddings.shape[1]
        n_clusters = min(100, len(embeddings) // 2)
        quantizer = faiss.IndexFlatL2(dimension)
        self.index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters)

        if len(embeddings) < n_clusters:
            logging.warning(
                f"Not enough data points ({len(embeddings)}) for IVF index. Using IndexFlatL2 instead."
            )
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(embeddings)
        else:
            self.index.train(embeddings)
            self.index.add(embeddings)

        logging.info("Index built successfully")

    def save_index(self, identifier: str):
        try:
            os.makedirs(self.index_dir, exist_ok=True)
            index_filename = os.path.join(self.index_dir, f"{identifier}.index")

            faiss.write_index(self.index, index_filename)
            logging.info(f"Index and chunks saved successfully to {self.index_dir}")
            self.current_identifier = identifier
        except Exception as e:
            logging.error(f"Error saving index: {e}")
            raise

    def load_index(self, identifier: str):
        os.makedirs(self.index_dir, exist_ok=True)
        index_filename = os.path.join(self.index_dir, f"{identifier}.index")
        chunks_filename = os.path.join(self.index_dir, f"{identifier}.npy")

        logging.info(f"Loading index from {index_filename}")

        if not os.path.exists(index_filename) or not os.path.exists(chunks_filename):
            raise FileNotFoundError(
                f"Index files for {identifier} not found in {self.index_dir}"
            )

        self.index = faiss.read_index(index_filename)
        self.chunks = np.load(chunks_filename, allow_pickle=True)
        self.current_identifier = identifier
        logging.info(f"Index and chunks loaded successfully from {self.index_dir}")

    def retrieve(self, query, top_k=5, similarity_threshold=0.1):
        if self.current_identifier is None:
            raise ValueError(
                "No index is currently loaded. Please load an index first."
            )

        try:
            self.ensure_index_loaded(self.current_identifier)
        except FileNotFoundError:
            raise ValueError(
                f"No index found for the current identifier: {self.current_identifier}"
            )

        try:
            logging.info(f"Encoding query: {query}")
            tokenized_query = self.tokenizer(query, return_tensors="pt")

            query_embedding = self.model.encode(query, convert_to_tensor=True)

            if query_embedding.dim() == 1:
                query_embedding = query_embedding.unsqueeze(0)

            query_embedding_np = query_embedding.cpu().numpy().astype(np.float32)
            distances, indices = self.index.search(query_embedding_np, top_k * 2)

            results = []
            seen_files = {}
            for i, idx in enumerate(indices[0]):
                distance = distances[0][i]
                similarity = 1 / (1 + distance)

                if similarity < similarity_threshold:
                    continue

                chunk = self.chunks[idx]
                file_path = chunk["metadata"]["file"]
                start_line = chunk["metadata"]["start_line"]
                end_line = chunk["metadata"]["end_line"]

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
                result = CodeLocation(
                    file_path=file_path,
                    start_line=details["start_line"],
                    end_line=details["end_line"],
                    score=details["score"],
                )
                results.append(result)

            logging.info(f"Found the following semantic matches: {results}")

            return results

        except Exception as e:
            logging.error(f"An error occurred during retrieval: {str(e)}")
            traceback.print_exc()
            return []

    def semantic_search(
        self, query: str, k: int = 5, similarity_threshold: float = 0.1
    ) -> List[CodeLocation]:
        return self.retrieve(query, k, similarity_threshold)
