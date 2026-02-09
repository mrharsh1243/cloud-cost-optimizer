from fastapi import APIRouter
from datetime import datetime
from waste_engine import run_waste_scan
from db import ElasticIP
from aws_scanners import scan_eip_all_regions

from db import SessionLocal, Resource, EBSVolume, Snapshot, Cost
from aws_scanners import (
    scan_ec2_all_regions,
    scan_ebs_all_regions,
    scan_snapshots_all_regions
)

router = APIRouter()

@router.post("/scan")
def scan_ec2():
    db = SessionLocal()
    db.query(Resource).delete()

    results = scan_ec2_all_regions()

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
                        last_seen=str(datetime.utcnow())
                    )
                )

    db.commit()
    db.close()
    return {"status": "EC2 scanned and stored"}

@router.post("/scan-ebs")
def scan_ebs():
    db = SessionLocal()
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

    db.commit()
    db.close()
    return {"status": "EBS scanned and stored"}

@router.post("/scan-snapshots")
def scan_snapshots():
    db = SessionLocal()
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

    db.commit()
    db.close()
    return {"status": "Snapshots scanned and stored"}

@router.post("/scan-eip")
def scan_eip():
    db = SessionLocal()
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

    db.commit()
    db.close()
    return {"status": "Elastic IPs scanned and stored"}

@router.post("/scan-lb")
def scan_load_balancers():
    from db import LoadBalancer
    from aws_scanners import scan_load_balancers_all_regions

    db = SessionLocal()
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
                last_seen=str(datetime.utcnow())
            )
        )

    db.commit()
    db.close()

    return {"status": "Load balancers scanned and stored"}

@router.post("/scan-waste")
def scan_waste():
    run_waste_scan()
    return {
        "status": "success",
        "message": "Waste scan completed"
    }