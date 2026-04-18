from fastapi import APIRouter, Body, HTTPException
from collections import defaultdict
from datetime import datetime
from db import (
    SessionLocal, Waste, Resource, Cost, EBSVolume, Snapshot, 
    ElasticIP, LoadBalancer, NatGateway, RDSInstance, RDSSnapshot, ScanLog, RuleConfig
)

router = APIRouter()

# ==================================================
# RESOURCES API
# ==================================================

@router.get("/resources")
def get_resources():
    db = SessionLocal()
    inventory = []

    # 1. EC2 Instances
    ec2_rows = db.query(Resource).all()
    for r in ec2_rows:
        inventory.append({
            "resource_type": "EC2",
            "resource_id": r.instance_id,
            "resource_name": r.instance_name,
            "state": r.state,
            "avg_cpu": r.avg_cpu,
            "region": r.region,
            "last_seen": r.last_seen
        })

    # 2. EBS Volumes
    ebs_rows = db.query(EBSVolume).all()
    for v in ebs_rows:
        inventory.append({
            "resource_type": "EBS",
            "resource_id": v.volume_id,
            "size_gb": v.size_gb,
            "state": v.state,
            "region": v.region,
            "last_seen": v.last_seen
        })

    # 3. Snapshots
    snap_rows = db.query(Snapshot).all()
    for s in snap_rows:
        inventory.append({
            "resource_type": "SNAPSHOT",
            "resource_id": s.snapshot_id,
            "volume_id": s.volume_id,
            "region": s.region,
            "last_seen": s.last_seen
        })

    # 4. Elastic IPs
    eip_rows = db.query(ElasticIP).all()
    for e in eip_rows:
        inventory.append({
            "resource_type": "EIP",
            "resource_id": e.allocation_id,
            "public_ip": e.public_ip,
            "region": e.region,
            "last_seen": e.last_seen
        })

    # 5. Load Balancers
    lb_rows = db.query(LoadBalancer).all()
    for l in lb_rows:
        inventory.append({
            "resource_type": "LB",
            "resource_id": l.lb_arn,
            "resource_name": l.lb_name,
            "type": l.lb_type,
            "target_count": l.target_count,
            "region": l.region,
            "last_seen": l.last_seen
        })

    # 6. NAT Gateways
    nat_rows = db.query(NatGateway).all()
    for n in nat_rows:
        inventory.append({
            "resource_type": "NAT",
            "resource_id": n.nat_gateway_id,
            "state": n.state,
            "region": n.region,
            "last_seen": n.last_seen
        })

    # 7. RDS Instances
    rds_rows = db.query(RDSInstance).all()
    for i in rds_rows:
        inventory.append({
            "resource_type": "RDS",
            "resource_id": i.db_instance_identifier,
            "state": i.db_instance_status,
            "engine": i.engine,
            "region": i.region,
            "last_seen": i.last_seen
        })

    # 8. RDS Snapshots
    rds_snap_rows = db.query(RDSSnapshot).all()
    for rs in rds_snap_rows:
        inventory.append({
            "resource_type": "RDS_SNAPSHOT",
            "resource_id": rs.db_snapshot_identifier,
            "db_instance": rs.db_instance_identifier,
            "region": rs.region,
            "last_seen": rs.last_seen
        })

    db.close()
    return inventory


# ==================================================
# WASTE API (MAIN DASHBOARD API)
# ==================================================

@router.get("/waste")
def get_waste():
    db = SessionLocal()
    rows = db.query(Waste).all()
    
    # Map resource types to their last scan time
    scan_logs = db.query(ScanLog).all()
    last_scanned = {log.resource_type: log.last_scanned_at for log in scan_logs}
    
    db.close()

    # These are the resource sections the UI should ALWAYS show
    KNOWN_RESOURCES = ["EC2", "EBS", "SNAPSHOT", "EIP", "LB", "NAT", "RDS", "RDS_SNAPSHOT"]

    # Human-readable labels for messages
    RESOURCE_LABELS = {
        "EC2": "stopped or underutilized EC2 instance",
        "EBS": "unattached EBS volume",
        "SNAPSHOT": "old snapshot",
        "EIP": "unattached Elastic IP",
        "LB": "unused load balancer",
        "NAT": "unused NAT Gateway",
        "RDS": "stopped RDS instance",
        "RDS_SNAPSHOT": "old RDS snapshot"
    }

    # Group waste by resource type
    waste_by_type = defaultdict(list)
    for w in rows:
        waste_by_type[w.resource_type].append(w)

    # Build summary dynamically
    summary = {}
    for r in KNOWN_RESOURCES:
        items = waste_by_type.get(r, [])
        
        # Determine scan status
        # RDS_SNAPSHOT depends on the RDS scan
        scan_key = "RDS" if r == "RDS_SNAPSHOT" else r
        scan_time = last_scanned.get(scan_key)
        is_scanned = scan_time is not None

        if items:
            label = RESOURCE_LABELS.get(r, f"{r} item")
            summary[r] = {
                "scanned": is_scanned,
                "last_scanned_at": scan_time,
                "waste_found": True,
                "count": len(items),
                "message": f"{len(items)} {label}(s) detected"
            }
        else:
            summary[r] = {
                "scanned": is_scanned,
                "last_scanned_at": scan_time,
                "waste_found": False,
                "count": 0,
                "message": f"No {RESOURCE_LABELS.get(r, r)}s found"
            }

    # Detailed waste list
    data = [
        {
            "resource_type": w.resource_type,
            "resource_id": w.resource_id,
            "resource_name": w.resource_name,
            "region": w.region,
            "reason": w.reason
        }
        for w in rows
    ]

    return {
        "status": "success",
        "summary": summary,
        "data": data
    }


