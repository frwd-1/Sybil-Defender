from sqlalchemy import Integer, Numeric, Column, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from dotenv import load_dotenv
import datetime


load_dotenv()

Base = declarative_base()


# class Interactions(Base):
#     __tablename__ = "interactions"
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     address = Column(String, unique=False)


class Transfer(Base):
    __tablename__ = "transfers"
    tx_hash = Column(String, primary_key=True)
    sender = Column(String)
    receiver = Column(String)
    amount = Column(Numeric)
    gas_price = Column(Numeric)
    timestamp = Column(Integer)
    processed = Column(Boolean, default=False)


class ContractTransaction(Base):
    __tablename__ = "contract_transactions"
    tx_hash = Column(String, primary_key=True)
    sender = Column(String)
    contract_address = Column(String)
    amount = Column(Numeric)
    timestamp = Column(Integer)
    data = Column(String)
    processed = Column(Boolean, default=False)


class SybilClusters(Base):
    __tablename__ = "sybil_clusters"
    id = Column(Integer, primary_key=True, autoincrement=True)
    cluster_id = Column(String, nullable=False)
    address = Column(String, nullable=False)
    labels = Column(String)
    creation_timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    last_update_timestamp = Column(DateTime, onupdate=datetime.datetime.utcnow)

    def __init__(self, cluster_id, address, labels):
        self.cluster_id = cluster_id
        self.address = address
        self.labels = labels

    def __repr__(self):
        return (
            f"<SybilCluster(cluster_id={self.cluster_id}, address={self.address}, labels={self.labels}, "
            f"creation_timestamp={self.creation_timestamp}, last_update_timestamp={self.last_update_timestamp})>"
        )
