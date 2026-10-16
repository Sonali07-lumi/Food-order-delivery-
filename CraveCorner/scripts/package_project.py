"""Create and verify a clean Windows-friendly CraveCorner source archive."""

from __future__ import annotations

import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT_FILES = (
    "app.py",
    "config.py",
    "database.py",
    "models.py",
    "queue_manager.py",
    "requirements.txt",
    ".env.example",
    ".gitignore",
    "README.md",
    "PROJECT_SUMMARY.md",
    "test_report.md",
)
DIRECTORIES = ("scripts", "tests", "templates", "static", "database", "instance")
REQUIRED_FILES = (
    "app.py",
    "config.py",
    "database.py",
    "models.py",
    "queue_manager.py",
    "requirements.txt",
    ".env.example",
    "README.md",
    "PROJECT_SUMMARY.md",
    "test_report.md",
    "scripts/init_db.py",
    "scripts/create_admin.py",
    "tests/test_queue.py",
    "tests/test_orders.py",
    "tests/test_admin.py",
    "templates/base.html",
    "templates/index.html",
    "templates/menu.html",
    "templates/cart.html",
    "templates/checkout.html",
    "templates/confirmation.html",
    "templates/tracking.html",
    "templates/about.html",
    "templates/admin_login.html",
    "templates/admin.html",
    "static/css/site.css",
    "static/js/shared.js",
    "static/js/customer.js",
    "static/js/admin.js",
    "static/images/favicon.svg",
)


def source_files() -> list[Path]:
    selected: set[Path] = set()
    for relative in ROOT_FILES:
        path = PROJECT_ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(f"Required source file is missing: {relative}")
        selected.add(path)
    for directory in DIRECTORIES:
        base = PROJECT_ROOT / directory
        if not base.is_dir():
            raise FileNotFoundError(f"Required source directory is missing: {directory}")
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(PROJECT_ROOT)
            if any(part in {"__pycache__", ".pytest_cache", "node_modules", ".venv"} for part in relative.parts):
                continue
            if path.suffix in {".pyc", ".pyo"} or path.name == ".env":
                continue
            if relative.parts[0] in {"instance", "database"} and path.name != ".gitkeep":
                continue
            selected.add(path)
    return sorted(selected)


def create_archive(output: Path) -> list[str]:
    files = source_files()
    output.parent.mkdir(parents=True, exist_ok=True)
    output = output.resolve()
    with ZipFile(output, "w", ZIP_DEFLATED) as archive:
        for path in files:
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            archive.write(path, f"CraveCorner/{relative}")
    with ZipFile(output, "r") as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP integrity test failed.")
        names = set(archive.namelist())
        missing = [
            relative
            for relative in REQUIRED_FILES
            if f"CraveCorner/{relative}" not in names
        ]
        if missing:
            raise RuntimeError(f"ZIP is missing required files: {', '.join(missing)}")
        if any(name.startswith(("CraveCorner/.venv/", "CraveCorner/node_modules/")) for name in names):
            raise RuntimeError("The archive unexpectedly contains a runtime environment.")
        if any(name.endswith((".pyc", ".sqlite3")) or "/__pycache__/" in name for name in names):
            raise RuntimeError("The archive unexpectedly contains generated or local data.")
        if any(name.startswith("CraveCorner/.env/") or name == "CraveCorner/.env" for name in names):
            raise RuntimeError("The archive unexpectedly contains a local .env file.")
    return [f"CraveCorner/{path.relative_to(PROJECT_ROOT).as_posix()}" for path in files]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path.cwd() / "CraveCorner.zip",
        help="ZIP output path (defaults to ./CraveCorner.zip)",
    )
    args = parser.parse_args()
    paths = create_archive(args.output)
    print(f"Created and verified {args.output.resolve()}")
    print(f"Included {len(paths)} source and asset files under one CraveCorner/ folder.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
