# Batch Video Scheduling Guide

This guide explains how to automatically schedule multiple videos for YouTube using the batch upload system.

## Overview

The batch scheduling system automatically:
- Finds all videos in `output/` directory
- Loads SEO metadata from JSON files
- Calculates optimal publish schedule (6 videos per day)
- Uploads videos as private with scheduled publish times
- Saves schedule to CSV for reference

## Default Schedule Pattern

The scheduler will find the earliest available slot starting from the current moment, prioritizing any open slots today that fall within the configured hours, then moving to tomorrow if today's slots are exhausted or in the past.

```
Example (assuming current time allows for today's slots):
Day N (Today):  [Earliest available slot today], ... [Last available slot today]
Day N+1 (Tomorrow):  6 AM,  8 AM, 10 AM, 12 PM,  2 PM,  4 PM  (6 videos)
Day N+2:  6 AM,  8 AM, 10 AM, 12 PM,  2 PM,  4 PM  (6 videos)
...and so on until all videos are scheduled
```

**Configuration (in `.env`):**
- `YOUTUBE_TIMEZONE`: Your timezone (default: America/Chicago)
- `YOUTUBE_SCHEDULE_START_HOUR`: First video hour (default: 6 = 6 AM)
- `YOUTUBE_SCHEDULE_END_HOUR`: Last video hour (default: 16 = 4 PM)
- `YOUTUBE_SCHEDULE_INTERVAL_HOURS`: Hours between videos (default: 2)

## Usage

### 1. Preview Schedule (Dry Run)

Preview the schedule without uploading:

```bash
python -m src.main schedule-uploads --dry-run
```

This will show you:
- Total number of videos found
- Calculated publish schedule, **starting from the earliest available slot today (if applicable) or tomorrow.**
- Detailed table with each video and its publish time
- No videos will be uploaded

**Example output:**
```
📅 Batch Video Scheduling

Found 15 videos to schedule

Schedule Summary (America/Chicago):
Total videos: 15
First publish: 2025-11-12 06:00
Last publish: 2025-11-14 16:00

Daily breakdown:
  2025-11-12: 6 videos at 06:00, 08:00, 10:00, 12:00, 14:00, 16:00
  2025-11-13: 6 videos at 06:00, 08:00, 10:00, 12:00, 14:00, 16:00
  2025-11-14: 3 videos at 06:00, 08:00, 10:00

✓ Schedule validation passed

🔍 Dry run mode - no uploads will be performed

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┓
┃ Video          ┃ Publish Time      ┃ Publish Time      ┃
┃                ┃ (Local)           ┃ (UTC)             ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━┩
│ video_001.mp4  │ 2025-11-12 06:00  │ 2025-11-12 12:00  │
│ video_002.mp4  │ 2025-11-12 08:00  │ 2025-11-12 14:00  │
│ video_003.mp4  │ 2025-11-12 10:00  │ 2025-11-12 16:00  │
│ ...            │ ...               │ ...               │
└────────────────┴───────────────────┴───────────────────┘
```

### 2. Upload and Schedule (Default)

Upload all videos with automatic scheduling starting tomorrow:

```bash
python -m src.main schedule-uploads
```

This will:
1. Find all `video_*.mp4` files in `output/`
2. Load corresponding `video_*_metadata.json` files
3. Calculate schedule starting tomorrow at 6 AM
4. Upload each video as private with scheduled publish time
5. Save results to `output/scheduled_videos.csv`

### 3. Upload with Custom Start Date

Specify a start date:

```bash
python -m src.main schedule-uploads --start-date 2025-11-15
```

Schedule will start on November 15, 2025 at 6 AM.

## Prerequisites

### Required Files

For each video in `output/`:
- `video_XXX.mp4` - The video file
- `video_XXX_metadata.json` - SEO metadata (optional but recommended)

If metadata file doesn't exist, defaults will be used:
- Title: "Motivational Short {N}"
- Description: "An inspiring motivational message. #motivation #shorts"
- Tags: ["motivation", "shorts", "inspiration", "self-improvement"]

### Generate Metadata

If you have videos without metadata, generate it first:

```bash
# Generate videos with SEO metadata
python -m src.main generate --count 10

# This creates:
# - output/video_001.mp4 + video_001_metadata.json
# - output/video_002.mp4 + video_002_metadata.json
# - ...
```

## Configuration

### Timezone Configuration

Edit `.env` to set your timezone:

```bash
# Common US timezones
YOUTUBE_TIMEZONE=America/Chicago      # Central Time
YOUTUBE_TIMEZONE=America/New_York     # Eastern Time
YOUTUBE_TIMEZONE=America/Los_Angeles  # Pacific Time
YOUTUBE_TIMEZONE=America/Denver       # Mountain Time

# Other timezones
YOUTUBE_TIMEZONE=Europe/London
YOUTUBE_TIMEZONE=Asia/Tokyo
YOUTUBE_TIMEZONE=Australia/Sydney
```

Full list: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

### Schedule Configuration

Customize your publishing schedule in `.env`:

