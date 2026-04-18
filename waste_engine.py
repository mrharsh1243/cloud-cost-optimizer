from datetime import datetime, timedelta

# ==================================================
# MAIN ENTRY
# ==================================================

def get_rules(db):
    from db import RuleConfig
    configs = db.query(RuleConfig).all()
    return {c.rule_name: {"enabled": c.is_enabled, "threshold": c.threshold_value} for c in configs}

def run_waste_scan():
    from db import SessionLocal, Waste

    db = SessionLocal()
    db.query(Waste).delete()

    rules = get_rules(db)

    detect_ec2_waste(db, rules)
    detect_ebs_waste(db, rules)
    detect_snapshot_waste(db, rules)
    detect_eip_waste(db, rules)
    detect_lb_waste(db, rules)
    detect_nat_waste(db, rules)
    detect_rds_waste(db, rules)

    db.commit()
    db.close()


# ==================================================
# EC2 RULE
# ==================================================

def detect_ec2_waste(db, rules):
    from db import Resource, Waste

    now = datetime.utcnow()
    resources = db.query(Resource).all()

    stopped_rule = rules.get("EC2_STOPPED_AGE", {"enabled": False, "threshold": 7})
    idle_rule = rules.get("EC2_IDLE_CPU", {"enabled": False, "threshold": 5.0})

    for r in resources:
        if r.state == "stopped" and stopped_rule["enabled"]:
            try:
                clean_time = r.launch_time.split("+")[0].strip()
                age_days = (now - datetime.fromisoformat(clean_time)).days
                if age_days > stopped_rule["threshold"]:
                    db.add(
                        Waste(
                            resource_type="EC2",
                            resource_id=r.instance_id,
                            resource_name=r.instance_name,
                            region=r.region,
                            reason=f"EC2 instance stopped for > {int(stopped_rule['threshold'])} days",
                            estimated_monthly_savings=0,
                            detected_at=str(now)
                        )
                    )
            except Exception as e:
                print(f"Error parsing launch_time for {r.instance_id}: {e}")
        elif r.state != "stopped" and idle_rule["enabled"]:
            if r.avg_cpu is not None and r.avg_cpu < idle_rule["threshold"]:
                db.add(
                    Waste(
                        resource_type="EC2",
                        resource_id=r.instance_id,
                        resource_name=r.instance_name,
                        region=r.region,
                        reason=f"EC2 instance average CPU < {idle_rule['threshold']}% for 7 days",
                        estimated_monthly_savings=0,
                        detected_at=str(now)
                    )
                )


# ==================================================
# EBS RULE
# ==================================================

def detect_ebs_waste(db, rules):
    from db import EBSVolume, Waste

    if not rules.get("EBS_UNATTACHED", {"enabled": False})["enabled"]:
        return

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

def detect_snapshot_waste(db, rules):
    from db import Snapshot, Waste

    rule = rules.get("EBS_SNAPSHOT_AGE", {"enabled": False, "threshold": 30})
    if not rule["enabled"]:
        return

    now = datetime.utcnow()
    snapshots = db.query(Snapshot).all()

    for s in snapshots:
        try:
            age_days = (now - datetime.fromisoformat(s.start_time.replace("Z", ""))).days
            if age_days > rule["threshold"]:
                db.add(
                    Waste(
                        resource_type="SNAPSHOT",
                        resource_id=s.snapshot_id,
                        resource_name=f"Snapshot {age_days} days old",
                        region=s.region,
                        reason=f"Old snapshot (> {int(rule['threshold'])} days)",
                        estimated_monthly_savings=0,
                        detected_at=str(now)
                    )
                )
        except:
            continue


# ==================================================
# EIP RULE
# ==================================================

def detect_eip_waste(db, rules):
    from db import ElasticIP, Waste

    if not rules.get("EIP_UNASSOCIATED", {"enabled": False})["enabled"]:
        return

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
# LOAD BALANCER RULE
# ==================================================

def detect_lb_waste(db, rules):
    from db import LoadBalancer, Waste

    now = datetime.utcnow()
    lbs = db.query(LoadBalancer).all()
    
    target_rule = rules.get("LB_NO_TARGETS", {"enabled": False})
    traffic_rule = rules.get("LB_NO_TRAFFIC", {"enabled": False})

    for lb in lbs:
        if lb.target_count == 0 and target_rule["enabled"]:
            db.add(
                Waste(
                    resource_type="LB",
                    resource_id=lb.lb_arn,
                    resource_name=lb.lb_name,
                    region=lb.region,
                    reason="Load balancer with 0 targets",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )
        elif lb.request_count == 0 and traffic_rule["enabled"]:
            db.add(
                Waste(
                    resource_type="LB",
                    resource_id=lb.lb_arn,
                    resource_name=lb.lb_name,
                    region=lb.region,
                    reason="Load balancer with no traffic in 7 days",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )

# ==================================================
# NAT RULE
# ==================================================
def detect_nat_waste(db, rules):
    from db import NatGateway, Waste

    now = datetime.utcnow()
    nats = db.query(NatGateway).all()
    
    route_rule = rules.get("NAT_NO_ROUTE", {"enabled": False})
    traffic_rule = rules.get("NAT_NO_TRAFFIC", {"enabled": False})

    for nat in nats:
        if nat.attached_route_tables == 0 and route_rule["enabled"]:
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
        elif nat.total_traffic_gb == 0 and traffic_rule["enabled"]:
            db.add(
                Waste(
                    resource_type="NAT",
                    resource_id=nat.nat_gateway_id,
                    resource_name=f"NAT in {nat.subnet_id}",
                    region=nat.region,
                    reason="NAT Gateway with no traffic in 7 days",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )

# ==================================================
# RDS RULE
# ==================================================

def detect_rds_waste(db, rules):
    from db import RDSInstance, RDSSnapshot, Waste

    now = datetime.utcnow()
    instances = db.query(RDSInstance).all()
    
    stopped_rule = rules.get("RDS_STOPPED", {"enabled": False})
    traffic_rule = rules.get("RDS_IDLE_CONN", {"enabled": False})
    snap_rule = rules.get("RDS_SNAPSHOT_AGE", {"enabled": False, "threshold": 30})

    for i in instances:
        if i.db_instance_status == "stopped" and stopped_rule["enabled"]:
            db.add(
                Waste(
                    resource_type="RDS",
                    resource_id=i.db_instance_identifier,
                    resource_name=i.db_instance_identifier,
                    region=i.region,
                    reason="Stopped RDS instance",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )
        elif i.max_connections == 0 and traffic_rule["enabled"]:
            db.add(
                Waste(
                    resource_type="RDS",
                    resource_id=i.db_instance_identifier,
                    resource_name=i.db_instance_identifier,
                    region=i.region,
                    reason="RDS instance with 0 connections in 7 days",
                    estimated_monthly_savings=0,
                    detected_at=str(now)
                )
            )

    if snap_rule["enabled"]:
        snapshots = db.query(RDSSnapshot).all()
        for s in snapshots:
            try:
                clean_time = s.snapshot_create_time.split("+")[0].strip()
                age_days = (now - datetime.fromisoformat(clean_time)).days
                if age_days > snap_rule["threshold"]:
                    db.add(
                        Waste(
                            resource_type="RDS_SNAPSHOT",
                            resource_id=s.db_snapshot_identifier,
                            resource_name=s.db_snapshot_identifier,
                            region=s.region,
                            reason=f"Old RDS snapshot (> {int(snap_rule['threshold'])} days)",
                            estimated_monthly_savings=0,
                            detected_at=str(now)
                        )
                    )
            except:
                continue