"""Run the three-strategy retrieval benchmark from the starter directory."""
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_pdf
from .store import PgVectorStore


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """TODO:

    1. Load the corpus and benchmark; validate at least 30 content pages.
    2. Build strategies A (fixed), B (paragraph) and C (B + metadata filter).
    3. Embed with the same model and store vectors/metadata per strategy.
    4. Run the same dev/test questions and save full top-3 traces.
    5. Report retrieval metrics and prepare samples for manual assessment.

    Follow the five dimensions in ../../BENCHMARK.md.
    """
    starter = Path(__file__).resolve().parents[1]
    project = starter.parent
    load_dotenv(starter / ".env")
    manifest_path = Path(os.getenv("MANIFEST_PATH", project / "data/manifest.json"))
    pdf_path = Path(os.getenv("CORPUS_PDF", project / "data/Tutorial_EDIT.pdf"))
    questions_path = Path(os.getenv("BENCHMARK_PATH", project / "benchmark/questions.jsonl"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_id = manifest["source_id"]
    section_by_page = {int(page["physical_page"]): section["section_id"]
                       for section in manifest["included_pages"] for page in section["content_pages"]}
    pages = load_pdf(pdf_path, source_id, source_id)
    pages = [p for p in pages if p.page in section_by_page and p.text]
    if len(pages) < 30:
        raise ValueError(f"Manifest/PDF yielded only {len(pages)} non-empty content pages; expected at least 30.")
    for page in pages:
        page.metadata.update({"section": section_by_page[page.page], "version": manifest.get("version"),
                              "language": "en", "title": manifest.get("title")})
    questions = _read_jsonl(questions_path)
    if not questions:
        raise ValueError("Benchmark contains no questions")
    if not {q.get("split") for q in questions} >= {"dev", "test"}:
        raise ValueError("Benchmark must contain both dev and test questions")
    if any(q.get("gold_source_id") != source_id for q in questions):
        raise ValueError("Benchmark gold_source_id does not match the manifest source_id")
    model = os.getenv("EMBEDDING_MODEL", "").strip()
    if not model:
        raise ValueError("Set EMBEDDING_MODEL in starter/.env")
    embedder = MyEmbedder(model)
    database_url = os.getenv("DATABASE_URL", "").strip()
    store = PgVectorStore(database_url, embedder.dimensions)
    store.create_schema()

    strategy_chunks = {
        "A_fixed": [c for page in pages for c in fixed_size(page, 1000, 150)],
        "B_paragraph": [c for page in pages for c in by_paragraph(page, 1200)],
    }
    strategy_chunks["C_paragraph_filter"] = strategy_chunks["B_paragraph"]
    traces, resource = [], {}
    document_vector_cache: dict[tuple[str, str], list[float]] = {}
    query_vector_cache: dict[str, list[float]] = {}
    for strategy, chunks in strategy_chunks.items():
        started = time.perf_counter()
        vectors = []
        missing_chunks = []
        missing_keys = []
        for chunk in chunks:
            key = (chunk.chunk_id, chunk.text)
            cached = document_vector_cache.get(key)
            if cached is None:
                missing_chunks.append(chunk)
                missing_keys.append(key)
            else:
                vectors.append((key, cached))
        computed = []
        for start in range(0, len(missing_chunks), 64):
            batch = missing_chunks[start:start + 64]
            computed.extend(embedder.embed_documents([c.text for c in batch]))
        document_vector_cache.update(zip(missing_keys, computed))
        vector_by_key = dict(vectors)
        vector_by_key.update(zip(missing_keys, computed))
        vectors = [vector_by_key[(c.chunk_id, c.text)] for c in chunks]
        embed_seconds = time.perf_counter() - started
        store.upsert(strategy, chunks, vectors)
        resource[strategy] = {"chunk_count": len(chunks), "embedding_seconds": round(embed_seconds, 3),
                              "model": embedder.model_name, "dimensions": embedder.dimensions}
        for question in questions:
            query_vector = query_vector_cache.get(question["question"])
            if query_vector is None:
                query_vector = embedder.embed_query(question["question"])
                query_vector_cache[question["question"]] = query_vector
            filters = {}
            if strategy == "C_paragraph_filter" and question.get("filter"):
                requested = question["filter"]
                if requested.get("provided_by") != "ngữ cảnh truy vấn trước khi truy xuất":
                    raise ValueError(f"Question {question.get('id')} has a filter without a pre-retrieval source")
                filters[requested["field"]] = requested["value"]
            hits = store.search(strategy, query_vector, top_k=3, filters=filters)
            evaluated = evaluate_query(question, hits)
            evaluated["strategy"] = strategy
            evaluated["query_filter"] = filters
            traces.append(evaluated)
    results = starter / "results"
    _write_json(results / "traces.json", traces)
    _write_json(results / "summary.json", summarize(traces))
    _write_json(results / "resource_usage.json", resource)
    # Manual review is intentionally left for the student; provide consistent candidates.
    samples = [{"strategy": t["strategy"], "split": t["split"], "id": t["id"],
                "question": t["question"], "gold": t["gold"], "hits": t["hits"]}
               for t in traces if t["split"] == "test"]
    _write_json(results / "manual_assessment_samples.json", samples)
    print(f"Processed {len(pages)} content pages, {len(questions)} questions, {len(traces)} query-strategy traces.")
    print(json.dumps(summarize(traces), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
