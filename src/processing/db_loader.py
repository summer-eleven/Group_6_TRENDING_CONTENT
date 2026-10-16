from __future__ import annotations
 
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable
from dotenv import load_dotenv
load_dotenv()
import pyodbc
 
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("db_loader")
 
# Cac cot duoc phep ghi vao bang youtube_videos (khop docker/db/schema.sql).
ALLOWED_COLUMNS = [
    "video_id",
    "title",
    "channel_id",
    "channel_title",
    "category_id",
    "published_at",
    "region_code",
    "view_count",
    "like_count",
    "comment_count",
    "is_trending",
    "trending_rank",
    "raw_object_path",
    "collected_at",
]
 
# Cac cot co gia tri datetime can duoc parse tu chuoi ISO 8601 (crawler luu
# published_at / collected_at dang string, vd "2026-09-27T10:00:00+00:00").
DATETIME_COLUMNS = {"published_at", "collected_at"}
 
 
@dataclass
class LoadResult:
    inserted_or_updated: int = 0
    failed: list[dict[str, Any]] = field(default_factory=list)
 
    def as_dict(self) -> dict[str, Any]:
        return {
            "inserted_or_updated": self.inserted_or_updated,
            "failed_count": len(self.failed),
            "failed": self.failed,
        }
 
 
class DBLoader:
    """Ket noi SQL Server va load record vao bang youtube_videos."""
 
    def __init__(self) -> None:
        self._host = os.environ.get("MSSQL_HOST", "localhost")
        self._port = os.environ.get("MSSQL_PORT", "1433")
        self._db = os.environ.get("MSSQL_DB", "youtube_trending")
        self._user = os.environ.get("MSSQL_USER", "sa")
        self._password = os.environ.get("MSSQL_PASSWORD", "YourStrong@Passw0rd")
 
    def _connect(self) -> pyodbc.Connection:
        conn_str = (
            "DRIVER={ODBC Driver 18 for SQL Server};"
            f"SERVER={self._host},{self._port};"
            f"DATABASE={self._db};"
            f"UID={self._user};PWD={self._password};"
            "TrustServerCertificate=yes;"
        )
        return pyodbc.connect(conn_str)
 
    @staticmethod
    def _clean_record(record: dict[str, Any]) -> dict[str, Any]:
        """Chi giu field hop le, ep kieu datetime, bo field la."""
        cleaned: dict[str, Any] = {}
        for key, value in record.items():
            if key not in ALLOWED_COLUMNS:
                continue
            if key in DATETIME_COLUMNS and isinstance(value, str) and value:
                try:
                    # Ho tro chuoi ISO 8601 co "Z" o cuoi (YouTube API tra ve dang nay).
                    cleaned[key] = datetime.fromisoformat(value.replace("Z", "+00:00"))
                except ValueError:
                    cleaned[key] = None
            else:
                cleaned[key] = value
        return cleaned
 
    def load_records(self, records: Iterable[dict[str, Any]]) -> dict[str, Any]:
        """
        Upsert nhieu record theo video_id. Loi tung record duoc ghi lai
        trong result["failed"] thay vi lam dung toan bo tien trinh.
        """
        result = LoadResult()
        conn = None
        try:
            conn = self._connect()
            conn.autocommit = False
            cur = conn.cursor()
            for raw_record in records:
                record = self._clean_record(raw_record)
                if not record.get("video_id"):
                    result.failed.append({"record": raw_record, "error": "missing video_id"})
                    continue
                try:
                    self._merge_one(cur, record)
                    conn.commit()
                    result.inserted_or_updated += 1
                except Exception as exc:  # noqa: BLE001 - ghi loi per-record
                    conn.rollback()
                    logger.warning("Insert failed for %s: %s", record.get("video_id"), exc)
                    result.failed.append({"video_id": record.get("video_id"), "error": str(exc)})
        finally:
            if conn is not None:
                conn.close()
 
        logger.info(
            "Load hoan tat: %s upsert thanh cong, %s that bai",
            result.inserted_or_updated,
            len(result.failed),
        )
        return result.as_dict()
 
    @staticmethod
    def _merge_one(cur: pyodbc.Cursor, record: dict[str, Any]) -> None:
        columns = list(record.keys())
        update_columns = [c for c in columns if c != "video_id"]
 
        set_clause = ", ".join(f"target.{c} = source.{c}" for c in update_columns)
        insert_columns = ", ".join(columns)
        insert_values = ", ".join(f"source.{c}" for c in columns)
        select_placeholders = ", ".join(f"? AS {c}" for c in columns)
 
        query = f"""
            MERGE youtube_videos AS target
            USING (SELECT {select_placeholders}) AS source
            ON target.video_id = source.video_id
            WHEN MATCHED THEN
                UPDATE SET {set_clause}, target.inserted_at = SYSUTCDATETIME()
            WHEN NOT MATCHED THEN
                INSERT ({insert_columns})
                VALUES ({insert_values});
        """
        cur.execute(query, list(record.values()))
 
 
if __name__ == "__main__":
    # Vi du chay thu nhanh de kiem tra ket noi.
    sample = [
        {
            "video_id": "TEST_VIDEO_ID_001",
            "title": "Sample video for pipeline test",
            "channel_id": "UC_TEST",
            "channel_title": "Test Channel",
            "region_code": "VN",
            "view_count": 1000,
            "like_count": 50,
            "comment_count": 5,
            "is_trending": 1,
            "trending_rank": 1,
            "collected_at": "2026-09-27T10:00:00+00:00",
            "raw_object_path": "raw/2026-09-27/youtube_popular_raw.json",
        }
    ]
    loader = DBLoader()
    print(loader.load_records(sample))