"""Initialize or refresh the CraveCorner SQLite schema and menu seed."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import load_config
from database import initialize_database


if __name__ == "__main__":
    config = load_config()
    initialize_database(config["DATABASE"])
    print(f"Database initialized at {config['DATABASE']}")
