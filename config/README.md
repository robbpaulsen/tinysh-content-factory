# Config Directory

## ⚠️ IMPORTANT: This directory is for LEGACY/FALLBACK only

For **multi-channel setup** (recommended), configure each channel independently:

```
channels/<channel_name>/
├── channel.yaml      ← Channel-specific settings (subreddit, content_type, etc.)
├── profiles.yaml     ← Channel-specific voice/music profiles
├── prompts/          ← Optional custom prompts
│   ├── script.txt
│   └── image.txt
└── credentials.json  ← Channel-specific OAuth credentials
```

## Files in this Directory

### `profiles.yaml` (LEGACY - Not Used in Multi-Channel)

This file is **only used** as a fallback when:
- Running commands **without** `--channel` flag
- Using single-channel legacy mode

**For multi-channel:** Place `profiles.yaml` in each channel directory instead:
- `channels/momentum_mindset/profiles.yaml`
- `channels/wealth_wisdom/profiles.yaml`
- `channels/finance_wins/profiles.yaml`

### `.env.example`

Template for creating `.env` file in project root.

**Contains ONLY global settings:**
- API keys (Gemini, Together.ai)
- Media server URL
- Google Sheets spreadsheet ID (shared)
- FFmpeg settings (global)
- SEO settings (global)
- Logging settings (global)

**Does NOT contain channel-specific settings** (those are in `channel.yaml`):
- ❌ SUBREDDIT
- ❌ CONTENT_TYPE
- ❌ ART_STYLE
- ❌ SHEET_NAME
- ❌ ACTIVE_PROFILE
- ❌ YOUTUBE_CATEGORY_ID
- ❌ YOUTUBE_SCHEDULE_*

## Migration from Old System

If you have an old `.env` with channel-specific settings:

1. **Move settings to channel.yaml:**
   ```yaml
   # channels/momentum_mindset/channel.yaml
   content:
     subreddit: "selfimprovement"
     content_type: "motivational speech"
     sheet_tab: "momentum_mindset"

   image:
     style: "cinematic, dramatic lighting..."

   youtube:
     category_id: "22"
     schedule:
       timezone: "America/Chicago"
       start_hour: 6
       end_hour: 16

   default_profile: "frank_motivational"
   ```

2. **Remove from .env:**
   - Delete: SUBREDDIT, CONTENT_TYPE, ART_STYLE, SHEET_NAME, ACTIVE_PROFILE
   - Keep: GOOGLE_API_KEY, TOGETHER_API_KEY, MEDIA_SERVER_URL, etc.

3. **Update your .env to match `.env.example`**

## See Also

- `.github/CHANNEL_STRUCTURE.md` - Complete channel directory structure
- `.github/TESTING_GUIDE.md` - How to test multi-channel setup
- `QUICK_TEST.md` - Quick reference commands
