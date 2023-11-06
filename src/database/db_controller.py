from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.utils import globals
from contextlib import asynccontextmanager
from dotenv import load_dotenv
import os
import asyncio

load_dotenv()

DATABASE_URL = os.environ.get("POSTGRESQL_DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_async_session():
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()


async def initialize_database():
    if not globals.database_initialized:
        print("creating tables")
        await create_tables()
        globals.database_initialized = True


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("database initialized")
