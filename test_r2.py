import os
import boto3
from dotenv import load_dotenv

load_dotenv()

account_id = os.getenv("R2_ACCOUNT_ID")
access_key = os.getenv("R2_ACCESS_KEY_ID")
secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
bucket = os.getenv("R2_BUCKET_NAME")
endpoint = os.getenv("R2_ENDPOINT_URL")

print("Testing R2 connection...")
print(f"Bucket: {bucket}")
print(f"Endpoint: {endpoint}")

s3 = boto3.client(
    "s3",
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    region_name="auto"
)

try:
    response = s3.list_objects_v2(
        Bucket=bucket,
        MaxKeys=5
    )

    print("R2 CONNECTION SUCCESSFUL")
    print(f"Objects found: {response.get('KeyCount', 0)}")

    for obj in response.get("Contents", []):
        print(f" - {obj['Key']}")

except Exception as e:
    print("R2 CONNECTION FAILED")
    print(type(e).__name__)
    print(str(e))