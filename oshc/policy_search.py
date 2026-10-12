"""Offline BM25 development baseline. Returns excerpts, never generated advice.

This is not the hybrid retriever promised by oshc.retrieval.search. Its ranking
scores are not confidence values, and it does not replace the safety gate.
"""
from __future__ import annotations

import re
import unicodedata

from rank_bm25 import BM25Okapi

from oshc.policy_source import CAPTURED_ON, SOURCE_DOC, SOURCE_URL, PolicyCorpus
from oshc.schemas import RetrievalHit

_STOP = set("a an and are as at be by can for from how i in is it me my of on or our "
            "that the their this to us we what when where which with would you your".split())


def tokens(text: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", text).casefold())
            if word not in _STOP]


class PolicySearch:
    def __init__(self, corpus: PolicyCorpus):
        self.chunks = corpus.chunks
        if not self.chunks or len({item.chunk_id for item in self.chunks}) != len(self.chunks):
            raise ValueError("The corpus must contain chunks with unique IDs.")
        documents = [tokens(chunk.text) for chunk in self.chunks]
        if any(not document for document in documents):
            raise ValueError("Every indexed chunk must contain searchable text.")
        self.bm25 = BM25Okapi(documents)

    def search(self, query: str, *, k: int = 5) -> list[RetrievalHit]:
        if not isinstance(query, str) or len(query) > 2000:
            raise ValueError("Use a text query of at most 2000 characters.")
        if type(k) is not int or not 1 <= k <= 20:
            raise ValueError("k must be an integer from 1 to 20.")
        query_tokens = sorted(set(tokens(query)))
        if not query_tokens:
            return []
        scores = self.bm25.get_scores(query_tokens)
        ranked = sorted(((float(score), chunk) for score, chunk in zip(scores, self.chunks)
                         if score > 0), key=lambda pair: (-pair[0], pair[1].chunk_id))[:k]
        return [RetrievalHit(chunk_id=chunk.chunk_id, text=chunk.text, source_doc=SOURCE_DOC,
                            source_url=f"{SOURCE_URL}#page={chunk.page}",
                            section=f"PDF page {chunk.page}, {chunk.column} column",
                            captured_on=CAPTURED_ON, score=score, rank=rank)
                for rank, (score, chunk) in enumerate(ranked, 1)]
