from collections.abc import Callable
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import run_sql

pytestmark = pytest.mark.integration

RUNBOOK = b"# Timeouts\n\nFraud scoring times out after 3 seconds.\n\n## Retries\n\nOne retry."
CHANGELOG = b"CHG-2291 reduced the payments-db pool from 50 to 20 connections."


def _upload(client: TestClient, *files: tuple[str, bytes]) -> list[dict[str, object]]:
    response = client.post("/documents", files=[("files", file) for file in files])
    assert response.status_code == 200
    results: list[dict[str, object]] = response.json()["results"]
    return results


def _uploaded_id(client: TestClient, name: str, content: bytes) -> str:
    (result,) = _upload(client, (name, content))
    document = result["document"]
    assert isinstance(document, dict)
    return str(document["id"])


def _insert_dataset_document(document_id: str) -> None:
    run_sql(
        "INSERT INTO documents (id, title, file_type, origin, text, content_hash, chunk_count,"
        " file_metadata) VALUES ($1, 'Ed Wood', 'txt', 'dataset', 'A film.', 'hash', 1, '{}')",
        document_id,
    )


def test_upload_indexes_the_document_and_its_chunks(
    client: TestClient, qdrant_point_count: Callable[[], int]
) -> None:
    (result,) = _upload(client, ("runbook.md", RUNBOOK))

    assert result["status"] == "indexed"
    assert result["fileName"] == "runbook.md"
    document = result["document"]
    assert isinstance(document, dict)
    assert document["fileType"] == "md"
    assert document["origin"] == "upload"
    assert document["chunkCount"] == 2  # one chunk per heading section
    assert qdrant_point_count() == 2


def test_upload_reports_each_file_on_its_own(client: TestClient) -> None:
    results = _upload(
        client,
        ("runbook.md", RUNBOOK),
        ("copy-of-runbook.md", RUNBOOK),
        ("page.html", b"<p>hi</p>"),
        ("blank.txt", b"   "),
    )

    assert [result["status"] for result in results] == ["indexed", "duplicate", "failed", "failed"]
    indexed = results[0]["document"]
    assert isinstance(indexed, dict)
    assert results[1]["duplicateOfId"] == indexed["id"]
    assert results[2]["error"] == {
        "code": "unsupported_format",
        "message": "Unsupported file type “.html”. Use .docx, .markdown, .md, .pdf, .txt.",
    }
    error = results[3]["error"]
    assert isinstance(error, dict)
    assert error["code"] == "empty_document"


def test_upload_rejects_a_file_over_the_size_limit(client: TestClient) -> None:
    cast(FastAPI, client.app).state.settings.max_upload_bytes = 10

    (result,) = _upload(client, ("big.txt", b"x" * 11))

    assert result["status"] == "failed"
    error = result["error"]
    assert isinstance(error, dict)
    assert error["code"] == "file_too_large"


def test_list_documents_searches_and_paginates(client: TestClient) -> None:
    _upload(client, ("runbook.md", RUNBOOK), ("changelog.txt", CHANGELOG))

    first_page = client.get("/documents", params={"page": 1, "pageSize": 1}).json()
    search = client.get("/documents", params={"search": "CHANGE"}).json()

    assert first_page["total"] == 2
    assert first_page["pageSize"] == 1
    assert len(first_page["items"]) == 1
    assert [item["title"] for item in search["items"]] == ["changelog.txt"]


def test_list_documents_rejects_an_invalid_page_size(client: TestClient) -> None:
    response = client.get("/documents", params={"pageSize": 1000})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_input"


def test_replace_swaps_the_content_and_its_chunks(
    client: TestClient, qdrant_point_count: Callable[[], int]
) -> None:
    document_id = _uploaded_id(client, "runbook.md", RUNBOOK)

    response = client.put(f"/documents/{document_id}", files={"file": ("v2.txt", CHANGELOG)})

    assert response.status_code == 200
    assert response.json()["title"] == "v2.txt"
    assert response.json()["chunkCount"] == 1
    assert qdrant_point_count() == 1


def test_replace_rejects_content_indexed_as_another_document(client: TestClient) -> None:
    document_id = _uploaded_id(client, "runbook.md", RUNBOOK)
    other_id = _uploaded_id(client, "changelog.txt", CHANGELOG)

    response = client.put(f"/documents/{document_id}", files={"file": ("x.txt", CHANGELOG)})

    assert response.status_code == 409
    assert response.json()["error"] == {
        "code": "duplicate_document",
        "message": f"The same content is already indexed as {other_id}.",
    }


def test_delete_removes_the_document_and_its_chunks(
    client: TestClient, qdrant_point_count: Callable[[], int]
) -> None:
    document_id = _uploaded_id(client, "runbook.md", RUNBOOK)

    deleted = client.delete(f"/documents/{document_id}")
    deleted_again = client.delete(f"/documents/{document_id}")

    assert deleted.status_code == 204
    assert deleted_again.status_code == 404
    assert qdrant_point_count() == 0
    assert client.get("/documents").json()["total"] == 0


@pytest.mark.parametrize("method", ["put", "delete"])
def test_dataset_documents_are_read_only(client: TestClient, method: str) -> None:
    _insert_dataset_document("hotpot_ed_wood")

    if method == "put":
        response = client.put("/documents/hotpot_ed_wood", files={"file": ("x.txt", CHANGELOG)})
    else:
        response = client.delete("/documents/hotpot_ed_wood")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
