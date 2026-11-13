#!/usr/bin/env python3
"""Resolve a user catalog once, then check its approved path/hash before execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path


class CatalogError(Exception):
    pass


def implementation_root(workdir: Path) -> Path:
    workdir = workdir.expanduser().resolve()
    if not workdir.is_dir():
        raise CatalogError(f"implementation directory not found: {workdir}")
    try:
        proc = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=workdir,
                              capture_output=True, text=True, check=False,
                              env={**os.environ, "LC_ALL": "C", "LANGUAGE": "C"})
    except FileNotFoundError:
        return workdir
    except OSError as exc:
        raise CatalogError(f"cannot inspect implementation repository: {exc}") from exc
    if proc.returncode == 0:
        return Path(proc.stdout.strip()).resolve()
    if "not a git repository" not in proc.stderr:
        raise CatalogError(f"cannot determine implementation root: {proc.stderr.strip()}")
    for parent in (workdir, *workdir.parents):
        try:
            (parent / ".git").lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise CatalogError(f"cannot inspect repository metadata: {exc}") from exc
        raise CatalogError(f"cannot read implementation repository metadata: {parent / '.git'}")
    return workdir


def catalog_identity(path: Path, source: str) -> dict:
    try:
        path = path.resolve(strict=True)
        if not path.is_file():
            raise CatalogError(f"{source} catalog must be a regular file: {path}")
        content = path.read_bytes()
    except OSError as exc:
        raise CatalogError(f"{source} catalog is unavailable: {path} ({exc})") from exc
    return {"path": str(path), "sha256": hashlib.sha256(content).hexdigest(), "source": source}


def resolve_catalog(workdir: Path, catalog: str | None = None, *, home: Path | None = None) -> dict:
    root = implementation_root(workdir)
    if catalog is not None:
        path = Path(catalog).expanduser()
        return catalog_identity(path if path.is_absolute() else root / path, "explicit")
    for source, path in (("project", root / "artifex-tools.local.md"),
                         ("user", (home or Path.home()) / ".agents" / "artifex-tools.local.md")):
        # Only absence permits fallback; an unreadable or non-file selection is an error.
        try:
            path.lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise CatalogError(f"cannot inspect {source} catalog: {path} ({exc})") from exc
        return catalog_identity(path, source)
    return catalog_identity(Path(__file__).resolve().parents[1] / "references" / "tools-catalog.example.md",
                            "example")


def check_catalog(path: Path, expected_sha256: str) -> dict:
    path = path.expanduser()
    if not path.is_absolute():
        raise CatalogError("the pinned catalog path must be absolute")
    identity = catalog_identity(path, "pinned")
    if identity["sha256"] != expected_sha256.strip().lower():
        raise CatalogError(f"catalog changed since planning: {identity['path']}; reconcile the affected plan")
    return identity


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    resolve = commands.add_parser("resolve")
    resolve.add_argument("--workdir", type=Path, required=True)
    resolve.add_argument("--catalog", help="explicit file; relative paths use the implementation root")
    check = commands.add_parser("check")
    check.add_argument("--path", type=Path, required=True, help="approved absolute catalog path")
    check.add_argument("--sha256", required=True, help="approved SHA-256 of the catalog bytes")
    args = parser.parse_args(argv)
    try:
        result = (resolve_catalog(args.workdir, args.catalog) if args.command == "resolve"
                  else check_catalog(args.path, args.sha256))
    except CatalogError as exc:
        parser.exit(2, f"{exc}\n")
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
