# Channel Directory Structure

This document defines the correct structure for each channel directory in the multi-channel system.

## Standard Channel Structure

Each channel must follow this directory structure:

```
channels/<channel_name>/
├── channel.yaml          # Channel configuration (REQUIRED)
├── profiles.yaml         # Voice & music profiles (REQUIRED for AI channels)
├── prompts/              # Custom prompts directory (OPTIONAL)
│   ├── script.txt       # Custom LLM script generation prompt
│   ├── image.txt        # Custom image generation prompt
│   └── seo.txt          # Custom SEO optimization prompt (future)
├── assets/               # Channel-specific assets
│   ├── intro.mp4        # Intro video (optional)
│   ├── outro.mp4        # Outro video (optional)
│   └── logo.png         # Channel logo (optional)
├── output/               # Generated videos (auto-created)
│   ├── video_001.mp4
│   ├── video_001_metadata.json
│   └── video_ids.csv
├── credentials.json      # YouTube OAuth credentials (gitignored)
└── token_youtube.json    # OAuth token (gitignored, auto-generated)
```

## File Loading Priority

### Profiles (profiles.yaml)

The system loads profiles in this order:

1. **Channel-specific**: `channels/<channel_name>/profiles.yaml`
2. **Global fallback**: `config/profiles.yaml` (if channel-specific not found)

**Best Practice**: Each channel should have its own `profiles.yaml` with channel-appropriate voices and music.

**Example**:
- `channels/wealth_wisdom/profiles.yaml` - Finance-focused profiles (professional, authoritative)
- `channels/momentum_mindset/profiles.yaml` - Motivation-focused profiles (energetic, inspiring)

### Custom Prompts (prompts/*.txt)

Custom prompts are **optional** and loaded per-channel:

- **script.txt**: Overrides default LLM script generation
  - When present: Skips motivational speech generation, uses custom prompt directly
  - Format: Plain text with `{title}` and `{content}` placeholders

- **image.txt**: Overrides default image generation style
  - When present: Prepends to image prompts for consistent visual style
  - Format: Plain text with `{scene_description}` placeholder

**Example**: `channels/wealth_wisdom/prompts/script.txt` uses "humble brag" tone for finance content

### Configuration (channel.yaml)

The `channel.yaml` file must include:

```yaml
# Basic info
name: "Channel Name"
description: "Channel description"
handle: "@ChannelHandle"
channel_type: "ai_generated_shorts"  # or ai_generated_videos, youtube_compilation

# Content settings
content:
  format: "shorts"
  duration_range: [15, 45]
  subreddit: "subreddit_name"
  sheet_tab: "channel_sheet_tab"
  content_type: "motivational speech"  # or "financial advice", etc.

# Video format
video:
  aspect_ratio: "9:16"
  width: 768
  height: 1344

# YouTube settings
youtube:
  category_id: "22"
  schedule:
    videos_per_day: 6
    start_hour: 6
    end_hour: 16
    interval_hours: 2
    timezone: "America/Chicago"

# SEO settings
seo:
  enabled: true
  channel_name: "ChannelName"
  target_audience: "target audience description"

# Voice & Music
default_profile: "profile_name"
profiles_path: "profiles.yaml"  # Relative to channel directory
```

## Code Implementation

### ChannelConfig Class

The `ChannelConfig` class (in `src/channel_config.py`) provides these properties:

- `output_dir` → `channels/<channel_name>/output/`
- `prompts_dir` → `channels/<channel_name>/prompts/`
- `assets_dir` → `channels/<channel_name>/assets/`
- `credentials_path` → `channels/<channel_name>/credentials.json`
- `youtube_token_path` → `channels/<channel_name>/token_youtube.json`
- `profiles_path` → `channels/<channel_name>/profiles.yaml` (or custom path from config)

### WorkflowOrchestrator

The workflow uses channel config to:

1. **Load profiles**: From `channel_config.profiles_path`
2. **Load custom prompts**: Via `channel_config.get_prompt('script')` and `channel_config.get_prompt('image')`
3. **Initialize YouTube service**: With channel-specific credentials
4. **Set output directory**: All videos go to channel's output dir

## Bug Fixes Applied (2025-11-15)

### Fixed Issues:

1. **workflow.py line 54-59**: Was hardcoding `"profiles.yaml"` instead of using `channel_config.profiles_path` property
   - **Before**: `profiles_path = self.channel_config.channel_dir / "profiles.yaml"`
   - **After**: `profiles_path = self.channel_config.profiles_path`

2. **profiles.yaml location**: Moved from project root to channel directories
   - **Before**: `/profiles.yaml` (global, incorrect)
   - **After**: `/channels/wealth_wisdom/profiles.yaml` (per-channel, correct)

3. **channel.yaml profiles_path**: Updated to use relative paths correctly
   - **Value**: `profiles_path: "profiles.yaml"` (relative to channel dir)

## Validation

To verify channel configuration loads correctly:

```bash
source .venv/bin/activate
python -c "
from src.channel_config import ChannelConfig

# Test channel
channel = ChannelConfig('wealth_wisdom')
print(f'Name: {channel.config.name}')
print(f'Profiles: {channel.profiles_path.exists()}')
print(f'Script prompt: {channel.get_prompt(\"script\") is not None}')
"
```

## Migration from Old System

If you have channels with incorrect structure:

1. **Move profiles.yaml**: From project root to `channels/<channel_name>/profiles.yaml`
2. **Update channel.yaml**: Set `profiles_path: "profiles.yaml"`
3. **Create prompts dir**: `mkdir -p channels/<channel_name>/prompts` (if using custom prompts)
4. **Verify**: Run validation script above

## Adding a New Channel

1. Create directory: `mkdir -p channels/new_channel/{assets,prompts,output}`
2. Create `channel.yaml` (copy from existing channel and modify)
3. Create `profiles.yaml` with channel-appropriate voices/music
4. (Optional) Add custom prompts in `prompts/script.txt` and `prompts/image.txt`
5. Add credentials: `channels/new_channel/credentials.json`
6. Test: `python -m src.main generate --channel new_channel --count 1`

## Best Practices

1. **Separate profiles per channel**: Each channel should have distinct voice/music to differentiate content
2. **Custom prompts for unique tones**: Use `prompts/script.txt` for channel-specific content styles (e.g., "humble brag" for finance)
3. **Channel-specific credentials**: Keep YouTube accounts separate for better scaling and risk management
4. **Version control**: Add `credentials.json` and `token_youtube.json` to `.gitignore`
5. **Output isolation**: Each channel's videos stay in its own output directory
