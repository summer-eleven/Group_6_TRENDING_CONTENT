import json

POPULAR_PATH = "data/raw/youtube_popular_raw.json"
CONTROL_PATH = "data/raw/youtube_control_raw.json"
OUTPUT_PATH = "data/raw/youtube_dataset_1000_raw.json"


with open(POPULAR_PATH, "r", encoding="utf-8") as file:
    popular_records = json.load(file)

with open(CONTROL_PATH, "r", encoding="utf-8") as file:
    control_records = json.load(file)


all_records = popular_records + control_records

unique_records = {}

for record in all_records:
    video_id = record.get("video_id")

    if not video_id:
        continue

    if video_id not in unique_records:
        unique_records[video_id] = record
    elif record.get("is_trending") == 1:
        unique_records[video_id] = record


records = list(unique_records.values())

trending_count = sum(
    1 for record in records
    if record.get("is_trending") == 1
)

control_count = sum(
    1 for record in records
    if record.get("is_trending") == 0
)


with open(OUTPUT_PATH, "w", encoding="utf-8") as file:
    json.dump(
        records,
        file,
        ensure_ascii=False,
        indent=2,
    )


print("=" * 60)
print("MERGE COMPLETED")
print("Popular input:", len(popular_records))
print("Control input:", len(control_records))
print("Total before deduplication:", len(all_records))
print("Total unique:", len(records))
print("Trending:", trending_count)
print("Control:", control_count)
print("Saved to:", OUTPUT_PATH)
print("=" * 60)