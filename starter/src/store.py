"""PostgreSQL/pgvector store with strategy-scoped, idempotent ingestion."""
import math
from typing import Any
import psycopg
from psycopg.types.json import Jsonb
from .models import Chunk


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        """TODO: retain connection settings; validate model dimensions."""
        if not database_url:
            raise ValueError("database_url is required")
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.database_url = database_url
        self.dimensions = dimensions

    def create_schema(self) -> None:
        """TODO: create table with vector column and source/page/filter metadata."""
        with psycopg.connect(self.database_url) as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(f"""CREATE TABLE IF NOT EXISTS retrieval_chunks (
                strategy TEXT NOT NULL, chunk_id TEXT NOT NULL, document_id TEXT NOT NULL,
                source TEXT NOT NULL, page INTEGER NOT NULL, content TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb, embedding vector({self.dimensions}) NOT NULL,
                PRIMARY KEY (strategy, chunk_id))""")
            conn.execute("CREATE INDEX IF NOT EXISTS retrieval_chunks_metadata_idx ON retrieval_chunks USING GIN (metadata)")

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        """TODO: validate lengths/dimensions and write stable IDs without duplicates.

        When re-ingesting changed source documents, remove obsolete chunks too.
        """
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        if any(len(v) != self.dimensions or not all(math.isfinite(float(x)) for x in v) for v in vectors):
            raise ValueError(f"Every vector must contain {self.dimensions} finite values")
        if len({c.chunk_id for c in chunks}) != len(chunks):
            raise ValueError("chunk_id values must be unique within an upsert")
        documents = sorted({c.document_id for c in chunks})
        with psycopg.connect(self.database_url) as conn:
            # Replacing these documents also removes stale chunk IDs on changed re-ingestion.
            if documents:
                conn.execute("DELETE FROM retrieval_chunks WHERE strategy = %s AND document_id = ANY(%s)", (strategy, documents))
            rows = [(strategy, c.chunk_id, c.document_id, c.source, c.page, c.text,
                     Jsonb(c.metadata), "[" + ",".join(str(float(x)) for x in v) + "]")
                    for c, v in zip(chunks, vectors)]
            if rows:
                with conn.cursor() as cur:
                    cur.executemany("""INSERT INTO retrieval_chunks
                    (strategy, chunk_id, document_id, source, page, content, metadata, embedding)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::vector)""", rows)

    def search(self, strategy: str, query_vector: list[float], top_k: int = 3,
               filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """TODO: filter permitted metadata in SQL, rank by cosine distance, return top-k.

        Return chunk ID, text, score and metadata. Parameterize user-supplied values.
        """
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        if len(query_vector) != self.dimensions:
            raise ValueError(f"query vector must contain {self.dimensions} values")
        allowed = {"source", "page", "document_id", "section", "version", "language", "category"}
        filters = filters or {}
        unknown = set(filters) - allowed
        if unknown:
            raise ValueError(f"Unsupported metadata filter(s): {', '.join(sorted(unknown))}")
        clauses = ["strategy = %s"]
        params: list[Any] = [strategy]
        for key, value in filters.items():
            if key in {"source", "page", "document_id"}:
                clauses.append(f"{key} = %s")
            else:
                clauses.append("metadata ->> %s = %s")
                params.append(key)
            params.append(value)
        vector = "[" + ",".join(str(float(x)) for x in query_vector) + "]"
        params.extend([vector, top_k])
        sql = f"""SELECT chunk_id, document_id, source, page, content, metadata,
                    1 - (embedding <=> %s::vector) AS score
                 FROM retrieval_chunks WHERE {' AND '.join(clauses)}
                 ORDER BY embedding <=> %s::vector LIMIT %s"""
        # Distance vector appears first in SELECT, then the vector for ORDER BY.
        params = [vector, *params[:-2], vector, top_k]
        with psycopg.connect(self.database_url) as conn:
            rows = conn.execute(sql, params).fetchall()
        return [{"chunk_id": r[0], "document_id": r[1], "source": r[2], "page": r[3],
                 "text": r[4], "metadata": r[5], "score": float(r[6])} for r in rows]
