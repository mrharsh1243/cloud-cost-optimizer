from fastapi import FastAPI
import boto3
from sqlalchemy import create_engine, Column, Integer, String, Float
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
from collections import defaultdict

# ==================================================
# APP
# ==================================================
app = FastAPI()

# ==================================================
# AWS CONFIG
# ==================================================
ACCOUNT_ID = "664418997920"
ROLE_NAME = "CloudOptimizerRole"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}"
COST_REGION = "us-east-1"  # Cost Explorer is global

# ==================================================
# DATABASE
# ==================================================
DATABASE_URL = "sqlite:///cloud.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ==================================================
# TABLES
# ==================================================

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

Base.metadata.create_all(bind=engine)

# ==================================================
# AWS HELPERS
# ==================================================

def assume_role():
    sts = boto3.client("sts")
    return sts.assume_role(
        RoleArn=ROLE_ARN,
        RoleSessionName="cloud-optimizer"
    )["Credentials"]

def get_all_regions():
    creds = assume_role()
    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name="us-east-1"
    )
    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]

# ==================================================
# SCAN HELPERS (MULTI-REGION)
# ==================================================

def scan_ec2_all_regions():
    creds = assume_role()
    results = []

    for region in get_all_regions():
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region
        )
        results.append((region, ec2.describe_instances()))

    return results

def scan_ebs_all_regions():
    creds = assume_role()
    results = []

    for region in get_all_regions():
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region
        )
        results.append((region, ec2.describe_volumes()))

    return results

def scan_snapshots_all_regions():
    creds = assume_role()
    results = []

    for region in get_all_regions():
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region
        )
        results.append((region, ec2.describe_snapshots(OwnerIds=["self"])))

    return results

def scan_cost_data():
    creds = assume_role()
    ce = boto3.client(
        "ce",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=COST_REGION
    )

    end = datetime.utcnow().date()
    start = end - timedelta(days=30)

    resp = ce.get_cost_and_usage(
        TimePeriod={"Start": str(start), "End": str(end)},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}]
    )

    return resp["ResultsByTime"][0]["Groups"], start, end

# ==================================================
# APIs
# ==================================================

@app.get("/")
def home():
    return {"status": "Cloud Cost Optimizer running"}

# --------------------------
# SCAN EC2
# --------------------------

@app.post("/scan")
def scan_resources():
    db = SessionLocal()
    db.query(Resource).delete()

    for region, data in scan_ec2_all_regions():
        for res in data["Reservations"]:
            for inst in res["Instances"]:
                name = "Unnamed"
                for tag in inst.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]

                db.add(Resource(
                    instance_id=inst["InstanceId"],
                    instance_name=name,
                    instance_type=inst["InstanceType"],
                    state=inst["State"]["Name"],
                    launch_time=str(inst["LaunchTime"]),
                    region=region,
                    last_seen=str(datetime.utcnow())
                ))

    db.commit()
    db.close()
    return {"status": "EC2 scanned (all regions)"}

# --------------------------
# SCAN EBS
# --------------------------

@app.post("/scan-ebs")
def scan_ebs():
    db = SessionLocal()
    db.query(EBSVolume).delete()

    for region, data in scan_ebs_all_regions():
        for v in data["Volumes"]:
            attached = v["Attachments"][0]["InstanceId"] if v["Attachments"] else None
            db.add(EBSVolume(
                volume_id=v["VolumeId"],
                size_gb=v["Size"],
                state=v["State"],
                attached_instance=attached,
                region=region,
                last_seen=str(datetime.utcnow())
            ))

    db.commit()
    db.close()
    return {"status": "EBS scanned (all regions)"}

# --------------------------
# SCAN SNAPSHOTS
# --------------------------

@app.post("/scan-snapshots")
def scan_snapshots():
    db = SessionLocal()
    db.query(Snapshot).delete()

    for region, data in scan_snapshots_all_regions():
        for s in data["Snapshots"]:
            db.add(Snapshot(
                snapshot_id=s["SnapshotId"],
                volume_id=s.get("VolumeId"),
                start_time=str(s["StartTime"]),
                region=region,
                last_seen=str(datetime.utcnow())
            ))

    db.commit()
    db.close()
    return {"status": "Snapshots scanned (all regions)"}

