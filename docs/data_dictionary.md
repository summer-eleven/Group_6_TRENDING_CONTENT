# Initial Data Dictionary

This document defines the initial variables that will be used in the YouTube Trending Content Analysis project.

| Variable | Description | Data Type | Role |
|---|---|---|---|
| video_id | Unique identifier of a YouTube video | String | Identifier |
| title | Title of the video | String | Feature |
| published_at | Date and time when the video was published | DateTime | Feature |
| view_count | Total number of video views | Integer | Popularity indicator |
| like_count | Total number of likes | Integer | Engagement feature |
| comment_count | Total number of comments | Integer | Engagement feature |
| trending_status | Indicates whether the video is trending | Boolean | Target |
| category_id | YouTube video category identifier | String | Feature |

## Derived Variables

Additional variables may be created during data processing, including:

- Upload hour
- Upload time group
- Engagement rate
- Negative engagement indicators

The final Data Dictionary will be updated after the actual YouTube data is collected and validated.
docs: add initial data dictionary
