import os

from dotenv import load_dotenv
from minio import Minio

load_dotenv()

client = Minio(
    os.getenv("MINIO_ENDPOINT"),
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=False,
)

bucket_name = os.getenv("MINIO_BUCKET")
file_path = "data/raw/youtube_trending_raw.json"
object_name = "raw/youtube_trending_raw.json"

if not client.bucket_exists(bucket_name):
    client.make_bucket(bucket_name)

client.fput_object(bucket_name, object_name, file_path)

print("Upload completed")
print("Bucket:", bucket_name)
print('Object:', object_name)
