# ==================================================
# PAGE 2 — AWS SCANNERS
# ==================================================
import boto3
import datetime
from datetime import timedelta
from botocore.config import Config
from aws_auth import assume_role, get_all_regions

RETRY_CONFIG = Config(retries={'max_attempts': 3, 'mode': 'standard'})

def scan_ec2_all_regions():
    """
    Fetches EC2 instances from ALL AWS regions.
    Returns: List of (region, list of instance data with CPU metrics)
    """
    creds = assume_role()
    results = []
    now = datetime.datetime.utcnow()
    start_time = now - timedelta(days=7)

    for region in get_all_regions():
        try:
            ec2 = boto3.client(
                "ec2",
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
                region_name=region,
                config=RETRY_CONFIG
            )
            
            cw = boto3.client(
                "cloudwatch",
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
                region_name=region,
                config=RETRY_CONFIG
            )

            response = ec2.describe_instances()
            region_instances = []
            
            for reservation in response["Reservations"]:
                for instance in reservation["Instances"]:
                    instance_id = instance["InstanceId"]
                    
                    # Fetch CloudWatch metrics
                    metrics = cw.get_metric_statistics(
                        Namespace='AWS/EC2',
                        MetricName='CPUUtilization',
                        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                        StartTime=start_time,
                        EndTime=now,
                        Period=3600,
                        Statistics=['Average']
                    )
                    
                    datapoints = metrics.get('Datapoints', [])
                    if datapoints:
                        avg_cpu = sum(d['Average'] for d in datapoints) / len(datapoints)
                    else:
                        avg_cpu = 0.0

                    # Prepare instance data
                    instance_data = {
                        "InstanceId": instance_id,
                        "InstanceType": instance["InstanceType"],
                        "State": instance["State"],
                        "LaunchTime": instance["LaunchTime"],
                        "Tags": instance.get("Tags", []),
                        "avg_cpu": avg_cpu
                    }
                    region_instances.append(instance_data)

            results.append((region, {"Reservations": [{"Instances": region_instances}]}))
        except Exception as e:
            print(f"Error scanning EC2 in {region}: {e}")
            continue

    return results

def scan_ebs_all_regions():
    """
    Fetches EBS volumes from ALL AWS regions.
    """
    creds = assume_role()
    results = []

    for region in get_all_regions():
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
            config=RETRY_CONFIG
        )

        response = ec2.describe_volumes()
        results.append((region, response))

    return results

def scan_snapshots_all_regions():
    """
    Fetches snapshots owned by the account from ALL regions.
    """
    creds = assume_role()
    results = []

    for region in get_all_regions():
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
            config=RETRY_CONFIG
        )

        response = ec2.describe_snapshots(OwnerIds=["self"])
        results.append((region, response))

    return results

def scan_eip_all_regions():
    creds = assume_role()
    all_data = []

    for region in get_all_regions():
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
            config=RETRY_CONFIG
        )

        response = ec2.describe_addresses()
        all_data.append((region, response))

    return all_data

def scan_load_balancers_all_regions():
    creds = assume_role()
    all_lbs = []
    now = datetime.datetime.utcnow()
    start_time = now - timedelta(days=7)

    for region in get_all_regions():
        elb = boto3.client(
            "elbv2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
            config=RETRY_CONFIG
        )

        cw = boto3.client(
            "cloudwatch",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
            config=RETRY_CONFIG
        )

        lbs = elb.describe_load_balancers()["LoadBalancers"]

        for lb in lbs:
            lb_arn = lb["LoadBalancerArn"]
            tgs = elb.describe_target_groups(
                LoadBalancerArn=lb_arn
            )["TargetGroups"]

            target_count = 0
            for tg in tgs:
                health = elb.describe_target_health(
                    TargetGroupArn=tg["TargetGroupArn"]
                )
                target_count += len(health["TargetHealthDescriptions"])

            # Traffic detection via CloudWatch RequestCount
            # Dimensional mapping for LB metrics
            parts = lb_arn.split('/')
            lb_id = f"app/{parts[-2]}/{parts[-1]}"
            
            metrics = cw.get_metric_statistics(
                Namespace='AWS/ApplicationELB',
                MetricName='RequestCount',
                Dimensions=[{'Name': 'LoadBalancer', 'Value': lb_id}],
                StartTime=start_time,
                EndTime=now,
                Period=86400 * 7,
                Statistics=['Sum']
            )

            datapoints = metrics.get('Datapoints', [])
            total_requests = sum(d['Sum'] for d in datapoints) if datapoints else 0

            all_lbs.append({
                "arn": lb_arn,
                "name": lb["LoadBalancerName"],
                "type": lb["Type"],
                "region": region,
                "target_count": target_count,
                "request_count": total_requests
            })

    return all_lbs

