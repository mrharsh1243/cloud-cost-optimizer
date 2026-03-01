from datetime import datetime

# ==================================================
# MAIN ENTRY
# ==================================================

def run_waste_scan():
    from db import SessionLocal, Waste

    db = SessionLocal()
    db.query(Waste).delete()

    detect_ec2_waste(db)
    detect_ebs_waste(db)
    detect_snapshot_waste(db)
    detect_eip_waste(db)
    detect_lb_waste(db)
    detect_nat_waste(db)

    db.commit()
    db.close()


# ==================================================
# EC2 RULE
# ==================================================

def detect_ec2_waste(db):
    from db import Resource, Waste

    now = datetime.utcnow()
    resources = db.query(Resource).all()

    for r in resources:
        if r.state == "stopped":
            db.add(
                Waste(
                    resource_type="EC2",
                    resource_id=r.instance_id,
                    resource_name=r.instance_name,
                    region=r.region,
                    reason="Stopped EC2 instance",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )


# ==================================================
# EBS RULE
# ==================================================

def detect_ebs_waste(db):
    from db import EBSVolume, Waste

    now = datetime.utcnow()
    volumes = db.query(EBSVolume).all()

    for v in volumes:
        if not v.attached_instance:
            db.add(
                Waste(
                    resource_type="EBS",
                    resource_id=v.volume_id,
                    resource_name=f"{v.size_gb}GB volume",
                    region=v.region,
                    reason="Unattached EBS volume",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )


# ==================================================
# SNAPSHOT RULE
# ==================================================

def detect_snapshot_waste(db):
    from db import Snapshot, Waste

    now = datetime.utcnow()
    snapshots = db.query(Snapshot).all()

    for s in snapshots:
        age_days = (now - datetime.fromisoformat(s.start_time.replace("Z", ""))).days
        if age_days > 30:
            db.add(
                Waste(
                    resource_type="SNAPSHOT",
                    resource_id=s.snapshot_id,
                    resource_name=f"Snapshot {age_days} days old",
                    region=s.region,
                    reason="Old snapshot (>30 days)",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )


# ==================================================
# EIP RULE
# ==================================================

def detect_eip_waste(db):
    from db import ElasticIP, Waste

    now = datetime.utcnow()
    eips = db.query(ElasticIP).all()

    for eip in eips:
        if not eip.associated_instance:
            db.add(
                Waste(
                    resource_type="EIP",
                    resource_id=eip.allocation_id,
                    resource_name=eip.public_ip,
                    region=eip.region,
                    reason="Unattached Elastic IP",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )


# ==================================================
# LOAD BALANCER RULE (DAY 12)
# ==================================================

def detect_lb_waste(db):
    from db import LoadBalancer, Waste

    now = datetime.utcnow()
    lbs = db.query(LoadBalancer).all()

    for lb in lbs:
        if lb.target_count == 0:
            db.add(
                Waste(
                    resource_type="LB",
                    resource_id=lb.lb_arn,
                    resource_name=lb.lb_name,
                    region=lb.region,
                    reason="Load balancer with no registered targets",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )

# ==================================================
# NAT RULE (DAY 13)
# ==================================================
def detect_nat_waste(db):
    from db import NatGateway, Waste

    now = datetime.utcnow()
    nats = db.query(NatGateway).all()

    for nat in nats:
        if nat.attached_route_tables == 0:
            db.add(
                Waste(
                    resource_type="NAT",
                    resource_id=nat.nat_gateway_id,
                    resource_name=f"NAT in {nat.subnet_id}",
                    region=nat.region,
                    reason="NAT Gateway not attached to any route table",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )
