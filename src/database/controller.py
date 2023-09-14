from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine
from datetime import datetime
import logging

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
LOG_ENABLED = True  # Global switch to enable or disable logging
# Database Configuration
DATABASE_URL = "sqlite+aiosqlite:///./src/database/main.db"
# Adjust as necessary

engine = create_engine(DATABASE_URL)
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)

Base = declarative_base()


# Define tables
class EOA(Base):
    __tablename__ = "eoas"
    address = Column(String, primary_key=True)


class Transaction(Base):
    __tablename__ = "transactions"
    tx_hash = Column(String, primary_key=True)
    sender = Column(String)
    receiver = Column(String)
    amount = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)


async def create_tables():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if LOG_ENABLED:
        logger.info("Database initialized")
