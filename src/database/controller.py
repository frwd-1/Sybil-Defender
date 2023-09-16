from sqlalchemy import create_engine, Column, String, BigInteger, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine
from datetime import datetime
import logging
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
LOG_ENABLED = True  # Global switch to enable or disable logging
# Database Configuration
DATABASE_URL = os.environ.get("POSTGRESQL_DATABASE_URL")
# Adjust as necessary

# engine = create_engine(DATABASE_URL)
async_engine = create_async_engine(DATABASE_URL, echo=False, future=True)

Base = declarative_base()


# Define tables
class EOA(Base):
    __tablename__ = "eoas"

    # Change default to a callable function that generates a new UUID
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    address = Column(String, unique=False)  # Address


class Transaction(Base):
    __tablename__ = "transactions"
    tx_hash = Column(String, primary_key=True)
    sender = Column(String)
    receiver = Column(String)
    amount = Column(BigInteger)
    timestamp = Column(DateTime, default=datetime.utcnow)


async def create_tables():
    print("creating tables")
    async with async_engine.begin() as conn:
        print("connection started")
        await conn.run_sync(Base.metadata.create_all)

    if LOG_ENABLED:
        logger.info("Database initialized")
