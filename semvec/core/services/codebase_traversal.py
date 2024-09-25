import logging
import os
import gitmatch
import aiofiles
import asyncio
from typing import Dict, List

from constants.file_patterns import DEFAULT_IGNORE_PATTERNS


def normalize_path(path: str) -> str:
    """
    Normalize a file path for consistent processing.

    Args:
        path (str): The path to normalize.

    Returns:
        str: The normalized path.
    """
    path = path.replace(os.sep, "/")
    if path.startswith("./"):
        path = path[2:]
    if path != "/" and path.endswith("/"):
        path = path[:-1]
    return path


def parse_gitignore(repo_path: str, base_path: str = "") -> List[str]:
    """
    Parse the .gitignore file in the given repository path.

    Args:
        repo_path (str): The path to the repository.
        base_path (str): The base path to prepend to the patterns.

    Returns:
        List[str]: A list of normalized ignore patterns.
    """
    gitignore_path = os.path.join(repo_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        return []
    with open(gitignore_path, "r") as f:
        patterns = [
            line.strip() for line in f if line.strip() and not line.startswith("#")
        ]
        return [
            normalize_path(os.path.join(base_path, pattern)) for pattern in patterns
        ]


def should_ignore(path: str, ignore_patterns: List[str], repo_path: str) -> bool:
    """
    Determine if a given path should be ignored based on the ignore patterns.

    Args:
        path (str): The path to check.
        ignore_patterns (List[str]): List of ignore patterns.
        repo_path (str): The base path of the repository.

    Returns:
        bool: True if the path should be ignored, False otherwise.
    """
    if os.path.isabs(path):
        path = os.path.relpath(path, repo_path)
    path = normalize_path(path)
    matcher = gitmatch.compile(ignore_patterns)
    return bool(matcher.match(path))


async def traverse_codebase_from_path(repo_path: str) -> Dict[str, str]:
    """
    Asynchronously traverse a codebase and read the contents of all files.

    Args:
        repo_path (str): The path to the repository to traverse.

    Returns:
        Dict[str, str]: A dictionary where keys are relative file paths and values are file contents.
    """
    codebase_dict = {}
    ignore_patterns = [normalize_path(p) for p in DEFAULT_IGNORE_PATTERNS]
    ignore_patterns.extend(parse_gitignore(repo_path))

    async def process_file(file_path: str, relative_path: str):
        """
        Process a single file: read its contents if it's not ignored.

        Args:
            file_path (str): The absolute path to the file.
            relative_path (str): The path of the file relative to the repo root.
        """
        if should_ignore(relative_path, ignore_patterns, repo_path):
            return
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                codebase_dict[relative_path] = content
        except UnicodeDecodeError:
            logging.info(f"Skipping binary file: {file_path}")
        except Exception as e:
            logging.error(f"Error reading file {file_path}: {str(e)}")

    tasks = []
    for root, dirs, files in os.walk(repo_path):
        relative_root = os.path.relpath(root, repo_path)
        # Filter out ignored directories
        dirs[:] = [
            d
            for d in dirs
            if not should_ignore(
                normalize_path(os.path.join(relative_root, d)),
                ignore_patterns,
                repo_path,
            )
        ]
        # Check for nested .gitignore files
        if ".gitignore" in files:
            new_patterns = parse_gitignore(root, relative_root)
            ignore_patterns.extend(new_patterns)
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_path)
            tasks.append(process_file(file_path, relative_path))

    await asyncio.gather(*tasks)
    return codebase_dict
