"""Shared fixtures for integration tests against the local services (`make services-up`)."""

import asyncio
import os
import uuid
import zlib
from collections.abc import Callable, Iterator, Sequence

import asyncpg
import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from qdrant_client import QdrantClient

from investigation_engine.core.config import Settings
from investigation_engine.main import create_app
from investigation_engine.retrieval.embeddings import Embedding, SparseVector

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5440/investigation_engine_test"
)
TEST_QDRANT_URL = os.environ.get("TEST_QDRANT_URL", "http://localhost:6333")


class FakeEmbedder:
    """Deterministic, instant stand-in for the real models: words hashed into 8 buckets."""

    dense_size = 8

    def embed_passages(self, texts: Sequence[str]) -> list[Embedding]:
        return [self._embed(text) for text in texts]

    def embed_query(self, query: str) -> Embedding:
        return self._embed(query)

    def _embed(self, text: str) -> Embedding:
        word_ids = sorted({zlib.crc32(word.encode()) for word in text.lower().split()})
        dense = [0.0] * self.dense_size
        for word_id in word_ids:
            dense[word_id % self.dense_size] += 1.0
        dense[0] += 0.01  # never an all-zero vector, which cosine distance can't handle
        return Embedding(
            dense=dense,
            sparse=SparseVector(indices=word_ids, values=[1.0] * len(word_ids)),
        )


async def _reset_test_database() -> None:
    """Creates the test database on first use and empties it before each test."""
    admin_url = TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"
    database_name = TEST_DATABASE_URL.rsplit("/", 1)[1]
    admin = await asyncpg.connect(admin_url)
    try:
        exists = await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", database_name)
        if not exists:
            await admin.execute(f'CREATE DATABASE "{database_name}"')
    finally:
        await admin.close()

    connection = await asyncpg.connect(TEST_DATABASE_URL)
    try:
        await connection.execute("DROP TABLE IF EXISTS documents")
    finally:
        await connection.close()


def run_sql(statement: str, *arguments: object) -> None:
    """Runs one statement against the test database (for setting up test data)."""

    async def run() -> None:
        connection = await asyncpg.connect(TEST_DATABASE_URL)
        try:
            await connection.execute(statement, *arguments)
        finally:
            await connection.close()

    asyncio.run(run())


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        env="test",
        database_url=SecretStr(TEST_DATABASE_URL),
        qdrant_url=TEST_QDRANT_URL,
        qdrant_api_key=None,
        qdrant_collection=f"test_{uuid.uuid4().hex}",
    )


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    """The app against a fresh test database and Qdrant collection, with the fake embedder."""
    asyncio.run(_reset_test_database())
    app = create_app(test_settings, embedder=FakeEmbedder())
    with TestClient(app) as test_client:  # `with` runs the app's startup and shutdown
        yield test_client
    qdrant = QdrantClient(url=TEST_QDRANT_URL)
    qdrant.delete_collection(test_settings.qdrant_collection)
    qdrant.close()


@pytest.fixture
def qdrant_point_count(test_settings: Settings) -> Iterator[Callable[[], int]]:
    """Returns a function that counts the points in the test collection."""
    qdrant = QdrantClient(url=TEST_QDRANT_URL)

    def count() -> int:
        return qdrant.count(test_settings.qdrant_collection, exact=True).count

    yield count
    qdrant.close()
