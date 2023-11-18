from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.utils import globals
from contextlib import asynccontextmanager
import os
import asyncio


def get_database_url(network_name):
    return f"sqlite+aiosqlite:///{network_name}_database.db"


@asynccontextmanager
async def get_async_session(network_name):
    engine = create_async_engine(get_database_url(network_name), echo=False)
    AsyncSessionLocal = sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()
        await engine.dispose()


# Initialize and create tables for a specific network
async def initialize_database(network_name):
    engine = create_async_engine(get_database_url(network_name), echo=False)
    if not globals.database_initialized:
        print(f"Creating tables for {network_name} database")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        globals.database_initialized = True
    await engine.dispose()


# from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
# from sqlalchemy.orm import sessionmaker
# from src.database.models import Base
# from src.utils import globals
# from contextlib import asynccontextmanager
# from dotenv import load_dotenv
# import os
# import asyncio

# load_dotenv()

# DATABASE_URL = os.environ.get("POSTGRESQL_DATABASE_URL")

# engine = create_async_engine(DATABASE_URL, echo=False)
# AsyncSessionLocal = sessionmaker(
#     bind=engine, class_=AsyncSession, expire_on_commit=False
# )


# @asynccontextmanager
# async def get_async_session():
#     session = AsyncSessionLocal()
#     try:
#         yield session
#         await session.commit()
#     except Exception as e:
#         await session.rollback()
#         raise
#     finally:
#         await session.close()


# async def initialize_database():
#     if not globals.database_initialized:
#         print("creating tables")
#         await create_tables()
#         globals.database_initialized = True


# async def create_tables():
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)
#     print("database initialized")
