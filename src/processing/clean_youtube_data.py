import pandas as pd

input_path = "data/raw/youtube_raw.csv"
df = pd.read_csv(input_path)

print("Dataset shape:", df.shape)
print(df.head())

print("\nDataset info:")
print(df.info())

print("\nMissing values:")
print(df.isnull().sum())

print("\nDuplicate rows:")
print(df.duplicated().sum())

print("\nDuplicate video IDs:")
print(df["video_id"].duplicated().sum())

df["views"] = df["views"].fillna("0")
df["published"] = df["published"].fillna("Unknown")

print("\nMissing values after cleaning:")
print(df.isnull().sum())

df["views"] = (
    df["views"].astype(str).str.extract(r"([\d.,]+)", expand=False).str.replace(",", "", regex=False).str.replace(".", "", regex=False)
    )

df["views"] = pd.to_numeric(df["views"], errors="coerce").fillna(0).astype("int64")

print("\nViews after conversion:")
print(df["views"].head())

print("\nViews data type:")
print(df["views"].dtype)

df["published"] = df["published"].astype(str).str.strip()
df["title"] = df["title"].astype(str).str.strip()
df["channel"] = df["channel"].astype(str).str.strip()
df["search_query"] = df["search_query"].astype(str).str.strip()

print("\nText columns cleaned")
print(df[["published", "title", "channel", "search_query"]].head())

output_path = "data/processed/youtube_clean.csv"

df.to_csv(output_path, index=False, encoding='utf-8-sig')

print("\nCleaning completed")
print("Dataset shape:", df.shape)
print("Saved to:", output_path)
