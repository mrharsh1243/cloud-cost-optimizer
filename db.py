from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = "sqlite:///cloud.db"

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True)
    instance_id = Column(String)
    instance_name = Column(String)
    instance_type = Column(String)
    state = Column(String)
    launch_time = Column(String)
    region = Column(String)
    last_seen = Column(String)

class Cost(Base):
    __tablename__ = "costs"

    id = Column(Integer, primary_key=True)
    service = Column(String)
    amount = Column(Float)
    start_date = Column(String)
    end_date = Column(String)
    last_updated = Column(String)

class Waste(Base):
    __tablename__ = "waste"

    id = Column(Integer, primary_key=True)
    resource_type = Column(String)
    resource_id = Column(String)
    resource_name = Column(String)
    region = Column(String)
    reason = Column(String)
    estimated_monthly_savings = Column(Float)
    detected_at = Column(String)

class EBSVolume(Base):
    __tablename__ = "ebs_volumes"

    id = Column(Integer, primary_key=True)
    volume_id = Column(String)
    size_gb = Column(Integer)
    state = Column(String)
    attached_instance = Column(String)
    region = Column(String)
    last_seen = Column(String)

class Snapshot(Base):
    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True)
    snapshot_id = Column(String)
    volume_id = Column(String)
    start_time = Column(String)
    region = Column(String)
    last_seen = Column(String)

class ElasticIP(Base):
    __tablename__ = "elastic_ips"

    id = Column(Integer, primary_key=True)
    allocation_id = Column(String)
    public_ip = Column(String)
    associated_instance = Column(String)
    region = Column(String)
    last_seen = Column(String)

class LoadBalancer(Base):
    __tablename__ = "load_balancers"

    id = Column(Integer, primary_key=True)
    lb_arn = Column(String)
    lb_name = Column(String)
    lb_type = Column(String)      # application / network
    region = Column(String)
    target_count = Column(Integer)
    last_seen = Column(String)

Base.metadata.create_all(bind=engine)

