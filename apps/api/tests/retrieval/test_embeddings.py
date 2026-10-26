import math

import pytest

from investigation_engine.core.config import Settings
from investigation_engine.retrieval.embeddings import Embedder

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    settings = Settings(env="test")
    return Embedder(settings.embedding_model, settings.embedding_query_prefix)


def _cosine(first: list[float], second: list[float]) -> float:
    dot = sum(a * b for a, b in zip(first, second, strict=True))
    return dot / (math.hypot(*first) * math.hypot(*second))


def test_embed_passages_returns_one_dense_and_sparse_vector_per_text(embedder: Embedder) -> None:
    embeddings = embedder.embed_passages(["Payments slowed down.", "A film by Ed Wood."])

    assert len(embeddings) == 2
    assert all(len(embedding.dense) == embedder.dense_size for embedding in embeddings)
    assert all(embedding.sparse.indices for embedding in embeddings)


def test_dense_query_is_closest_to_the_passage_with_the_same_meaning(embedder: Embedder) -> None:
    payments, film = embedder.embed_passages(
        [
            "Checkout latency rose after the database connection pool was reduced.",
            "Ed Wood is a 1994 biographical film directed by Tim Burton.",
        ]
    )

    query = embedder.embed_query("Why were payments slow?")

    assert _cosine(query.dense, payments.dense) > _cosine(query.dense, film.dense)


def test_sparse_query_matches_exact_terms(embedder: Embedder) -> None:
    (passage,) = embedder.embed_passages(["CHG-2291 reduced the payments-db pool."])

    query = embedder.embed_query("What did CHG-2291 change?")

    assert set(query.sparse.indices) & set(passage.sparse.indices)