def scan_nat_gateways_all_regions():
    creds = assume_role()
    all_nats = []
    now = datetime.datetime.utcnow()
    start_time = now - timedelta(days=7)

    for region in get_all_regions():
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
            config=RETRY_CONFIG
        )
        
        cw = boto3.client(
            "cloudwatch",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
            config=RETRY_CONFIG
        )

        # Get Route Tables to check for attachments
        route_tables = ec2.describe_route_tables()["RouteTables"]

        paginator = ec2.get_paginator("describe_nat_gateways")

        for page in paginator.paginate():
            nat_gateways = page.get("NatGateways", [])

            for nat in nat_gateways:
                nat_id = nat["NatGatewayId"]
                
                # Calculate Route Table attachments
                attached_count = 0
                for rt in route_tables:
                    for route in rt.get("Routes", []):
                        if route.get("NatGatewayId") == nat_id:
                            attached_count += 1
                            break

                # Traffic detection via CloudWatch
                total_bytes = 0
                for metric in ['BytesInFromSource', 'BytesOutFromSource']:
                    m_data = cw.get_metric_statistics(
                        Namespace='AWS/NATGateway',
                        MetricName=metric,
                        Dimensions=[{'Name': 'NatGatewayId', 'Value': nat_id}],
                        StartTime=start_time,
                        EndTime=now,
                        Period=86400 * 7,
                        Statistics=['Sum']
                    )
                    datapoints = m_data.get('Datapoints', [])
                    total_bytes += sum(d['Sum'] for d in datapoints) if datapoints else 0
                
                total_traffic_gb = total_bytes / (1024 ** 3)

                all_nats.append({
                    "nat_gateway_id": nat_id,
                    "state": nat["State"],
                    "vpc_id": nat["VpcId"],
                    "subnet_id": nat["SubnetId"],
                    "region": region,
                    "attached_route_tables": attached_count,
                    "total_traffic_gb": total_traffic_gb
                })

    return all_nats

def scan_rds_instances_all_regions():
    """
    Fetches RDS instances from ALL AWS regions.
    """
    creds = assume_role()
    all_rds = []
    now = datetime.datetime.utcnow()
    start_time = now - timedelta(days=7)

    for region in get_all_regions():
        try:
            rds = boto3.client(
                "rds",
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
                region_name=region,
                config=RETRY_CONFIG
            )
            
            cw = boto3.client(
                "cloudwatch",
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
                region_name=region,
                config=RETRY_CONFIG
            )

            instances = rds.describe_db_instances()["DBInstances"]

            for ins in instances:
                db_id = ins["DBInstanceIdentifier"]
                
                # Database Connections detection via CloudWatch
                metrics = cw.get_metric_statistics(
                    Namespace='AWS/RDS',
                    MetricName='DatabaseConnections',
                    Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
                    StartTime=start_time,
                    EndTime=now,
                    Period=86400 * 7,
                    Statistics=['Maximum']
                )
                
                datapoints = metrics.get('Datapoints', [])
                max_connections = max(d['Maximum'] for d in datapoints) if datapoints else 0

                all_rds.append({
                    "db_instance_identifier": db_id,
                    "db_instance_status": ins["DBInstanceStatus"],
                    "db_instance_class": ins["DBInstanceClass"],
                    "engine": ins["Engine"],
                    "region": region,
                    "max_connections": max_connections
                })
        except Exception as e:
            print(f"Error scanning RDS in {region}: {e}")
            continue

    return all_rds

def scan_rds_snapshots_all_regions():
    """
    Fetches manual RDS snapshots from ALL regions.
    """
    creds = assume_role()
    all_snaps = []

    for region in get_all_regions():
        rds = boto3.client(
            "rds",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region,
            config=RETRY_CONFIG
        )

        snaps = rds.describe_db_snapshots(SnapshotType="manual")["DBSnapshots"]

        for snap in snaps:
            all_snaps.append({
                "db_snapshot_identifier": snap["DBSnapshotIdentifier"],
                "db_instance_identifier": snap.get("DBInstanceIdentifier"),
                "snapshot_create_time": str(snap.get("SnapshotCreateTime")),
                "region": region
            })

    return all_snaps