import glob
import os
import re
from pathlib import Path
import pandas as pd

# Đường dẫn đầu ra bắt buộc theo đề bài
OUTPUT_PATH = Path("data/processed/comments_clean_JP.csv")
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# 1. Tự động tìm file JSON thô mới nhất trong thư mục raw comments
json_files = glob.glob("data/raw/comments/*.json")
if not json_files:
    raise FileNotFoundError("Không tìm thấy file JSON bình luận nào trong data/raw/comments/!")

# Lấy file JSON mới nhất
latest_json = max(json_files, key=os.path.getmtime)
print(f"--> Đang đọc dữ liệu từ: {latest_json}")

# Đọc dữ liệu từ file JSON vào DataFrame
comments = pd.read_json(latest_json)
print(f"Tổng số bình luận ban đầu: {len(comments)}")

# 2. Xóa các bình luận trùng lặp theo ID
comments = comments.drop_duplicates(subset=["comment_id"])

# 3. Loại bỏ giá trị null/rỗng
comments = comments.dropna(subset=["comment_text"])
comments["comment_text"] = comments["comment_text"].astype(str).str.strip()
comments = comments[comments["comment_text"] != ""]

# 4. Chuẩn hóa văn bản theo đúng yêu cầu đề bài:
# - Thay thế URL bằng token <URL> (không xóa emoji hay chữ Nhật)
comments["comment_clean"] = comments["comment_text"].str.replace(
    r"https?://\S+|www\.\S+", " <URL> ", regex=True
)

# - Thu gọn nhiều khoảng trắng liên tiếp thành 1 khoảng trắng duy nhất
comments["comment_clean"] = comments["comment_clean"].str.replace(
    r"\s+", " ", regex=True
).str.strip()

# Loại bỏ các bình luận sau khi xóa URL/khoảng trắng bị rỗng
comments = comments[comments["comment_clean"] != ""]

# 5. Lưu ra file CSV theo đúng định dạng đầu ra bắt buộc
comments.to_csv(
    OUTPUT_PATH,
    index=False,
    encoding="utf-8-sig"  # utf-8-sig giúp Excel và các công cụ hiển thị chuẩn chữ Nhật và Emoji
)

print("=" * 60)
print(f"LÀM SẠCH HOÀN TẤT!")
print(f"- Số bình luận sau khi làm sạch: {len(comments)}")
print(f"- Đã lưu kết quả tại: {OUTPUT_PATH}")
print("=" * 60)