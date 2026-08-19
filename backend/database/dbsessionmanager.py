"Module for managing database sessions"
import contextlib
from typing import Annotated, AsyncGenerator

from fastapi import Depends

from config import PSQL_CONN_STR
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


class DatabaseSessionManager:
    "Class for managing database sessions"

    def __init__(self, host: str):
        self._engine = create_async_engine(host, pool_size=20, max_overflow=100)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

    async def close(self):
        "Closes session manager"
        if self._engine is None:
            raise AttributeError("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection]:
        "Create a db connection"
        if self._engine is None:
            raise AttributeError("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        "Create a db session."
        if self._sessionmaker is None:
            raise AttributeError("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(PSQL_CONN_STR)

async def get_db_session():
    "Returns a generated session."
    async with sessionmanager.session() as session:
        yield session

DependsDb = Annotated[AsyncSession, Depends(get_db_session)]
