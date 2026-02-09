# ==================================================
# PAGE 1 — AWS ACCESS & IDENTITY
# ==================================================

import boto3

ACCOUNT_ID = "664418997920"
ROLE_NAME = "CloudOptimizerRole"
ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/{ROLE_NAME}"

def assume_role():
    """
    Assumes the customer's AWS role and returns temporary credentials.
    This is the ONLY place where STS is used.
    """
    sts = boto3.client("sts")
    response = sts.assume_role(
        RoleArn=ROLE_ARN,
        RoleSessionName="cloud-optimizer"
    )
    return response["Credentials"]

def get_all_regions():
    """
    Returns all AWS regions available to the account.
    This enables global scanning.
    """
    creds = assume_role()

    ec2 = boto3.client(
        "ec2",
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name="us-east-1"
    )

    return [r["RegionName"] for r in ec2.describe_regions()["Regions"]]
