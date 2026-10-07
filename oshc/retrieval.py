"""Hybrid BM25 + dense retrieval with reciprocal rank fusion.

Owner: Aayush Khade. Reviewer: Bikram Bhattarai.

The corpus is frozen under corpus/ and is chunked by oshc.chunker.
No reranker is used.
"""

from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from oshc.chunker import Chunk, build_chunks
from oshc.schemas import RetrievalHit


EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RRF_K = 60


def _tokenize(text: str) -> list[str]:
    """Tokenize text for BM25."""
    return re.findall(r"\b\w+\b", text.lower())


@lru_cache(maxsize=1)
def _load_index() -> tuple[
    list[Chunk],
    BM25Okapi,
    SentenceTransformer,
    np.ndarray,
]:
    """Build the retrieval index once and reuse it."""
    chunks = build_chunks()

    if not chunks:
        raise RuntimeError("No chunks were produced from the frozen corpus.")

    documents = [chunk.text for chunk in chunks]

    bm25_tokens = [_tokenize(document) for document in documents]
    bm25 = BM25Okapi(bm25_tokens)

    model = SentenceTransformer(EMBEDDING_MODEL)

    embeddings = model.encode(
        documents,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )

    return chunks, bm25, model, embeddings


def _rrf_score(rank: int) -> float:
    """Calculate the reciprocal rank fusion contribution."""
    return 1.0 / (RRF_K + rank)


def search(query: str, *, k: int = 5) -> list[RetrievalHit]:
    """Hybrid BM25 plus dense cosine, reciprocal rank fusion. No reranker.

    Owner: Aayush Khade. Reviewer: Bikram Bhattarai.
    """
    if not query.strip():
        return []

    if k < 1:
        raise ValueError("k must be at least 1.")

    chunks, bm25, model, embeddings = _load_index()

    # BM25 ranking.
    query_tokens = _tokenize(query)
    bm25_scores = np.asarray(bm25.get_scores(query_tokens))

    bm25_order = np.argsort(-bm25_scores, kind="stable")

    # Dense cosine ranking.
    query_embedding = model.encode(
        [query],
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]

    dense_scores = embeddings @ query_embedding
    dense_order = np.argsort(-dense_scores, kind="stable")

    # RRF combines the rankings rather than the raw BM25/dense scores.
    fused_scores: dict[int, float] = {}

    for rank, index in enumerate(bm25_order, start=1):
        fused_scores[int(index)] = fused_scores.get(int(index), 0.0) + _rrf_score(rank)

    for rank, index in enumerate(dense_order, start=1):
        fused_scores[int(index)] = fused_scores.get(int(index), 0.0) + _rrf_score(rank)

    ranked_indices = sorted(
        fused_scores,
        key=lambda index: (-fused_scores[index], index),
    )[:k]

    hits: list[RetrievalHit] = []

    for rank, index in enumerate(ranked_indices, start=1):
        chunk = chunks[index]

        hits.append(
            RetrievalHit(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                source_doc=chunk.source_doc,
                source_url=chunk.source_url,
                section=chunk.section,
                captured_on=chunk.captured_on,
                score=fused_scores[index],
                rank=rank,
            )
        )

    return hits