```bash
# Example 1: 8 videos per day (6 AM - 8 PM, every 2 hours)
YOUTUBE_SCHEDULE_START_HOUR=6
YOUTUBE_SCHEDULE_END_HOUR=20
YOUTUBE_SCHEDULE_INTERVAL_HOURS=2

# Example 2: 4 videos per day (9 AM - 6 PM, every 3 hours)
YOUTUBE_SCHEDULE_START_HOUR=9
YOUTUBE_SCHEDULE_END_HOUR=18
YOUTUBE_SCHEDULE_INTERVAL_HOURS=3

# Example 3: 3 videos per day (8 AM - 8 PM, every 6 hours)
YOUTUBE_SCHEDULE_START_HOUR=8
YOUTUBE_SCHEDULE_END_HOUR=20
YOUTUBE_SCHEDULE_INTERVAL_HOURS=6
```

## Output Files

### scheduled_videos.csv

After successful upload, a CSV file is created with the schedule:

```csv
Video Path,Publish Time (UTC),YouTube URL
output/video_001.mp4,2025-11-12T12:00:00+00:00,https://www.youtube.com/watch?v=abc123
output/video_002.mp4,2025-11-12T14:00:00+00:00,https://www.youtube.com/watch?v=def456
...
```

Use this to:
- Track what was scheduled
- Reference video URLs
- Import into spreadsheets for planning
- Verify schedule against your content calendar

## Workflow Example

Complete workflow from generation to scheduling:

```bash
# Step 1: Generate videos
python -m src.main generate --count 12

# Step 2: Preview schedule
python -m src.main schedule-uploads --dry-run

# Step 3: If schedule looks good, upload
python -m src.main schedule-uploads

# Step 4: Check YouTube Studio to verify
# https://studio.youtube.com → Content → Videos
```

## Error Handling

### No Videos Found

```
⚠ No videos found in output/
```

**Solution:** Generate videos first with `python -m src.main generate --count 5`

### Missing Metadata Warning

```
⚠ No metadata found for video_001.mp4, using default title
```

**Impact:** Video will upload with generic title/description
**Solution:** Generate metadata or edit manually after upload

### Upload Failure

```
✗ video_005.mp4: API rate limit exceeded
```

**Impact:** Video not uploaded, marked as ERROR in results
**Solution:** Wait and retry failed videos individually

## Verification

After batch upload:

1. **Go to YouTube Studio**
   - URL: https://studio.youtube.com
   - Navigate to: Content → Videos

2. **Verify Videos**
   - Status: "Private"
   - Badge: "Scheduled"
   - Publish time: Matches your schedule

3. **Check Details**
   - Click video to see full metadata
   - Verify title, description, tags
   - Check Made for Kids: No
   - Check Synthetic Media: Should be No (unless imitating real people)

## Best Practices

### 1. Generate in Batches

```bash
# Generate one week of content (42 videos at 6/day)
python -m src.main generate --count 42

# Schedule the batch
python -m src.main schedule-uploads
```

### 2. Stagger Content Types

```bash
# Week 1: Motivational content
python -m src.main generate --count 42 --profile frank_motivational

# Week 2: Calm content
python -m src.main generate --count 42 --profile brody_calm

# Schedule all at once
python -m src.main schedule-uploads
```

### 3. Plan Around Events

```bash
# Schedule content to start after holidays
python -m src.main schedule-uploads --start-date 2025-12-26

# Or schedule for specific campaign start
python -m src.main schedule-uploads --start-date 2025-01-01
```

### 4. Always Preview First

```bash
# ALWAYS run dry-run first
python -m src.main schedule-uploads --dry-run

# Review the output carefully
# Then commit to upload
python -m src.main schedule-uploads
```

## Troubleshooting

### Issue: Videos publish at wrong time

**Cause:** Timezone mismatch
**Solution:** Check `YOUTUBE_TIMEZONE` in `.env` matches your desired timezone

### Issue: Schedule validation failed

```
✗ Schedule validation failed: Video 7 scheduled at 18:00, outside allowed range
```

**Cause:** Calculated schedule exceeds end hour
**Solution:** This shouldn't happen with default settings. Check configuration.

### Issue: Rate limit errors

**Cause:** YouTube API quota exceeded
**Solution:**
- Default quota: 10,000 units/day ≈ 6 uploads
- Wait 24 hours for quota reset
- Or request quota increase from Google

### Issue: Duplicate uploads

**Cause:** Running schedule-uploads multiple times
**Solution:**
- Move uploaded videos to different directory
- Or rename them (not matching `video_*.mp4`)
- Or delete videos after successful upload

## Advanced Usage

### Programmatic Scheduling

For custom scheduling logic:

```python
from datetime import datetime, timedelta
from src.workflow import WorkflowOrchestrator

async def custom_schedule():
    orchestrator = WorkflowOrchestrator()

    # Custom start time (specific date and hour)
    start_date = datetime(2025, 11, 15, 6, 0, 0)

    results = await orchestrator.schedule_batch_upload(
        start_date=start_date,
        dry_run=False,
    )

    print(f"Scheduled {len(results)} videos")
```

### Integration with External Calendar

Export scheduled_videos.csv and import into:
- Google Calendar
- Notion content calendar
- Airtable
- Trello
- Any tool that accepts CSV import

---

**Related Documentation:**
- [YOUTUBE_SCHEDULING.md](YOUTUBE_SCHEDULING.md) - Single video scheduling
- [README.md](../README.md) - General usage guide
- [CHANGELOG.md](CHANGELOG.md) - Version history
