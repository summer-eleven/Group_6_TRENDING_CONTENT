import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.getenv('DB_SERVER')};"
        f"DATABASE={os.getenv('DB_NAME')};"
        f"UID={os.getenv('DB_USER')};"
        f"PWD={os.getenv('DB_PASSWORD')};"
    )
    return pyodbc.connect(conn_str)


def insert_video(record: dict):
    """
    record: dict chứa các field khớp với bảng videos
    (video_id, title, channel_id, channel_title, category_id,
     published_at, view_count, like_count, comment_count, region_code)
    """
    sql = """
    MERGE INTO videos AS target
    USING (SELECT ? AS video_id) AS source
    ON target.video_id = source.video_id
    WHEN NOT MATCHED THEN
        INSERT (video_id, title, channel_id, channel_title, category_id,
                published_at, view_count, like_count, comment_count, region_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, (
            record["video_id"],
            record["video_id"],
            record["title"],
            record.get("channel_id"),
            record.get("channel_title"),
            record.get("category_id"),
            record.get("published_at"),
            record.get("view_count"),
            record.get("like_count"),
            record.get("comment_count"),
            record.get("region_code"),
        ))
        conn.commit()
        return True
    except Exception as e:
        print(f"[DB ERROR] Failed to insert {record.get('video_id')}: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def insert_many(records: list[dict]):
    """Insert nhiều record, trả về số lượng thành công/thất bại"""
    success, failed = 0, 0
    for r in records:
        if insert_video(r):
            success += 1
        else:
            failed += 1
    print(f"Insert done: {success} success, {failed} failed")
    return success, failed