from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

# Database Configuration
DATABASE_URL = "sqlite+aiosqlite:///./database/main.db"

# Synchronous Engine (Adjust as necessary)
engine = create_engine(DATABASE_URL)

# Asynchronous Engine
async_engine = create_async_engine(DATABASE_URL, echo=False)

# Creating an async session factory bound to the async engine
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

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


# Create tables synchronously (keep in mind, for production you might want a separate script or mechanism for migrations)
Base.metadata.create_all(engine)
