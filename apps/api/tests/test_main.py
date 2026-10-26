from fastapi.testclient import TestClient

from investigation_engine.core.config import Settings
from investigation_engine.core.errors import NotFoundError
from investigation_engine.main import create_app


def test_app_error_is_mapped_to_error_envelope() -> None:
    app = create_app(Settings(env="test"))

    @app.get("/missing")
    async def missing() -> None:
        raise NotFoundError("Document 42 does not exist")

    client = TestClient(app)

    response = client.get("/missing")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Document 42 does not exist"}
    }
