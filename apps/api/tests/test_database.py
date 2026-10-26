from investigation_engine.core.database import to_asyncpg_url


def test_to_asyncpg_url_moves_sslmode_into_connect_args() -> None:
    raw_url = "postgresql://user:secret@db.example.com/app?sslmode=require&channel_binding=require"

    url, connect_args = to_asyncpg_url(raw_url)

    assert url.drivername == "postgresql+asyncpg"
    assert url.host == "db.example.com"
    assert url.password == "secret"
    assert dict(url.query) == {}
    assert connect_args == {"ssl": "require"}


def test_to_asyncpg_url_without_ssl_has_no_connect_args() -> None:
    url, connect_args = to_asyncpg_url("postgresql://postgres:postgres@localhost:5440/app")

    assert url.drivername == "postgresql+asyncpg"
    assert url.port == 5440
    assert connect_args == {}
