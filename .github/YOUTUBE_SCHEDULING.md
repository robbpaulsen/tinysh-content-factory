# YouTube Scheduling Guide

This guide explains how to upload videos with scheduled publish times.

## Overview

Videos can be uploaded to YouTube with a scheduled publish time. This allows you to:
- Upload videos in advance
- Publish at optimal times for your audience
- Batch upload multiple videos for a content calendar
- Ensure consistent publishing schedule

## Configuration

### Default Settings (config/profiles.yaml)

```bash
# YouTube Upload Settings
YOUTUBE_PRIVACY_STATUS=private  # Required for scheduling
YOUTUBE_CATEGORY_ID=22          # 22 = People & Blogs
```

### Important Notes

1. **Privacy Status**: Videos with scheduled publish times MUST be uploaded as `private`
2. **Category**: Category 22 = "People & Blogs" (suitable for motivational content)
3. **AI Content Declaration**:
   - `containsSyntheticMedia: true` - Automatically set (AI-generated content)
   - `selfDeclaredMadeForKids: false` - Automatically set (not for kids)

## Usage

### Method 1: Programmatic Upload with Scheduling

```python
from datetime import datetime, timedelta
from pathlib import Path
from src.services.youtube import YouTubeService

# Initialize service
youtube = YouTubeService()

# Set publish time (e.g., tomorrow at 10:00 AM UTC)
publish_time = datetime(2025, 11, 12, 10, 0, 0)  # UTC time

# Upload with scheduling
result = youtube.upload_video(
    video_path=Path("output/video_001.mp4"),
    title="My Motivational Short",
    description="An inspiring message. #motivation #shorts",
    tags=["motivation", "shorts", "inspiration"],
    privacy_status="private",  # Required
    publish_at=publish_time,   # Schedule publish time
)

print(f"Video scheduled for: {publish_time}")
print(f"Video URL: {result.url}")
```

### Method 2: Upload as Private (Manual Publish)

```python
# Upload without scheduling (stays private until manual publish)
result = youtube.upload_video(
    video_path=Path("output/video_001.mp4"),
    title="My Motivational Short",
    description="An inspiring message. #motivation #shorts",
    tags=["motivation", "shorts"],
    privacy_status="private",  # No publish_at parameter
)
```

### Method 3: Using SEO Metadata

```python
import json
from pathlib import Path

# Load SEO-optimized metadata
metadata_path = Path("output/video_001_metadata.json")
with open(metadata_path) as f:
    metadata = json.load(f)

# Upload with SEO metadata
youtube = YouTubeService()
publish_time = datetime.utcnow() + timedelta(hours=24)

result = youtube.upload_video(
    video_path=Path("output/video_001.mp4"),
    title=metadata["title"],
    description=metadata["description"],
    tags=metadata["tags"],
    category_id=metadata["category_id"],
    publish_at=publish_time,
)
```

## Scheduling Multiple Videos

For batch uploads with scheduled times:

```python
from datetime import datetime, timedelta

youtube = YouTubeService()
base_time = datetime(2025, 11, 12, 10, 0, 0)  # Start: Nov 12, 10:00 AM UTC

videos = [
    ("video_001.mp4", "Day 1: Start Your Journey", 0),    # Publish immediately
    ("video_002.mp4", "Day 2: Build Momentum", 24),       # +24 hours
    ("video_003.mp4", "Day 3: Stay Consistent", 48),      # +48 hours
]

for filename, title, hours_offset in videos:
    publish_time = base_time + timedelta(hours=hours_offset)

    result = youtube.upload_video(
        video_path=Path(f"output/{filename}"),
        title=title,
        description="Daily motivation series. #motivation #shorts",
        tags=["motivation", "shorts", "daily"],
        publish_at=publish_time,
    )

    print(f"✓ {title} scheduled for {publish_time}")
```

## Workflow Integration

### Current Workflow (Immediate Upload)

Currently, the workflow uploads videos immediately:

```python
# src/workflow.py:243
result = self.youtube.upload_video(
    video_path=video_path,
    title=script.title,
    description=script.description,
    tags=["motivation", "shorts", "inspiration", "self-improvement"],
)
```

### Enhanced Workflow (With Scheduling)

To add scheduling to the main workflow, modify `upload_to_youtube()`:

```python
async def upload_to_youtube(
    self,
    video_id: str,
    script: VideoScript,
    output_dir: Path | None = None,
    publish_at: datetime | None = None,  # Add parameter
) -> str:
    # ... existing download code ...

    result = self.youtube.upload_video(
        video_path=video_path,
        title=script.title,
        description=script.description,
        tags=["motivation", "shorts", "inspiration", "self-improvement"],
        publish_at=publish_at,  # Pass scheduling parameter
    )

    return result.url
```

## Time Zones

**Important**: YouTube API requires UTC time in RFC 3339 format.

```python
from datetime import datetime, timezone

# Method 1: Explicitly use UTC
publish_time = datetime(2025, 11, 12, 10, 0, 0, tzinfo=timezone.utc)

# Method 2: Convert from local time to UTC
import pytz
local_tz = pytz.timezone("America/Chicago")  # Your timezone
local_time = local_tz.localize(datetime(2025, 11, 12, 10, 0, 0))
publish_time = local_time.astimezone(timezone.utc)
```

## YouTube API Limits

- **Upload Quota**: Each upload consumes quota (1600 units per upload)
- **Default Quota**: 10,000 units per day = ~6 uploads/day
- **Scheduling Limit**: Can schedule up to 100 videos per channel

## Verification

After uploading, verify in YouTube Studio:
1. Go to https://studio.youtube.com
2. Navigate to Content → Videos
3. Check video status:
   - "Private" with scheduled publish time
   - "Scheduled" badge showing publish date/time

## Troubleshooting

### Error: "Scheduled videos must be private"

- **Cause**: `publish_at` set but `privacy_status` is not "private"
- **Fix**: Code automatically forces `privacy_status="private"` when `publish_at` is set
- **Warning**: You'll see a log warning if this happens

### Error: "Invalid publish time"

- **Cause**: Publish time is in the past or invalid format
- **Fix**: Ensure `publish_at` is a future datetime in UTC

### Video doesn't publish at scheduled time

- **Cause**: YouTube processing delay
- **Expected**: Videos typically publish within 1-2 minutes of scheduled time
- **Note**: Very short delays (< 1 hour) may not be respected

## Examples

See `scripts/schedule_upload_example.py` for complete working examples.

---

**Related Documentation:**
- [YouTube Data API - Videos: insert](https://developers.google.com/youtube/v3/docs/videos/insert)
- [RFC 3339 DateTime Format](https://datatracker.ietf.org/doc/html/rfc3339)
