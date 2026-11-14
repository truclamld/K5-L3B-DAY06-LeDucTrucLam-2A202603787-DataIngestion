"""OpenAI-compatible embeddings adapter using only the Python standard library."""
import json
import os
import urllib.error
import urllib.request
from typing import Protocol


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class MyEmbedder:
    """TODO: implement a provider adapter; do not silently fall back to mock vectors."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.dimensions = int(os.getenv("EMBEDDING_DIMENSIONS", "0"))
        if self.dimensions <= 0:
            raise ValueError("Set EMBEDDING_DIMENSIONS to the selected model's output size.")
        self.base_url = os.getenv("EMBEDDING_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        self.api_key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENROUTER_API_KEY") or "").strip()
        if not self.api_key:
            raise ValueError("Set OPENAI_API_KEY or OPENROUTER_API_KEY; no mock fallback is used.")

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = json.dumps({"model": self.model_name, "input": texts}).encode()
        request = urllib.request.Request(self.base_url + "/embeddings", data=payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=90) as response:
                data = json.loads(response.read())
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            raise RuntimeError(f"Embedding provider request failed: {exc}") from exc
        rows = sorted(data["data"], key=lambda row: row["index"])
        vectors = [[float(v) for v in row["embedding"]] for row in rows]
        if len(vectors) != len(texts) or any(len(v) != self.dimensions for v in vectors):
            raise ValueError("Embedding provider returned a count or dimension mismatch.")
        return vectors

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._embed(texts)

    def embed_query(self, question: str) -> list[float]:
        return self._embed([question])[0]
