"""FastAPI dependencies shared by routes."""

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from investigation_engine.core.database import Database


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    """One database session per request, closed when the response is sent."""
    database: Database = request.app.state.database
    async with database.sessions() as session:
        yield session


SessionDependency = Annotated[AsyncSession, Depends(get_session)]
