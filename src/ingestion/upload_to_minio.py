"""
Đồng bộ thư mục data/ lên MinIO (thay thế 4 script upload riêng lẻ).

Ánh xạ đường dẫn:
    data/raw/...        ->  raw/...
    data/processed/...  ->  processed/...

Chạy:
    uv run python src/ingestion/upload_to_minio.py
    uv run python src/ingestion/upload_to_minio.py --only raw
    uv run python src/ingestion/upload_to_minio.py --only processed
    uv run python src/ingestion/upload_to_minio.py --force      # upload lại tất cả
    uv run python src/ingestion/upload_to_minio.py --dry-run    # chỉ xem, không upload
"""
import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio
from minio.error import S3Error

# ---------------------------------------------------------------
# 1. Cấu hình
# ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent   # gốc project
DATA_DIR = BASE_DIR / "data"
ENV_PATH = BASE_DIR / ".env"

CONTENT_TYPES = {
    ".json": "application/json",
    ".csv": "text/csv",
    ".txt": "text/plain",
}

if not ENV_PATH.exists():
    sys.exit(f"[LỖI] Không tìm thấy file .env tại: {ENV_PATH}")
load_dotenv(ENV_PATH)

ENDPOINT = os.getenv("MINIO_ENDPOINT")
ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
SECRET_KEY = os.getenv("MINIO_SECRET_KEY")
BUCKET = os.getenv("MINIO_BUCKET")

missing = [
    k for k, v in {
        "MINIO_ENDPOINT": ENDPOINT,
        "MINIO_ACCESS_KEY": ACCESS_KEY,
        "MINIO_SECRET_KEY": SECRET_KEY,
        "MINIO_BUCKET": BUCKET,
    }.items() if not v
]
if missing:
    sys.exit(f"[LỖI] Thiếu biến trong .env: {', '.join(missing)}")

client = Minio(ENDPOINT, access_key=ACCESS_KEY, secret_key=SECRET_KEY, secure=False)


# ---------------------------------------------------------------
# 2. Hàm hỗ trợ
# ---------------------------------------------------------------
def needs_upload(object_name: str, local_file: Path) -> bool:
    """True nếu object chưa có hoặc khác kích thước (file local đã thay đổi)."""
    try:
        stat = client.stat_object(BUCKET, object_name)
        return stat.size != local_file.stat().st_size
    except S3Error as e:
        if e.code in ("NoSuchKey", "NoSuchObject"):
            return True
        raise


def collect_files(only: str | None) -> list[Path]:
    root = DATA_DIR / only if only else DATA_DIR
    if not root.exists():
        sys.exit(f"[LỖI] Thư mục không tồn tại: {root}")
    return sorted(
        f for f in root.rglob("*")
        if f.is_file() and f.suffix.lower() in CONTENT_TYPES
    )


def sync(only: str | None, force: bool, dry_run: bool) -> None:
    print(f"Project root : {BASE_DIR}")
    print(f"Endpoint     : {ENDPOINT} | Bucket: {BUCKET}")
    print(f"Nguồn        : {DATA_DIR / only if only else DATA_DIR}")

    if not client.bucket_exists(BUCKET):
        if dry_run:
            print(f"(dry-run) Bucket '{BUCKET}' chưa có, sẽ được tạo")
        else:
            client.make_bucket(BUCKET)
            print(f"Đã tạo bucket: {BUCKET}")

    files = collect_files(only)
    print(f"Tìm thấy {len(files)} file\n")

    uploaded = skipped = failed = 0
    for f in files:
        object_name = f.relative_to(DATA_DIR).as_posix()   # raw/... hoặc processed/...
        try:
            if not force and not needs_upload(object_name, f):
                skipped += 1
                continue
            if dry_run:
                print(f"[DRY]  {object_name}")
            else:
                client.fput_object(
                    BUCKET, object_name, str(f),
                    content_type=CONTENT_TYPES[f.suffix.lower()],
                )
                print(f"[OK]   {object_name}")
            uploaded += 1
        except Exception as e:
            failed += 1
            print(f"[FAIL] {object_name} -> {e}")

    print(f"\nHoàn tất: {uploaded} upload | {skipped} bỏ qua | {failed} lỗi")


# ---------------------------------------------------------------
# 3. CLI
# ---------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Đồng bộ data/ lên MinIO")
    parser.add_argument("--only", choices=["raw", "processed"],
                        help="chỉ đồng bộ một thư mục con")
    parser.add_argument("--force", action="store_true",
                        help="upload lại cả file đã có")
    parser.add_argument("--dry-run", action="store_true",
                        help="chỉ liệt kê, không upload")
    args = parser.parse_args()

    try:
        sync(args.only, args.force, args.dry_run)
    except S3Error as e:
        sys.exit(f"[LỖI MinIO] {e.code}: {e.message}")
    except Exception as e:
        sys.exit(f"[LỖI] {e}")