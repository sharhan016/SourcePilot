import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sourcepilot.config import Settings, get_settings
from sourcepilot.db import Base, get_session
from sourcepilot.main import create_app
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def session_factory(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest_asyncio.fixture
async def client(session_factory):
    app = create_app()

    async def override_session():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_settings] = lambda: Settings()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as test_client:
        yield test_client
