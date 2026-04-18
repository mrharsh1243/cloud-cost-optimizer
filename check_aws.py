import boto3
from aws_auth import assume_role, ROLE_ARN

def check_aws_connectivity():
    print("--- Testing AWS Connectivity ---")
    
    # 1. Test Base Connection
    try:
        sts = boto3.client('sts')
        identity = sts.get_caller_identity()
        print(f"STEP 1: Base connection successful.")
        print(f"Logged in as: {identity['Arn']}")
    except Exception as e:
        print(f"STEP 1 FAILED: Could not connect to AWS. Error: {str(e)}")
        return

    # 2. Test Role Assumption
    print(f"\n--- Testing Role Assumption to: {ROLE_ARN} ---")
    try:
        creds = assume_role()
        
        # Test the assumed credentials by calling STS again
        assumed_sts = boto3.client(
            'sts',
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken']
        )
        assumed_identity = assumed_sts.get_caller_identity()
        
        print(f"STEP 2: Role assumption successful.")
        print(f"Assumed Role Identity: {assumed_identity['Arn']}")
        print("\n✅ SUCCESS: Connected to AWS and assumed the role!")
        
    except Exception as e:
        print(f"STEP 2 FAILED: Could not assume the role '{ROLE_ARN}'.")
        print(f"Error Message: {str(e)}")
        print("\n❌ Please verify that your local credentials have 'sts:AssumeRole' permissions for this ARN.")

if __name__ == "__main__":
    check_aws_connectivity()