"""OCA crawl, manifest parse, ChromaDB upsert pipeline for the search index.

Crawls OCA GitHub repositories via PyGithub, parses __manifest__.py files
using ast.literal_eval (never eval), and stores module metadata in a local
ChromaDB vector database for semantic search.
"""

from __future__ import annotations

import ast
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable

try:
    import chromadb
except ImportError:  # pragma: no cover
    chromadb = None  # type: ignore[assignment]

try:
    from github import Github, GithubException
except ImportError:  # pragma: no cover
    Github = None  # type: ignore[assignment,misc]
    GithubException = Exception  # type: ignore[assignment,misc]

if TYPE_CHECKING:
    from odoo_gen_utils.search.types import IndexStatus

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "odoo-gen" / "chromadb"


def get_github_token() -> str | None:
    """Retrieve a GitHub token from environment or gh CLI.

    Checks GITHUB_TOKEN env var first, then tries ``gh auth token`` via
    subprocess. Returns None if both fail.
    """
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return None


def _parse_manifest_safe(content: str) -> dict | None:
    """Parse an Odoo ``__manifest__.py`` file content safely.

    Uses ``ast.literal_eval`` to evaluate the manifest dictionary.
    NEVER uses ``eval()``. Returns None for invalid or non-dict content.

    Args:
        content: Raw string content of a __manifest__.py file.

    Returns:
        Parsed manifest dict, or None if parsing fails or result is not a dict.
    """
    try:
        result = ast.literal_eval(content)
    except (ValueError, SyntaxError, RecursionError):
        return None

    if not isinstance(result, dict):
        return None

    return result


def _build_document_text(manifest: dict, module_name: str) -> str:
    """Build the document text for ChromaDB embedding.

    Concatenates display_name, summary, description (first 500 chars),
    category, and depends list, joined with `` | ``.

    Args:
        manifest: Parsed manifest dictionary.
        module_name: Technical module name.

    Returns:
        Concatenated text string for embedding.
    """
    display_name = manifest.get("name", module_name)
    summary = manifest.get("summary", "")
    description = manifest.get("description", "")[:500]
    category = manifest.get("category", "")
    depends = manifest.get("depends", [])
    depends_str = ", ".join(depends) if isinstance(depends, list) else str(depends)

    parts = [display_name, summary, description, category, depends_str]
    return " | ".join(part for part in parts if part)


def build_oca_index(
    token: str,
    db_path: str,
    incremental: bool = False,
    progress_callback: Callable[[int, int], None] | None = None,
) -> int:
    """Crawl OCA GitHub repos and upsert module metadata into ChromaDB.

    Creates a ChromaDB persistent collection, iterates over all OCA
    organization repos, checks for a 17.0 branch, parses module manifests,
    and stores entries with metadata.

    Args:
        token: GitHub personal access token. Empty string raises SystemExit.
        db_path: Path to ChromaDB storage directory.
        incremental: If True, skip repos where pushed_at <= stored last_pushed.
        progress_callback: Optional callback(repos_done, total_repos).

    Returns:
        Count of modules indexed.

    Raises:
        SystemExit: If token is empty or falsy.
    """
    if not token:
        raise SystemExit("GitHub token required. Run: gh auth login")

    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(
        name="odoo_modules",
        metadata={"hnsw:space": "cosine"},
    )

    gh = Github(token)
    org = gh.get_organization("OCA")
    repos = list(org.get_repos())
    total_repos = len(repos)

    module_count = 0

    for idx, repo in enumerate(repos):
        # Try to get 17.0 branch; skip repo if not found
        try:
            repo.get_branch("17.0")
        except (GithubException, Exception):
            if progress_callback:
                progress_callback(idx + 1, total_repos)
            continue

        # Incremental: skip repos not pushed since last build
        if incremental:
            existing_meta = collection.metadata or {}
            last_pushed_stored = existing_meta.get(f"repo_pushed_{repo.name}", "")
            repo_pushed = str(repo.pushed_at) if repo.pushed_at else ""
            if repo_pushed and last_pushed_stored and repo_pushed <= last_pushed_stored:
                if progress_callback:
                    progress_callback(idx + 1, total_repos)
                continue

        # Get root contents of 17.0 branch
        try:
            contents = repo.get_contents("", ref="17.0")
        except Exception:
            if progress_callback:
                progress_callback(idx + 1, total_repos)
            continue

        if not isinstance(contents, list):
            contents = [contents]

        for item in contents:
            if item.type != "dir":
                continue

            module_name = item.name

            # Check for __manifest__.py in the module directory
            try:
                manifest_file = repo.get_contents(f"{module_name}/__manifest__.py", ref="17.0")
            except Exception:
                continue

            # Parse manifest
            manifest_content = manifest_file.decoded_content.decode("utf-8", errors="replace")
            manifest = _parse_manifest_safe(manifest_content)
            if manifest is None:
                continue

            # Skip non-installable modules
            if not manifest.get("installable", True):
                continue

            # Build document text and metadata
            document = _build_document_text(manifest, module_name)
            depends_list = manifest.get("depends", [])
            depends_str = ", ".join(depends_list) if isinstance(depends_list, list) else str(depends_list)

            entry_id = f"oca/{repo.name}/{module_name}"
            metadata = {
                "module_name": module_name,
                "oca_repo": repo.name,
                "org": "OCA",
                "category": manifest.get("category", ""),
                "depends": depends_str,
                "version": manifest.get("version", ""),
                "license": manifest.get("license", ""),
                "summary": manifest.get("summary", ""),
                "url": repo.html_url,
                "stars": repo.stargazers_count,
                "last_pushed": str(repo.pushed_at) if repo.pushed_at else "",
            }

            collection.upsert(
                ids=[entry_id],
                documents=[document],
                metadatas=[metadata],
            )
            module_count += 1

        if progress_callback:
            progress_callback(idx + 1, total_repos)

    # Store build timestamp in collection metadata
    build_time = datetime.now(timezone.utc).isoformat()
    collection.modify(metadata={
        **collection.metadata,
        "hnsw:space": "cosine",
        "last_built": build_time,
    })

    return module_count


def get_index_status(db_path: str | None = None) -> IndexStatus:
    """Check the status of the local ChromaDB search index.

    Args:
        db_path: Path to ChromaDB storage directory. Defaults to DEFAULT_DB_PATH.

    Returns:
        IndexStatus with index existence, module count, build timestamp, and size.
    """
    from odoo_gen_utils.search.types import IndexStatus

    resolved_path = db_path or str(DEFAULT_DB_PATH)
    path_obj = Path(resolved_path)

    if not path_obj.exists():
        return IndexStatus(
            exists=False,
            module_count=0,
            last_built=None,
            db_path=resolved_path,
            size_bytes=0,
        )

    try:
        client = chromadb.PersistentClient(path=resolved_path)
        collection = client.get_or_create_collection(
            name="odoo_modules",
            metadata={"hnsw:space": "cosine"},
        )
        count = collection.count()
        meta = collection.metadata or {}
        last_built = meta.get("last_built")

        # Calculate directory size
        size_bytes = sum(f.stat().st_size for f in path_obj.rglob("*") if f.is_file())

        return IndexStatus(
            exists=True,
            module_count=count,
            last_built=last_built,
            db_path=resolved_path,
            size_bytes=size_bytes,
        )
    except Exception:
        return IndexStatus(
            exists=False,
            module_count=0,
            last_built=None,
            db_path=resolved_path,
            size_bytes=0,
        )
