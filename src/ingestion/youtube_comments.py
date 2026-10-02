import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")
youtube = build("youtube", "v3", developerKey=api_key)


def fetch_top_comments(video_id, region_code="JP", max_comments=100):
    """
    Cào tối đa max_comments bình luận nổi bật (top relevance) của một video.
    """
    rows = []
    page_token = None

    while len(rows) < max_comments:
        try:
            request = youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=min(100, max_comments - len(rows)),
                order="relevance",
                textFormat="plainText",
                pageToken=page_token,
            )
            response = request.execute()
        except HttpError as e:
            # Bắt lỗi nếu video tắt tính năng bình luận hoặc video riêng tư
            if "commentsDisabled" in str(e):
                print(f"  [!] Video {video_id} đã tắt tính năng bình luận (Comments Disabled).")
            else:
                print(f"  [!] Lỗi API khi lấy bình luận của video {video_id}: {e}")
            break
        except Exception as e:
            print(f"  [!] Lỗi không xác định khi cào video {video_id}: {e}")
            break

        for item in response.get("items", []):
            top = item["snippet"]["topLevelComment"]
            snippet = top["snippet"]
            rows.append({
                "comment_id": top["id"],
                "video_id": video_id,
                "region_code": region_code,
                "comment_text": snippet.get("textDisplay", ""),
                "comment_like_count": snippet.get("likeCount", 0),
                "comment_published_at": snippet.get("publishedAt"),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            })

        page_token = response.get("nextPageToken")
        if not page_token:
            break

    return pd.DataFrame(rows)


def crawl_comments_for_video_list(
    video_list, 
    max_comments_per_video=100, 
    region_code="JP", 
    output_dir="data/raw/comments"
):
    """
    Cào bình luận cho danh sách video được chỉ định và lưu ra file CSV & JSON.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    all_comments = []
    total = len(video_list)
    print("=" * 60)
    print(f"BẮT ĐẦU CÀO BÌNH LUẬN CHO {total} VIDEO TRENDING")
    print("=" * 60)

    for idx, item in enumerate(video_list, start=1):
        if isinstance(item, dict):
            vid = item.get("video_id")
            region = item.get("region_code", region_code)
        else:
            vid = str(item).strip()
            region = region_code

        print(f"[{idx}/{total}] Đang lấy comments của video: {vid} (Region: {region})...")
        df_comments = fetch_top_comments(video_id=vid, region_code=region, max_comments=max_comments_per_video)

        if not df_comments.empty:
            all_comments.append(df_comments)
            print(f"    -> Đã lấy thành công {len(df_comments)} bình luận.")
        else:
            print(f"    -> Không có bình luận.")

        # Nghỉ nhẹ 0.3s để đảm bảo an toàn quota API
        time.sleep(0.3)

    if all_comments:
        final_df = pd.concat(all_comments, ignore_index=True)

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        json_file = out_path / f"trending_comments_{timestamp}.json"

        # Chỉ lưu JSON với định dạng danh sách bản ghi và thụt dòng 2 khoảng trắng
        final_df.to_json(json_file, orient="records", force_ascii=False, indent=2)

        print("\n" + "=" * 60)
        print("HOÀN THÀNH THU THẬP RAW COMMENTS!")
        print(f"- Tổng số bình luận thu thập được: {len(final_df)}")
        print(f"- Đã lưu file JSON: {json_file}")
        print("=" * 60)
        return final_df
    else:
        print("\n[!] Không thu thập được bình luận nào từ danh sách video.")
        return pd.DataFrame()


if __name__ == "__main__":
    # =========================================================================
    # DÁN DANH SÁCH 10 - 20 VIDEO ID BẠN ĐÃ LỌC THỦ CÔNG VÀO DƯỚI ĐÂY:
    # =========================================================================
    MANUAL_TRENDING_VIDEOS = [
        "bX1lt9yF_3s",  # Video 1
        "Z9NWm-Ycy2Q",  # Video 2
        "uaub3iRXnEk",  # Video 3
        "9M4W-t8_zK8",
        "4urpSWkaboA",
        "g0CVF2HCNM4",
        "nn2V3mptPLg",
        "XwCyAnRevrg",
        "sGQ_AaYImXA",
        "FvRaYwGW0k4",
        "LZMrGVAw1S0",
        "DTEGZrVSWQY",
        "nKl2Xqw5t4Q",
        "CWcSpLxtO84"
    ]

    crawl_comments_for_video_list(
        video_list=MANUAL_TRENDING_VIDEOS,
        max_comments_per_video=100,  # Số comment lấy mỗi video (tối đa 100)
        region_code="JP",           # Mã quốc gia (JP, VN, US, ...)
        output_dir="data/raw/comments"
    )