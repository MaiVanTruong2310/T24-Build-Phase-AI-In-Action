"""Script to index JSONL medical records into local ChromaDB vector store."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.medical_assistant.rag.vector_index import build_vector_store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index medical records into ChromaDB vector store")
    parser.add_argument("--rebuild", action="store_true", help="Clear and rebuild index from scratch")
    parser.add_argument("--batch-size", type=int, default=30, help="Batch size for embeddings")
    args = parser.parse_args()

    build_vector_store(rebuild=args.rebuild, batch_size=args.batch_size)
