from db import SessionLocal, RuleConfig

DEFAULT_RULES = [
    {
        "rule_name": "EC2_STOPPED_AGE", 
        "threshold_value": 7.0, 
        "description": "Flag EC2 instances stopped for more than X days"
    },
    {
        "rule_name": "EC2_IDLE_CPU", 
        "threshold_value": 5.0, 
        "description": "Flag EC2 instances with average CPU < X% for 7 days"
    },
    {
        "rule_name": "EBS_UNATTACHED", 
        "threshold_value": 0.0, 
        "description": "Flag EBS volumes not attached to any instance"
    },
    {
        "rule_name": "EBS_SNAPSHOT_AGE", 
        "threshold_value": 30.0, 
        "description": "Flag EBS snapshots older than X days"
    },
    {
        "rule_name": "EIP_UNASSOCIATED", 
        "threshold_value": 0.0, 
        "description": "Flag Elastic IPs not associated with any instance"
    },
    {
        "rule_name": "LB_NO_TARGETS", 
        "threshold_value": 0.0, 
        "description": "Flag Load Balancers with 0 registered targets"
    },
    {
        "rule_name": "LB_NO_TRAFFIC", 
        "threshold_value": 0.0, 
        "description": "Flag Load Balancers with 0 requests for 7 days"
    },
    {
        "rule_name": "NAT_NO_ROUTE", 
        "threshold_value": 0.0, 
        "description": "Flag NAT Gateways not attached to any route table"
    },
    {
        "rule_name": "NAT_NO_TRAFFIC", 
        "threshold_value": 0.0, 
        "description": "Flag NAT Gateways with 0 traffic for 7 days"
    },
    {
        "rule_name": "RDS_STOPPED", 
        "threshold_value": 0.0, 
        "description": "Flag RDS instances that are stopped"
    },
    {
        "rule_name": "RDS_IDLE_CONN", 
        "threshold_value": 0.0, 
        "description": "Flag RDS instances with 0 connections for 7 days"
    },
    {
        "rule_name": "RDS_SNAPSHOT_AGE", 
        "threshold_value": 30.0, 
        "description": "Flag RDS snapshots older than X days"
    }
]

def init_rules():
    db = SessionLocal()
    try:
        # Check if RuleConfig table is empty
        if db.query(RuleConfig).first() is None:
            print("Initializing default rules...")
            for rule in DEFAULT_RULES:
                new_rule = RuleConfig(
                    rule_name=rule["rule_name"],
                    is_enabled=True,
                    threshold_value=rule["threshold_value"],
                    description=rule["description"]
                )
                db.add(new_rule)
            db.commit()
            print("Rules initialized successfully!")
        else:
            print("Rules already exist in the database.")
    except Exception as e:
        print(f"Error initializing rules: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_rules()