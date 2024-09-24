import logging
import os
import gitmatch
import aiofiles
import asyncio
from typing import Dict, List

DEFAULT_IGNORE_PATTERNS = [
    # Version control
    ".git",
    ".svn",
    ".hg",
    ".bzr",
    ".fossil",
    "_darcs",
    "CVS",
    # Python
    "__pycache__",
    "*.py[cod]",
    "*.so",
    ".venv",
    "venv",
    "env",
    ".Python",
    "pip-log.txt",
    "pip-delete-this-directory.txt",
    ".tox",
    ".coverage",
    ".coverage.*",
    ".cache",
    "nosetests.xml",
    "coverage.xml",
    "*.cover",
    ".hypothesis",
    ".pytest_cache",
    # JavaScript / Node.js
    "node_modules",
    "jspm_packages",
    "bower_components",
    ".npm",
    ".eslintcache",
    ".node_repl_history",
    "*.tsbuildinfo",
    ".next",
    ".nuxt",
    ".vuepress/dist",
    ".serverless",
    ".fusebox",
    ".dynamodb",
    # Ruby
    "*.gem",
    "*.rbc",
    "/.config",
    "/coverage",
    "/InstalledFiles",
    "/pkg",
    "/spec/reports",
    "/test/tmp",
    "/test/version_tmp",
    "/tmp",
    ".rakeTasks",
    ".rspec",
    ".rspec_status",
    # Java
    "*.class",
    "*.log",
    "*.ctxt",
    ".mtj.tmp",
    "*.jar",
    "*.war",
    "*.nar",
    "*.ear",
    "*.zip",
    "*.tar.gz",
    "*.rar",
    "hs_err_pid*",
    ".gradle",
    "build",
    "out",
    # C/C++
    "*.o",
    "*.ko",
    "*.obj",
    "*.elf",
    "*.ilk",
    "*.map",
    "*.exp",
    "*.gch",
    "*.pch",
    "*.lib",
    "*.a",
    "*.la",
    "*.lo",
    "*.dll",
    "*.so",
    "*.so.*",
    "*.dylib",
    # Rust
    "target",
    "**/*.rs.bk",
    "Cargo.lock",
    # Go
    "*.exe",
    "*.test",
    "*.prof",
    "*.out",
    # Swift / Objective-C
    ".build",
    "Packages",
    "xcuserdata",
    "*.xcscmblueprint",
    "*.xccheckout",
    "build",
    "DerivedData",
    "*.moved-aside",
    "*.pbxuser",
    "!default.pbxuser",
    "*.mode1v3",
    "!default.mode1v3",
    "*.mode2v3",
    "!default.mode2v3",
    "*.perspectivev3",
    "!default.perspectivev3",
    "*.hmap",
    "*.ipa",
    "*.dSYM.zip",
    "*.dSYM",
    # Android
    "*.apk",
    "*.ap_",
    "*.dex",
    "*.class",
    "bin",
    "gen",
    "proguard",
    # iOS
    "*.ipa",
    "*.xcarchive",
    "*.dSYM.zip",
    "*.dSYM",
    # IDEs and editors
    ".idea",
    ".vscode",
    "*.swp",
    "*.swo",
    "*~",
    ".vs",
    "*.sublime-workspace",
    ".atom",
    ".buildpath",
    ".project",
    ".settings",
    "*.launch",
    "*.tmproj",
    "*.esproj",
    "nbproject",
    "*.iml",
    "*.ipr",
    "*.iws",
    # OS generated
    ".DS_Store",
    ".DS_Store?",
    "._*",
    ".Spotlight-V100",
    ".Trashes",
    "ehthumbs.db",
    "Thumbs.db",
    "desktop.ini",
    # Build outputs
    "dist",
    "build",
    "out",
    "bin",
    "target",
    # Logs and databases
    "*.log",
    "*.sql",
    "*.sqlite",
    "*.db",
    # Package management
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "composer.lock",
    "Gemfile.lock",
    "Pipfile.lock",
    "poetry.lock",
    # Temporary files
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.swp",
    "*.swo",
    "*~",
    # Configuration
    ".env",
    ".env.*",
    "config.local.js",
    "config.local.php",
    # Documentation
    "site",
    # Misc
    ".sass-cache",
    ".grunt",
    ".webpack",
    "*.pid",
    "*.seed",
    "dump.rdb",
    ".eslintcache",
    ".stylelintcache",
    ".tsbuildinfo",
    ".turbo",
    # Large media files
    "*.mp4",
    "*.tiff",
    "*.avi",
    "*.flv",
    "*.mov",
    "*.wmv",
]


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