# --------------------------
# SCAN COST
# --------------------------

@app.post("/scan-cost")
def scan_cost():
    db = SessionLocal()
    db.query(Cost).delete()

    groups, start, end = scan_cost_data()

    for g in groups:
        db.add(Cost(
            service=g["Keys"][0],
            amount=float(g["Metrics"]["UnblendedCost"]["Amount"]),
            start_date=str(start),
            end_date=str(end),
            last_updated=str(datetime.utcnow())
        ))

    db.commit()
    db.close()
    return {"status": "Cost scanned"}

# --------------------------
# WASTE RULES
# --------------------------

@app.post("/scan-waste")
def scan_waste():
    db = SessionLocal()
    db.query(Waste).delete()

    for r in db.query(Resource).all():
        if r.state == "stopped":
            db.add(Waste(
                resource_type="EC2",
                resource_id=r.instance_id,
                resource_name=r.instance_name,
                region=r.region,
                reason="Stopped EC2",
                estimated_monthly_savings=0,
                detected_at=str(datetime.utcnow())
            ))

    for v in db.query(EBSVolume).all():
        if not v.attached_instance:
            db.add(Waste(
                resource_type="EBS",
                resource_id=v.volume_id,
                resource_name=f"{v.size_gb}GB volume",
                region=v.region,
                reason="Unattached EBS",
                estimated_monthly_savings=0,
                detected_at=str(datetime.utcnow())
            ))

    now = datetime.utcnow()
    for s in db.query(Snapshot).all():
        age = (now - datetime.fromisoformat(s.start_time.replace("Z", ""))).days
        if age > 30:
            db.add(Waste(
                resource_type="SNAPSHOT",
                resource_id=s.snapshot_id,
                resource_name=f"{age} days old",
                region=s.region,
                reason="Old snapshot",
                estimated_monthly_savings=0,
                detected_at=str(datetime.utcnow())
            ))

    db.commit()
    db.close()
    return {"status": "Waste scanned"}

# --------------------------
# GET DATA
# --------------------------

@app.get("/resources")
def get_resources():
    db = SessionLocal()
    data = db.query(Resource).all()
    db.close()
    return data

@app.get("/waste")
def get_waste():
    db = SessionLocal()
    rows = db.query(Waste).all()
    db.close()

    summary = {
        "EC2": {
            "scanned": True,
            "waste_found": False,
            "count": 0,
            "message": "No stopped EC2 instances found"
        },
        "EBS": {
            "scanned": True,
            "waste_found": False,
            "count": 0,
            "message": "No unattached EBS volumes found"
        },
        "SNAPSHOT": {
            "scanned": True,
            "waste_found": False,
            "count": 0,
            "message": "No snapshots older than 30 days found"
        }
    }

    data = []

    for w in rows:
        rtype = w.resource_type
        summary[rtype]["count"] += 1
        summary[rtype]["waste_found"] = True

        data.append({
            "resource_type": w.resource_type,
            "resource_id": w.resource_id,
            "resource_name": w.resource_name,
            "region": w.region,
            "reason": w.reason
        })

    # Update messages dynamically
    if summary["EC2"]["count"] > 0:
        summary["EC2"]["message"] = f'{summary["EC2"]["count"]} stopped EC2 instance(s) detected'

    if summary["EBS"]["count"] > 0:
        summary["EBS"]["message"] = f'{summary["EBS"]["count"]} unattached EBS volume(s) detected'

    if summary["SNAPSHOT"]["count"] > 0:
        summary["SNAPSHOT"]["message"] = f'{summary["SNAPSHOT"]["count"]} old snapshot(s) detected'

    return {
        "status": "success",
        "summary": summary,
        "data": data
    }


@app.get("/summary")
def summary():
    db = SessionLocal()
    total_cost = sum(c.amount for c in db.query(Cost).all())
    wasted = sum(w.estimated_monthly_savings for w in db.query(Waste).all())
    db.close()

    return {
        "total_monthly_cost": round(total_cost, 2),
        "wasted_cost": round(wasted, 2),
        "potential_savings": round(wasted, 2)
    }
