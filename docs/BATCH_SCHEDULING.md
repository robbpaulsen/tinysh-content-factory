# Batch Video Scheduling Guide

This guide explains how to automatically schedule multiple videos for YouTube using the **2-Phase Upload System**.

## Overview

The scheduling system is designed to be intelligent and gap-aware. It automatically:
- Detects existing scheduled videos on your channel.
- Finds "gaps" in your schedule (e.g., a missing slot at 2 PM today).
- Prioritizes filling gaps in the *current day* before moving to tomorrow.
- Respects channel-specific configurations (Timezone, Category, Start/End Hours).

## Scheduling Logic (Smart Gap Filling)

The scheduler follows these rules to determine the next publish time:

1.  **Scan Horizon**: It checks the next 30 days for potential slots.
2.  **Gap Detection**: It queries the YouTube API for videos already scheduled (private status + publishAt set).
3.  **Priority**:
    -   **Rule 1**: If there is an open slot *today* (between `start_hour` and `end_hour`) that is in the future (current time + 5 mins buffer), schedule there first.
    -   **Rule 2**: If today is full or passed, move to the earliest slot tomorrow.
    -   **Rule 3**: Respect the `interval_hours` spacing between all videos.

**Example:**
Current time: 11:00 AM.
Schedule settings: 6 AM - 4 PM, every 2 hours.
Existing scheduled videos: 6 AM, 8 AM, [GAP], 12 PM, 2 PM.

*   **Old Logic**: Would append to the end (next available might be 4 PM or tomorrow).
*   **New Smart Logic**: Detects the gap at 10:00 AM is in the past (invalid). Checks 12 PM (occupied). Checks 2 PM (occupied). Checks 4 PM (available). Schedules at 4 PM today.

## Channel Configuration

The scheduler strictly adheres to `channel.yaml` settings:

-   **Timezone**: Uses `youtube.schedule.timezone` (e.g., `America/Mexico_City`). All schedule calculations are converted to this timezone.
-   **Category**: Enforces `youtube.category_id` (e.g., "22" for People & Blogs), overriding any AI-generated guesses.
-   **Window**: Respects `start_hour` and `end_hour` strictly.

## Usage

### Phase 1: Batch Upload (`batch-upload`)

Uploads videos to YouTube as `private`. This phase handles the heavy lifting of file transfer.

```bash
python -m src.main batch-upload --channel wealth_wisdom --limit 5
```

-   **Metadata**: Reads `_metadata.json` files to set Title, Description, and Tags immediately.
-   **Settings**: Applies `made_for_kids` and `language` settings from channel config.
-   **Result**: Videos are online but private, waiting to be scheduled.

### Phase 2: Batch Schedule (`batch-schedule`)

Calculates dates and updates the `publishAt` timestamp.

```bash
python -m src.main batch-schedule --channel wealth_wisdom --dry-run
```

-   **Dry Run**: Always run with `--dry-run` first to preview the calculated dates.
-   **Execution**: Remove the flag to apply changes.

```bash
python -m src.main batch-schedule --channel wealth_wisdom
```

**Output Example:**
```
📅 Batch Video Scheduling

Found 3 already scheduled videos

Scheduled Videos (Dry Run)
┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┓
┃ Video         ┃ Publish Time     ┃ Publish Time     ┃
┃               ┃ (Local)          ┃ (UTC)            ┃
┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━┩
│ video_004.mp4 │ 2025-11-28 12:00 │ 2025-11-28 18:00 │  <-- Fills gap today
│ video_005.mp4 │ 2025-11-28 14:00 │ 2025-11-28 20:00 │
└───────────────┴──────────────────┴──────────────────┘
```

## Troubleshooting

### "Timezone ignores my setting"
Ensure `timezone` is set correctly in `channels/<your_channel>/channel.yaml` under `youtube.schedule`. The system logs "Scheduler Timezone: <Your/Timezone>" at the start of `batch-schedule`.

### "Videos are scheduled at 6 AM but appear overlapped"
This happens if `get_scheduled_videos` fails to read existing videos. Run `batch-schedule` in verbose mode (`-v`) to confirm it finds existing videos ("Found X already scheduled videos").

### "Wrong Category"
The system enforces the category from `channel.yaml` during Phase 2 (`batch-schedule`). Even if Phase 1 uploaded with a generic category, Phase 2 will correct it.