# ==================================================
# PAGE 2 — AWS SCANNERS
# ==================================================
import boto3
from aws_auth import assume_role, get_all_regions

def scan_ec2_all_regions():
    """
    Fetches EC2 instances from ALL AWS regions.
    Returns: List of (region, describe_instances response)
    """
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

        response = ec2.describe_instances()
        results.append((region, response))

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
            region_name=region
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
            region_name=region
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
            region_name=region
        )

        response = ec2.describe_addresses()
        all_data.append((region, response))

    return all_data

def scan_load_balancers_all_regions():
    creds = assume_role()
    all_lbs = []

    for region in get_all_regions():
        elb = boto3.client(
            "elbv2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region
        )

        lbs = elb.describe_load_balancers()["LoadBalancers"]

        for lb in lbs:
            tgs = elb.describe_target_groups(
                LoadBalancerArn=lb["LoadBalancerArn"]
            )["TargetGroups"]

            target_count = 0
            for tg in tgs:
                health = elb.describe_target_health(
                    TargetGroupArn=tg["TargetGroupArn"]
                )
                target_count += len(health["TargetHealthDescriptions"])

            all_lbs.append({
                "arn": lb["LoadBalancerArn"],
                "name": lb["LoadBalancerName"],
                "type": lb["Type"],
                "region": region,
                "target_count": target_count
            })

    return all_lbs

def scan_nat_gateways_all_regions():
    creds = assume_role()
    all_nats = []

    for region in get_all_regions():
        ec2 = boto3.client(
            "ec2",
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
            region_name=region
        )

        paginator = ec2.get_paginator("describe_nat_gateways")

        for page in paginator.paginate():
            nat_gateways = page.get("NatGateways", [])

            for nat in nat_gateways:
                all_nats.append({
                    "nat_gateway_id": nat["NatGatewayId"],
                    "state": nat["State"],
                    "vpc_id": nat["VpcId"],
                    "subnet_id": nat["SubnetId"],
                    "region": region
                })

    return all_nats


