"""Download the one embedding model for local, offline inference."""

from pathlib import Path

from sentence_transformers import SentenceTransformer

MODEL_DIR = Path(__file__).resolve().parents[1] / "models" / "all-MiniLM-L6-v2"


def main():
    MODEL_DIR.parent.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    model.save(str(MODEL_DIR))
    print(f"Model saved to {MODEL_DIR}")


if __name__ == "__main__":
    main()
