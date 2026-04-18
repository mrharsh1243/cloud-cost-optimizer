from fastapi import APIRouter
from datetime import datetime
from waste_engine import run_waste_scan
from db import ElasticIP
from aws_scanners import scan_eip_all_regions

from db import SessionLocal, Resource, EBSVolume, Snapshot, Cost, RDSInstance, RDSSnapshot, ScanLog
from aws_scanners import (
    scan_ec2_all_regions,
    scan_ebs_all_regions,
    scan_snapshots_all_regions,
    scan_rds_instances_all_regions,
    scan_rds_snapshots_all_regions
)

router = APIRouter()

def record_scan(db, resource_type, status="completed", error_msg=None):
    scan_log = db.query(ScanLog).filter(ScanLog.resource_type == resource_type).first()
    now = str(datetime.utcnow())
    if scan_log:
        scan_log.last_scanned_at = now
        scan_log.status = status
        scan_log.error_message = error_msg
    else:
        db.add(ScanLog(resource_type=resource_type, last_scanned_at=now, status=status, error_message=error_msg))

@router.post("/scan")
def scan_ec2():
    db = SessionLocal()
    count = 0
    try:
        db.query(Resource).delete()

        results = scan_ec2_all_regions()

        if not results:
            record_scan(db, "EC2", status="failed", error_msg="No regions returned from AWS")
            db.commit()
            return {"status": "error", "message": "No data returned from AWS scanners"}

        for region, data in results:
            for reservation in data["Reservations"]:
                for instance in reservation["Instances"]:
                    name = "Unnamed"
                    for tag in instance.get("Tags", []):
                        if tag["Key"] == "Name":
                            name = tag["Value"]

                    db.add(
                        Resource(
                            instance_id=instance["InstanceId"],
                            instance_name=name,
                            instance_type=instance["InstanceType"],
                            state=instance["State"]["Name"],
                            launch_time=str(instance["LaunchTime"]),
                            region=region,
                            avg_cpu=instance.get("avg_cpu", 0.0),
                            last_seen=str(datetime.utcnow())
                        )
                    )
                    count += 1

        record_scan(db, "EC2")
        db.commit()
    except Exception as e:
        db.rollback()
        record_scan(db, "EC2", status="failed", error_msg=str(e))
        db.commit()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
    return {"status": "success", "count": count, "message": "EC2 scanned and stored"}

@router.post("/scan-ebs")
def scan_ebs():
    db = SessionLocal()
    count = 0
    try:
        db.query(EBSVolume).delete()
        results = scan_ebs_all_regions()

        for region, data in results:
            for vol in data["Volumes"]:
                attached = vol["Attachments"][0]["InstanceId"] if vol["Attachments"] else None
                db.add(
                    EBSVolume(
                        volume_id=vol["VolumeId"],
                        size_gb=vol["Size"],
                        state=vol["State"],
                        attached_instance=attached,
                        region=region,
                        last_seen=str(datetime.utcnow())
                    )
                )
                count += 1

        record_scan(db, "EBS")
        db.commit()
    except Exception as e:
        db.rollback()
        record_scan(db, "EBS", status="failed", error_msg=str(e))
        db.commit()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
    return {"status": "success", "count": count, "message": "EBS scanned and stored"}

@router.post("/scan-snapshots")
def scan_snapshots():
    db = SessionLocal()
    count = 0
    try:
        db.query(Snapshot).delete()
        results = scan_snapshots_all_regions()

        for region, data in results:
            for snap in data["Snapshots"]:
                db.add(
                    Snapshot(
                        snapshot_id=snap["SnapshotId"],
                        volume_id=snap.get("VolumeId"),
                        start_time=str(snap["StartTime"]),
                        region=region,
                        last_seen=str(datetime.utcnow())
                    )
                )
                count += 1

        record_scan(db, "SNAPSHOT")
        db.commit()
    except Exception as e:
        db.rollback()
        record_scan(db, "SNAPSHOT", status="failed", error_msg=str(e))
        db.commit()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
    return {"status": "success", "count": count, "message": "Snapshots scanned and stored"}

@router.post("/scan-eip")
def scan_eip():
    db = SessionLocal()
    count = 0
    try:
        db.query(ElasticIP).delete()
        results = scan_eip_all_regions()

        for region, data in results:
            for eip in data.get("Addresses", []):
                db.add(
                    ElasticIP(
                        allocation_id=eip.get("AllocationId"),
                        public_ip=eip.get("PublicIp"),
                        associated_instance=eip.get("InstanceId"),
                        region=region,
                        last_seen=str(datetime.utcnow())
                    )
                )
                count += 1

        record_scan(db, "EIP")
        db.commit()
    except Exception as e:
        db.rollback()
        record_scan(db, "EIP", status="failed", error_msg=str(e))
        db.commit()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
    return {"status": "success", "count": count, "message": "Elastic IPs scanned and stored"}

