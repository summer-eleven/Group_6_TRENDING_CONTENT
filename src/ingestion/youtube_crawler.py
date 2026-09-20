import json
import requests
import pandas as pd
from bs4 import BeautifulSoup

search_queries = ["trending music",
"trending gaming",
"trending technology",
"trending movies",
"trending sports",
"viral videos",
"popular videos",
"new music",
"entertainment",
"trending news"

"viral music",
"new song 2026",
"popular song 2026",
"gaming video",
"new games 2026",
"technology news",
"AI technology",
"smartphone 2026",
"movie trailers",
"new movies 2026",

"football highlights",
"basketball highlights",
"sports highlights",
"funny videos",
"viral tiktok",
"travel videos",
"food videos",
"education videos",
"science videos",
"podcast"]

all_video_data = []

def find_video_renderers(obj):
    videos = []

    if isinstance(obj, dict):
        if "videoRenderer" in obj:
            videos.append(obj["videoRenderer"])
        for key, value in obj.items():
            videos.extend(find_video_renderers(value))
    elif isinstance(obj, list):
        for item in obj:
            videos.extend(find_video_renderers(item))
    return videos

for query in search_queries:
    print("\nCrawling:", query)

    url = "https://www.youtube.com/results"
    params = {"search_query": query}

    response = requests.get(url, params=params, timeout=10)

    print("Status Code:", response.status_code)

    print("HTML length:", len(response.text))

    soup = BeautifulSoup(response.text, 'html.parser')

    html = response.text

    marker = "var ytInitialData = "

    start = html.find(marker)
    if start == -1:
        print("ytInitialData not found")
        continue

    start += len(marker)
    end = html.find(";</script>", start)

    json_text = html[start:end]
    data = json.loads(json_text)

    print("ytInitialData extracted successfully")


    videos = find_video_renderers(data)
    print("Number of video found:", len(videos))


    for video in videos:
        video_id = video.get("videoId", "")
        title_runs = video.get("title", {}).get("runs", [])
        title = title_runs[0].get("text", "") if title_runs else ""
        owner_runs = video.get("ownerText", {}).get("runs", [])
        channel = owner_runs[0].get("text", "") if owner_runs else ""
        views = video.get("viewCountText", {}).get("simpleText", "")
        published = video.get("publishedTimeText", {}).get("simpleText", "")
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        all_video_data.append({
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "views": views,
            "published": published,
            "url": video_url,
            "search_query": query
        })

print("\nFirst 5 videos:")

for item in all_video_data[:5]:
    print(item)

df = pd.DataFrame(all_video_data)
df = df.drop_duplicates(subset=["video_id"])

output_path = "data/raw/youtube_raw.csv"

df.to_csv(output_path, index=False, encoding='utf-8-sig')

print("\n=====================================")
print("CRAWLING COMPLETED")
print("Total unique videos:", len(df))
print("Dataset shape:", df.shape)
print("Saved to:", output_path)
print("=====================================")