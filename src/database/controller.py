from sqlalchemy import create_engine, Column, String, Integer, DateTime, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine
from datetime import datetime

# Database Configuration
DATABASE_URL = "sqlite+aiosqlite:///./database/main.db"  # Adjust as necessary

engine = create_engine(DATABASE_URL, pool_size=10)
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


Base.metadata.create_all(engine)