@router.post("/scan-lb")
def scan_load_balancers():
    from db import LoadBalancer
    from aws_scanners import scan_load_balancers_all_regions

    db = SessionLocal()
    count = 0
    try:
        db.query(LoadBalancer).delete()
        lbs = scan_load_balancers_all_regions()

        for lb in lbs:
            db.add(
                LoadBalancer(
                    lb_arn=lb["arn"],
                    lb_name=lb["name"],
                    lb_type=lb["type"],
                    region=lb["region"],
                    target_count=lb["target_count"],
                    request_count=lb.get("request_count", 0),
                    last_seen=str(datetime.utcnow())
                )
            )
            count += 1

        record_scan(db, "LB")
        db.commit()
    except Exception as e:
        db.rollback()
        record_scan(db, "LB", status="failed", error_msg=str(e))
        db.commit()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
    return {"status": "success", "count": count, "message": "Load balancers scanned and stored"}

@router.post("/scan-nat")
def scan_nat_gateways():
    from db import NatGateway
    from aws_scanners import scan_nat_gateways_all_regions

    db = SessionLocal()
    count = 0
    try:
        db.query(NatGateway).delete()
        nats = scan_nat_gateways_all_regions()

        for nat in nats:
            db.add(
                NatGateway(
                    nat_gateway_id=nat["nat_gateway_id"],
                    subnet_id=nat["subnet_id"],
                    vpc_id=nat["vpc_id"],
                    state=nat["state"],
                    region=nat["region"],
                    attached_route_tables=nat["attached_route_tables"],
                    total_traffic_gb=nat.get("total_traffic_gb", 0.0),
                    last_seen=str(datetime.utcnow())
                )
            )
            count += 1

        record_scan(db, "NAT")
        db.commit()
    except Exception as e:
        db.rollback()
        record_scan(db, "NAT", status="failed", error_msg=str(e))
        db.commit()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
    return {"status": "success", "count": count, "message": "NAT gateways scanned and stored"}

@router.post("/scan-rds")
def scan_rds():
    db = SessionLocal()
    count_inst = 0
    count_snap = 0
    try:
        db.query(RDSInstance).delete()
        db.query(RDSSnapshot).delete()

        instances = scan_rds_instances_all_regions()
        for inst in instances:
            db.add(
                RDSInstance(
                    db_instance_identifier=inst["db_instance_identifier"],
                    db_instance_status=inst["db_instance_status"],
                    db_instance_class=inst["db_instance_class"],
                    engine=inst["engine"],
                    region=inst["region"],
                    max_connections=inst.get("max_connections", 0),
                    last_seen=str(datetime.utcnow())
                )
            )
            count_inst += 1

        snapshots = scan_rds_snapshots_all_regions()
        for snap in snapshots:
            db.add(
                RDSSnapshot(
                    db_snapshot_identifier=snap["db_snapshot_identifier"],
                    db_instance_identifier=snap["db_instance_identifier"],
                    snapshot_create_time=snap["snapshot_create_time"],
                    region=snap["region"],
                    last_seen=str(datetime.utcnow())
                )
            )
            count_snap += 1

        record_scan(db, "RDS")
        db.commit()
    except Exception as e:
        db.rollback()
        record_scan(db, "RDS", status="failed", error_msg=str(e))
        db.commit()
        return {"status": "error", "message": str(e)}
    finally:
        db.close()
    return {"status": "success", "instances_count": count_inst, "snapshots_count": count_snap, "message": "RDS instances and snapshots scanned and stored"}

@router.post("/scan-waste")
def scan_waste():
    run_waste_scan()
    return {
        "status": "success",
        "message": "Waste scan completed"
    }

@router.post("/scan-all")
def scan_all():
    try:
        scan_ec2()
        scan_ebs()
        scan_snapshots()
        scan_eip()
        scan_load_balancers()
        scan_nat_gateways()
        scan_rds()
        run_waste_scan()
        return {
            "status": "success",
            "message": "Full infrastructure sync and waste analysis complete"
        }
    except Exception as e:
        return {"status": "error", "message": f"Global scan failed: {str(e)}"}