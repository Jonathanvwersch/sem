import re
from typing import List, Dict


def chunk_parsed_code(
    codebase_dict: Dict[str, str],
    max_chunk_size: int = 4000,
    whole_file_threshold: int = 4000,
) -> List[Dict]:
    chunks = []

    def clean_text(text: str) -> str:
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
        lines = content.split("\n")
        total_chars = sum(len(line) for line in lines)

        if total_chars <= whole_file_threshold:
            # Use whole file as a chunk
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
            if current_chunk:
                create_chunk(
                    file_path,
                    start_line,
                    len(lines),
                    current_chunk,
                    "partial",
                    f"{file_path.split('/')[-1]}_{start_line}",
                )

    for file_path, content in codebase_dict.items():
        process_item(content, file_path)

    return chunks