# ==================================================
# SUMMARY API (EXECUTIVE VIEW)
# ==================================================

@router.get("/summary")
def get_summary():
    db = SessionLocal()

    total_cost = round(sum(c.amount for c in db.query(Cost).all()), 2)
    wasted_cost = round(
        sum(w.estimated_monthly_savings for w in db.query(Waste).all()),
        2
    )

    summary = {
        "total_monthly_cost": total_cost,
        "wasted_cost": wasted_cost,
        "potential_savings": wasted_cost,
        "waste_count": db.query(Waste).count(),
        "resource_count": db.query(Resource).count()
    }

    db.close()
    return summary

# ==================================================
# RULES CONFIGURATION API
# ==================================================

@router.get("/rules")
def get_rules():
    db = SessionLocal()
    rules = db.query(RuleConfig).all()
    db.close()
    return rules

@router.patch("/rules/{rule_id}")
def update_rule(rule_id: int, is_enabled: bool = Body(None), threshold_value: float = Body(None)):
    db = SessionLocal()
    rule = db.query(RuleConfig).filter(RuleConfig.id == rule_id).first()
    if not rule:
        db.close()
        raise HTTPException(status_code=404, detail="Rule not found")
    
    if is_enabled is not None:
        rule.is_enabled = is_enabled
    if threshold_value is not None:
        rule.threshold_value = threshold_value
    
    db.commit()
    db.refresh(rule)
    db.close()
    return rule

@router.post("/rules/reset")
def reset_rules():
    db = SessionLocal()
    db.query(RuleConfig).delete()
    
    defaults = [
        {"rule_name": "EC2_STOPPED_AGE", "threshold_value": 7.0, "description": "EC2 instance stopped for > X days"},
        {"rule_name": "EC2_IDLE_CPU", "threshold_value": 5.0, "description": "EC2 instance CPU < X% for 7 days"},
        {"rule_name": "EBS_UNATTACHED", "threshold_value": 0.0, "description": "EBS volume is not attached"},
        {"rule_name": "EBS_SNAPSHOT_AGE", "threshold_value": 30.0, "description": "EBS snapshot is older than X days"},
        {"rule_name": "EIP_UNASSOCIATED", "threshold_value": 0.0, "description": "Elastic IP is not associated"},
        {"rule_name": "LB_NO_TARGETS", "threshold_value": 0.0, "description": "Load Balancer has 0 registered targets"},
        {"rule_name": "LB_NO_TRAFFIC", "threshold_value": 0.0, "description": "Load Balancer has 0 requests for 7 days"},
        {"rule_name": "NAT_NO_ROUTE", "threshold_value": 0.0, "description": "NAT Gateway not in any route table"},
        {"rule_name": "NAT_NO_TRAFFIC", "threshold_value": 0.0, "description": "NAT Gateway has 0 traffic for 7 days"},
        {"rule_name": "RDS_STOPPED", "threshold_value": 0.0, "description": "RDS instance is stopped"},
        {"rule_name": "RDS_IDLE_CONN", "threshold_value": 0.0, "description": "RDS instance max connections = 0 for 7 days"},
        {"rule_name": "RDS_SNAPSHOT_AGE", "threshold_value": 30.0, "description": "RDS snapshot is older than X days"},
    ]
    
    for d in defaults:
        db.add(RuleConfig(
            rule_name=d["rule_name"],
            is_enabled=True,
            threshold_value=d["threshold_value"],
            description=d["description"]
        ))
    
    db.commit()
    db.close()
    return {"status": "success", "message": "Rules reset to defaults"}