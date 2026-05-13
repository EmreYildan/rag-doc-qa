import os
import boto3
from dotenv import load_dotenv
from datetime import datetime


load_dotenv()


def upload_file_to_s3(local_file_path: str, original_filename: str) -> dict:
    """
    PDF dosyasını AWS S3'e yükler.
    """
    try:
        bucket_name = os.getenv("AWS_S3_BUCKET_NAME")
        region = os.getenv("AWS_REGION", "eu-west-1")

        if not bucket_name:
            raise ValueError("AWS_S3_BUCKET_NAME .env dosyasında tanımlı değil.")

        s3_client = boto3.client("s3", region_name=region)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = original_filename.replace(" ", "_")
        s3_key = f"documents/{timestamp}_{safe_filename}"

        s3_client.upload_file(
            local_file_path,
            bucket_name,
            s3_key
        )

        return {
            "success": True,
            "bucket": bucket_name,
            "key": s3_key,
            "s3_uri": f"s3://{bucket_name}/{s3_key}"
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }