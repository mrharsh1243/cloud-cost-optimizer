from fastapi import APIRouter
from collections import defaultdict
from db import SessionLocal, Waste, Resource, Cost

router = APIRouter()

# ==================================================
# RESOURCES API
# ==================================================

@router.get("/resources")
def get_resources():
    db = SessionLocal()
    rows = db.query(Resource).all()
    db.close()

    return [
        {
            "instance_id": r.instance_id,
            "instance_name": r.instance_name,
            "instance_type": r.instance_type,
            "state": r.state,
            "region": r.region,
            "last_seen": r.last_seen
        }
        for r in rows
    ]


# ==================================================
# WASTE API (MAIN DASHBOARD API)
# ==================================================

@router.get("/waste")
def get_waste():
    db = SessionLocal()
    rows = db.query(Waste).all()
    db.close()

    # These are the resource sections the UI should ALWAYS show
    KNOWN_RESOURCES = ["EC2", "EBS", "SNAPSHOT", "EIP","LB"]

    # Human-readable labels for messages
    RESOURCE_LABELS = {
        "EC2": "stopped EC2 instance",
        "EBS": "unattached EBS volume",
        "SNAPSHOT": "old snapshot",
        "EIP": "unattached Elastic IP",
        "LB": "unused load balancer"
    }

    # Group waste by resource type
    waste_by_type = defaultdict(list)
    for w in rows:
        waste_by_type[w.resource_type].append(w)

    # Build summary dynamically
    summary = {}
    for r in KNOWN_RESOURCES:
        items = waste_by_type.get(r, [])

        if items:
            label = RESOURCE_LABELS.get(r, f"{r} item")
            summary[r] = {
                "scanned": True,
                "waste_found": True,
                "count": len(items),
                "message": f"{len(items)} {label}(s) detected"
            }
        else:
            summary[r] = {
                "scanned": True,
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