import re
from typing import List, Dict


def chunk_parsed_code(
    codebase_dict: Dict[str, str],
    max_chunk_size: int = 4000,
    whole_file_threshold: int = 4000,
) -> List[Dict]:
    """
    Chunk the parsed code into smaller pieces for efficient processing and indexing.

    Args:
        codebase_dict (Dict[str, str]): Dictionary with file paths as keys and file contents as values.
        max_chunk_size (int): Maximum size of each chunk in characters. Defaults to 4000.
        whole_file_threshold (int): Threshold below which a file is treated as a single chunk. Defaults to 4000.

    Returns:
        List[Dict]: List of chunks, where each chunk is a dictionary containing content and metadata.
    """
    chunks = []

    def clean_text(text: str) -> str:
        """
        Clean the input text by removing non-printable characters and normalizing whitespace.

        Args:
            text (str): Input text to clean.

        Returns:
            str: Cleaned text.
        """
        # Remove non-printable characters and normalize whitespace
        text = re.sub(r"[\x00-\x1F\x7F-\x9F]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def create_chunk(
        file_path: str,
        start_line: int,
        end_line: int,
        content: List[str],
        chunk_type: str,
        name: str,
    ):
        """
        Create a chunk from the given content and add it to the chunks list.

        Args:
            file_path (str): Path of the file.
            start_line (int): Starting line number of the chunk.
            end_line (int): Ending line number of the chunk.
            content (List[str]): List of lines in the chunk.
            chunk_type (str): Type of the chunk ('whole_file' or 'partial').
            name (str): Name of the chunk.
        """
        cleaned_content = [
            (i, clean_text(line))
            for i, line in enumerate(content, start=start_line)
            if clean_text(line)
        ]
        if cleaned_content:
            chunks.append(
                {
                    "content": cleaned_content,
                    "metadata": {
                        "file": file_path,
                        "start_line": start_line,
                        "end_line": end_line,
                        "type": chunk_type,
                        "name": name,
                    },
                }
            )

    def process_item(content: str, file_path: str):
        """
        Process a single file, splitting it into chunks if necessary.

        Args:
            content (str): Content of the file.
            file_path (str): Path of the file.
        """
        lines = content.split("\n")
        total_chars = sum(len(line) for line in lines)

        if total_chars <= whole_file_threshold:
            # Use whole file as a chunk if it's below the threshold
            create_chunk(
                file_path, 1, len(lines), lines, "whole_file", file_path.split("/")[-1]
            )
        else:
            # Use chunking for larger files
            current_chunk = []
            current_size = 0
            start_line = 1
            for i, line in enumerate(lines, start=1):
                if current_size + len(line) > max_chunk_size and current_chunk:
                    # Create a chunk when it reaches the maximum size
                    create_chunk(
                        file_path,
                        start_line,
                        i - 1,
                        current_chunk,
                        "partial",
                        f"{file_path.split('/')[-1]}_{start_line}",
                    )
                    current_chunk = []
                    current_size = 0
                    start_line = i
                current_chunk.append(line)
                current_size += len(line)

            # Create the last chunk if there's remaining content
            if current_chunk:
                create_chunk(
                    file_path,
                    start_line,
                    len(lines),
                    current_chunk,
                    "partial",
                    f"{file_path.split('/')[-1]}_{start_line}",
                )

    # Process each file in the codebase dictionary
    for file_path, content in codebase_dict.items():
        process_item(content, file_path)

    return chunks
