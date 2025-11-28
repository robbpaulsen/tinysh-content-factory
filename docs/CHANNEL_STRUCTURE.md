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

### Google OAuth Credentials (credentials.json)

**IMPORTANT:** OAuth credentials are **account-specific** and **cannot be shared** between different Google accounts.

#### Multi-Channel with Separate Accounts (Recommended)

If each channel uses a **different Google/YouTube account** (most common setup):

```
channels/momentum_mindset/credentials.json   ← OAuth for account1@gmail.com
channels/wealth_wisdom/credentials.json      ← OAuth for account2@gmail.com
channels/finance_wins/credentials.json       ← OAuth for account3@gmail.com
```

**DO NOT use `.credentials/credentials.json` fallback** - it will cause 403 errors when trying to access other accounts' channels.

**Always specify `--channel`:**
```bash
python -m src.main generate --channel momentum_mindset --count 1
python -m src.main update-stories --channel wealth_wisdom --limit 5
```

#### Single Account for All Channels (Alternative)

If all channels are **brand channels** under the **same Google account**:

```
.credentials/credentials.json                ← OAuth for main account
channels/momentum_mindset/credentials.json   ← Copy of same OAuth (optional)
channels/wealth_wisdom/credentials.json      ← Copy of same OAuth (optional)
```

In this case, you can use the global fallback, but it's still recommended to place credentials in each channel directory for consistency.

**Error 403 Forbidden:** This error means you're trying to use OAuth credentials from one Google account to access a YouTube channel owned by a different account. Each channel must use credentials from its owning account.

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

## Configuration Priority System

The system uses a **3-tier priority** for loading configuration:

### Priority Order:
1. **Explicit arguments** - Direct values passed to functions
2. **Channel config** - Values from `channels/<channel_name>/channel.yaml`
3. **Global fallback** - Values from `.env` (only if channel config not available)

### Examples:

**Content Type:**
- wealth_wisdom → `"financial advice and money wisdom"` (from channel.yaml)
- momentum_mindset → `"motivational speech"` (from channel.yaml)
- No channel → `settings.content_type` (from .env)

**Image Style:**
- wealth_wisdom → Luxury finance aesthetic (from channel.yaml)
- momentum_mindset → Inspirational cinematic style (from channel.yaml)
- No channel → `settings.art_style` (from .env)

**Subreddit:**
- wealth_wisdom → `"personalfinance"` (from channel.yaml)
- momentum_mindset → `"selfimprovement"` (from channel.yaml)
- No channel → `settings.subreddit` (from .env)

This ensures **each channel uses its own configuration** and doesn't mix content styles between channels.

## Bug Fixes Applied (2025-11-15)

### Session 1: File Loading Fixes

1. **workflow.py line 54-59**: Was hardcoding `"profiles.yaml"` instead of using `channel_config.profiles_path` property
   - **Before**: `profiles_path = self.channel_config.channel_dir / "profiles.yaml"`
   - **After**: `profiles_path = self.channel_config.profiles_path`

2. **profiles.yaml location**: Moved from project root to channel directories
   - **Before**: `/profiles.yaml` (global, incorrect)
   - **After**: `/channels/wealth_wisdom/profiles.yaml` (per-channel, correct)

3. **channel.yaml profiles_path**: Updated to use relative paths correctly
   - **Value**: `profiles_path: "profiles.yaml"` (relative to channel dir)

### Session 2: Configuration Priority Fixes

4. **llm.py line 137**: Was using global `.env` content_type instead of channel config
   - **Before**: `content_type = content_type or settings.content_type`
   - **After**: Uses `channel_config.config.content.content_type` if available, falls back to settings only if no channel_config

5. **llm.py line 263**: Was using global `.env` art_style instead of channel config
   - **Before**: `art_style = art_style or settings.art_style`
   - **After**: Uses `channel_config.config.image.style` if available, falls back to settings only if no channel_config

6. **reddit.py line 56**: Added warning when using global `.env` subreddit fallback
   - **Before**: Silent fallback to `settings.subreddit`
   - **After**: Logs warning when no subreddit provided and falling back to .env

**Impact**: Fixes the critical bug where wealth_wisdom channel was generating content with momentum_mindset's configuration (motivational speech instead of financial advice, wrong art style, wrong subreddit)

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

### 1. Create Directory Structure

```bash
mkdir -p channels/new_channel/{assets,prompts,output}
```

### 2. Create channel.yaml

Copy from an existing channel and modify:
```bash
cp channels/momentum_mindset/channel.yaml channels/new_channel/channel.yaml
# Edit with your channel-specific settings
```

### 3. Create profiles.yaml

Copy and customize voice/music profiles:
```bash
cp channels/momentum_mindset/profiles.yaml channels/new_channel/profiles.yaml
# Edit with your channel-specific voices and music
```

### 4. (Optional) Add Custom Prompts

If you want custom content generation:
```bash
# Create prompts directory
mkdir channels/new_channel/prompts

# Add custom script prompt
echo "Your custom script prompt here..." > channels/new_channel/prompts/script.txt

# Add custom image prompt
echo "Your custom image style here..." > channels/new_channel/prompts/image.txt
```

### 5. Setup Google OAuth Credentials

**For each channel with a separate Google account:**

a. **Go to Google Cloud Console:**
   - Visit: https://console.cloud.google.com/
   - Sign in with the Google account that owns this YouTube channel

b. **Create a new project:**
   - Click "Select a project" → "New Project"
   - Name: "new-channel-youtube" (or similar)
   - Click "Create"

c. **Enable Required APIs:**
   - Go to "APIs & Services" → "Library"
   - Search and enable:
     - **YouTube Data API v3**
     - **Google Sheets API**

d. **Create OAuth 2.0 Credentials:**
   - Go to "APIs & Services" → "Credentials"
   - Click "Create Credentials" → "OAuth client ID"
   - If prompted, configure OAuth consent screen:
     - User Type: External
     - App name: "New Channel Content Factory"
     - User support email: your email
     - Developer contact: your email
     - Click "Save and Continue" through the scopes and test users
   - Back to Create OAuth client ID:
     - Application type: **Desktop app**
     - Name: "new_channel_oauth"
     - Click "Create"

e. **Download and Save Credentials:**
   - Click "Download JSON" on the created credential
   - Rename the downloaded file to `credentials.json`
   - Move to: `channels/new_channel/credentials.json`

   ```bash
   # Example on Windows
   move Downloads\client_secret_*.json channels\new_channel\credentials.json
   ```

### 6. First Authentication

```bash
# First run will open browser for OAuth authentication
python -m src.main update-stories --channel new_channel --limit 1

# After authenticating, token is saved automatically:
# channels/new_channel/token_youtube.json
```

### 7. Test Video Generation

```bash
python -m src.main generate --channel new_channel --count 1 --verbose
```

### Important Notes:

- **Each Google account = separate credentials.json** - You cannot reuse credentials between accounts (will get 403 error)
- **First run requires browser** - OAuth flow opens browser for authentication
- **Token auto-refreshes** - After initial auth, token_youtube.json handles refreshing
- **Gitignored** - Both credentials.json and token_youtube.json are in .gitignore for security

## Best Practices

1. **Separate profiles per channel**: Each channel should have distinct voice/music to differentiate content
2. **Custom prompts for unique tones**: Use `prompts/script.txt` for channel-specific content styles (e.g., "humble brag" for finance)
3. **Channel-specific credentials**: Keep YouTube accounts separate for better scaling and risk management
4. **Version control**: Add `credentials.json` and `token_youtube.json` to `.gitignore`
5. **Output isolation**: Each channel's videos stay in its own output directory
