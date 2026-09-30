import os

from dotenv import load_dotenv
from minio import Minio


load_dotenv()


def get_minio_client():
    endpoint = os.getenv("MINIO_ENDPOINT")
    access_key = os.getenv("MINIO_ACCESS_KEY")
    secret_key = os.getenv("MINIO_SECRET_KEY")

    if not endpoint or not access_key or not secret_key:
        raise ValueError(
            "MinIO configuration is missing. Check your .env file."
        )

    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=False,
    )


def upload_file_to_minio(file_path, object_name):
    client = get_minio_client()

    bucket_name = os.getenv("MINIO_BUCKET")

    if not bucket_name:
        raise ValueError(
            "MINIO_BUCKET was not found in .env"
        )

    if not client.bucket_exists(bucket_name):
        client.make_bucket(bucket_name)

    client.fput_object(
        bucket_name,
        object_name,
        str(file_path),
    )

    print("MinIO upload completed")
    print("Bucket:", bucket_name)
    print("Object:", object_name)


if __name__ == "__main__":
    file_path = "data/raw/youtube_trending_raw.json"
    object_name = "raw/youtube_trending_raw.json"

    upload_file_to_minio(
        file_path,
        object_name,
    )