# YouTube Shorts Factory

Automated YouTube Shorts generation from Reddit stories using AI. Transform stories into engaging videos with generated images, voiceovers, captions, and background music.

**Now with Multi-Channel Support!** Manage multiple YouTube channels from a single application with independent configurations, profiles, and credentials.

## Features

- 🤖 **AI-Powered Content**: Uses Google Gemini to create motivational speeches from Reddit stories
- 🎨 **Image Generation**: FLUX (via Together.ai) creates cinematic images for each scene
- 🗣️ **Text-to-Speech**: Local TTS using Kokoro or Chatterbox with voice cloning
- 🎬 **Video Processing**: Automatic captioning, merging, and background music
- 📊 **Google Sheets Integration**: Store and manage stories
- 📤 **YouTube Upload**: 2-phase upload/schedule system with smart gap filling
- 📺 **Multi-Channel System**: Manage 3+ YouTube channels independently
- 🎯 **Channel Types**: AI-generated shorts, AI-generated videos, YouTube compilations
- 🔄 **Complete Pipeline**: Reddit → AI → Video → YouTube

## Architecture

This project replaces the original n8n workflow with a clean Python implementation:

```
Reddit Stories → Google Sheets → Gemini (script) → Loop per scene:
  ├─ FLUX (image generation)
  ├─ Kokoro/Chatterbox (TTS)
  └─ Local server (video + captions)
→ Merge all videos → Add music → Upload to YouTube
```

## Prerequisites

### Execution Modes

The system supports **two execution modes**:

#### 🚀 **Local Mode (NEW)** - Recommended
- ✅ No Docker required
- ✅ Direct Python execution (faster)
- ✅ GPU acceleration (NVENC for video encoding)
- ✅ Better debugging and control
- ✅ Automatic model downloading

**Requirements:**
- Python 3.11+
- FFmpeg installed
- TTS models auto-download on first use
- 8GB+ RAM, NVIDIA GPU recommended

#### 🐳 **Remote Mode** - Legacy (Docker)
- Uses HTTP API to communicate with Docker media server
- Requires media server running on `http://localhost:8000`
- Useful for distributed setups

### Required Services

**API Keys:**
- Google Gemini API key
- Together.ai API key
- Google OAuth credentials (for Sheets & YouTube)
- Reddit (no API keys needed - uses public endpoints)

### System Requirements

**For Local Mode (recommended):**
- Python 3.11+
- `uv` package manager
- FFmpeg (command-line tool)
- 8GB+ RAM
- NVIDIA GPU recommended (for NVENC encoding)
- TTS models: Auto-downloaded on first use (1-2GB)

**For Remote Mode (legacy):**
- All of the above, plus:
- Docker with media server container
- Media server running on port 8000

## Installation

### 1. Install uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Clone and Setup

```bash
git clone <your-repo>
cd n8n-to-python-transpiler

# Initialize project with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Install pip module (required for some dependencies)
uv pip install pip
```

### 2.1 Install FFmpeg (Required for Local Mode)

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt-get install ffmpeg  # Debian/Ubuntu
sudo yum install ffmpeg      # RHEL/CentOS
```

### 3. Configuration

```bash
# Create .env file
python -m src.main init

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

### 4. Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing)
3. Enable APIs:
   - Google Sheets API
   - YouTube Data API v3
4. Create OAuth 2.0 credentials (Desktop app)
5. Download `credentials.json` and place in `.credentials/` directory

### 5. API Keys

- **Gemini**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Together.ai**: Sign up at [Together.ai](https://together.ai/)

## Multi-Channel System

The system supports managing **multiple YouTube channels** from a single application. Each channel has independent configuration, credentials, output directory, and scheduling.

### Channel Structure

```
channels/
├── momentum_mindset/           # Channel 1: Motivational shorts
│   ├── channel.yaml           # Channel configuration
│   ├── profiles.yaml          # Voice/music profiles (optional)
│   ├── credentials.json       # YouTube OAuth credentials
│   ├── token_youtube.json     # OAuth token (auto-generated)
│   ├── assets/                # Channel-specific assets
│   └── output/                # Generated videos
│       ├── video_001.mp4
│       ├── video_001_metadata.json
│       └── video_ids.csv
│
├── wealth_wisdom/             # Channel 2: Finance shorts
│   └── ...
│
└── finance_wins/              # Channel 3: Finance compilations
    └── ...
```

### Channel Types

1. **`ai_generated_shorts`** - AI-generated short videos (9:16 aspect ratio)
   - Reddit → Gemini → FLUX → TTS → FFmpeg
   - Perfect for motivational, educational, story content
   - 15-60 seconds duration

2. **`ai_generated_videos`** - AI-generated longer videos (16:9 aspect ratio)
   - Same pipeline as shorts but longer format
   - 3-10 minutes duration
   - More detailed content

3. **`youtube_compilation`** - Compilation videos from YouTube clips
   - Downloads clips using yt-dlp
   - Compiles with FFmpeg
   - Perfect for curated content, compilations
   - Zero AI generation costs

### Channel Configuration Example

Each channel has a `channel.yaml` file:

```yaml
name: "Momentum Mindset"
description: "Daily motivation and self-improvement"
handle: "@MomentumMindset"
channel_type: "ai_generated_shorts"

content:
  format: "shorts"
  duration_range: [15, 45]
  subreddit: "selfimprovement"
  topics:
    - self improvement
    - motivation
    - productivity

video:
  aspect_ratio: "9:16"
  width: 768
  height: 1344

youtube:
  category_id: "22"  # People & Blogs
  schedule:
    videos_per_day: 6
    start_hour: 6     # 6 AM
    end_hour: 16      # 4 PM
    interval_hours: 2 # Every 2 hours

seo:
  target_keywords:
    - motivation
    - self improvement
  default_tags:
    - shorts
    - motivation

default_profile: "frank_motivational"
```

### List Available Channels

```bash
python -m src.main list-channels
```

Output:
```
📺 Available Channels

┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Channel          ┃ Name            ┃ Type                ┃ Handle            ┃ Format         ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ momentum_mindset │ Momentum...     │ Ai Generated Shorts │ @MomentumMindset  │ 9:16 (shorts)  │
│ wealth_wisdom    │ Wealth Wisdom   │ Ai Generated Shorts │ @WealthWisdom     │ 9:16 (shorts)  │
│ finance_wins     │ Finance Wins    │ Youtube Compilation │ @FinanceWins      │ 16:9 (compila..│
└──────────────────┴─────────────────┴─────────────────────┴───────────────────┴────────────────┘
```

### OAuth Setup for Multiple Channels

You have **two options** for YouTube authentication:

#### Option A: Different YouTube Accounts (Recommended)
- Each channel uses a separate YouTube account
- Complete independence
- Better for scaling

1. Create/use 3 different Google accounts
2. Create OAuth credentials for each account
3. Place `credentials.json` in each channel directory:
   ```
   channels/momentum_mindset/credentials.json
   channels/wealth_wisdom/credentials.json
   channels/finance_wins/credentials.json
   ```
4. First time you run a command for a channel, it will open OAuth flow
5. Token is saved in the same directory automatically

**⚠️ Important Note on Authentication:**
The system now forces the consent screen (`prompt="consent"`) to prevent cross-account issues. You may be prompted twice:
1. **Google Sheets**: Select your main account (asks for Spreadsheet permissions).
2. **YouTube**: Select the specific account for that channel (asks for YouTube permissions).
Always check which permission is being requested before selecting the account!

#### Option B: Same YouTube Account
- All channels under one Google account
- Uses playlists or brand channels
- Simpler setup but less flexible

Same process, but use the same `credentials.json` for all channels.

### Working with Channels

All CLI commands now support `--channel` flag:

```bash
# Generate videos for specific channel
python -m src.main generate --channel momentum_mindset --count 6

# Upload videos for specific channel
python -m src.main batch-upload --channel wealth_wisdom --limit 10

# Schedule videos for specific channel
python -m src.main batch-schedule --channel finance_wins

# If you don't specify --channel, it uses the first available channel
python -m src.main generate --count 1
# → Auto-selects momentum_mindset (first alphabetically)
```

### Batch Process All Channels

Process all channels automatically in sequence:

```bash
# Generate 3 videos for each AI channel
python -m src.main batch-all --count 3

# Generate and update Reddit stories first
python -m src.main batch-all --count 5 --update
```

Output shows progress for each channel with summary table at the end.

### Smart Scheduling

Each channel has independent scheduling configuration. The scheduler:
- ✅ Checks existing scheduled videos on YouTube
- ✅ Fills gaps in the schedule based on channel config
- ✅ Never schedules at the same time
- ✅ Respects channel-specific hours (e.g., 6 AM - 4 PM)

Example workflow:
```bash
# 1. Generate videos
python -m src.main generate --channel momentum_mindset --count 6

# 2. Upload to YouTube (Phase 1)
python -m src.main batch-upload --channel momentum_mindset

# 3. Schedule with optimal times (Phase 2)
python -m src.main batch-schedule --channel momentum_mindset

# Check YouTube Studio - videos are scheduled!
```

### Benefits of Multi-Channel

- ✅ **Diversification**: Different niches, different audiences
- ✅ **Risk Management**: Not all eggs in one basket
- ✅ **A/B Testing**: Compare performance across channels
- ✅ **Revenue Optimization**: Target high-CPM niches (finance $8-15 CPM vs general $2-5)
- ✅ **Automation**: One command processes all channels
- ✅ **Independence**: Separate credentials, configs, schedules

For detailed multi-channel documentation, see `.github/MULTI_CHANNEL_SYSTEM.md`.

## Usage

### Validate Configuration

```bash
python -m src.main validate-config
```

### Check System Configuration

```bash
# Check if running in local or remote mode
python -m src.main check-server

# Test local mode functionality
python tests/test_integration_simple.py  # Quick initialization test
python tests/test_integration.py         # Full TTS test
python tests/test_video_local.py         # Video generation test
```

### List All Channels

```bash
python -m src.main list-channels
```

### Update Stories from Reddit

```bash
# Fetch stories using channel config subreddit
python -m src.main update-stories

# Custom subreddit and limit
python -m src.main update-stories --subreddit getdisciplined --limit 50
```

### Generate Videos

**Single Channel:**
```bash
# Generate 1 video for specific channel
python -m src.main generate --channel momentum_mindset --count 1

# Generate 3 videos and update stories first
python -m src.main generate --channel wealth_wisdom --count 3 --update

# Use specific voice profile
python -m src.main generate --channel momentum_mindset --count 1 --profile brody_calm
```

**All Channels (Batch):**
```bash
# Generate 3 videos for each AI channel automatically
python -m src.main batch-all --count 3

# Generate and update Reddit stories first
python -m src.main batch-all --count 5 --update
```

### Upload Videos to YouTube

**Phase 1: Upload as Private**
```bash
# Upload videos for a channel (max 20/day due to API limits)
python -m src.main batch-upload --channel momentum_mindset

# Upload only 5 videos
python -m src.main batch-upload --channel wealth_wisdom --limit 5
```

**Phase 2: Schedule with Metadata**
```bash
# Preview schedule first (dry run)
python -m src.main batch-schedule --channel momentum_mindset --dry-run

# Schedule videos with optimal times
python -m src.main batch-schedule --channel momentum_mindset
```

### Generate from Single Story

```bash
# Use Reddit post ID
python -m src.main generate-single abc123xyz

# With specific channel
python -m src.main generate-single abc123xyz --channel momentum_mindset
```

## Execution Mode Configuration

### Switching Between Local and Remote Mode

The system automatically uses **Local Mode** by default. To switch modes, configure in your `.env`:

```bash
# Local Mode (default) - No Docker required
MEDIA_EXECUTION_MODE=local

# Remote Mode - Requires Docker media server
MEDIA_EXECUTION_MODE=remote
MEDIA_SERVER_URL=http://localhost:8000
```

### Local Mode Benefits

**Performance:**
- ✅ **5-10x faster** video encoding with GPU (NVENC)
- ✅ **No HTTP overhead** - Direct function calls
- ✅ **Better progress tracking** - Real-time FFmpeg output

**Development:**
- ✅ **Easier debugging** - Stack traces show full context
- ✅ **No container management** - One less thing to maintain
- ✅ **Hot reloading** - Code changes apply immediately

**Cost:**
- ✅ **Zero infrastructure** - No Docker, no containers
- ✅ **Uses local GPU** - Free NVENC encoding

### When to Use Remote Mode

Use Remote Mode if you:
- Already have a media server running
- Need distributed processing across machines
- Want to offload heavy processing to a dedicated server
- Have existing Docker infrastructure

## Configuration Options

Key settings in `.env`:

### Content Generation

```bash
SUBREDDIT=selfimprovement
CONTENT_TYPE="motivational speech"
ART_STYLE="Create a cinematic image..."  # Full prompt in .env.example
```

### Voice & Music Profiles

The system uses **profiles** to manage voice and music configurations, defined in `config/profiles.yaml`:

```bash
# Optional: Override default profile from config/profiles.yaml
ACTIVE_PROFILE=frank_motivational

# Optional: Path to profiles configuration
PROFILES_PATH=config/profiles.yaml
```

**Profile Configuration (`config/profiles.yaml`):**

Each profile includes:
- **Voice settings**: TTS engine (Kokoro/Chatterbox), voice samples, parameters
- **Music playlist**: Multiple tracks with rotation (random/sequential)
- **Volume settings**: Per-profile music volume

Example profile structure:

```yaml
profiles:
  frank_motivational:
    name: "Frank - Motivational"
    description: "Energetic, inspiring tone"
    voice:
      engine: chatterbox
      sample_path: "D:/Music/voces/frank/sample.mp3"
      temperature: 0.7
      cfg_weight: 0.65
      exaggeration: 0.55
    music:
      playlist:
        - path: "D:/Music/tracks/track1.mp3"
          name: "Track Name"
      volume: 0.1
      rotation: random  # or sequential

default_profile: frank_motivational
```

**Using Profiles via CLI:**

```bash
# Use default profile
python -m src.main generate --count 1

# Use specific profile
python -m src.main generate --count 1 --profile brody_calm

# Generate single story with profile
python -m src.main generate-single abc123 --profile denzel_powerful
```

**Benefits:**
- ✅ Easy switching between voice styles
- ✅ Music rotation (avoid repetition)
- ✅ Multiple profiles for different content types
- ✅ Path validation for voice samples and music files

### Image Generation

```bash
FLUX_MODEL=black-forest-labs/FLUX.1-schnell-Free
IMAGE_WIDTH=768
IMAGE_HEIGHT=1344
```


### Performance Optimization

```bash
# FFmpeg encoder settings (configured on media server)
FFMPEG_ENCODER=auto     # Options: auto, nvenc (GPU), x264 (CPU)
FFMPEG_PRESET=p4        # NVENC: p1-p7, x264: ultrafast/fast/medium
FFMPEG_CQ=23            # Quality: 18=best, 28=worst
FFMPEG_BITRATE=5M       # Target bitrate for videos
FFMPEG_AUDIO_BITRATE=128k
```

**Performance Results:**
- ⚡ **GPU Encoding (NVENC)**: 5-10x faster than CPU encoding with NVIDIA GPU
- ⚡ **Sequential Mode**: ~3 minutes per video (model stays loaded)
- ⚡ **Individual Mode**: 5-7 minutes (model loads/unloads each time)
- ⚡ **Token-Optimized Prompts**: 15-45 second videos (480-1440 tokens)

### SEO Optimization

The system automatically generates SEO-optimized YouTube metadata using Google Gemini:

```bash
# Enable/disable SEO metadata generation (default: enabled)
SEO_ENABLED=true
```

**What it generates:**
- 📝 **Optimized Titles**: 50-60 characters, clickable, keyword-rich
- 📋 **Smart Descriptions**: Strategic keywords, hashtags, CTAs
- 🏷️ **Relevant Tags**: 10-15 tags per video for discoverability
- 🎯 **Category Selection**: Automatic YouTube category assignment
- 🎨 **Profile-Aware**: Adapts to your active voice/music profile

**Output:**

Each video generates two files:
```
output/
├── video_001.mp4              # Generated video
└── video_001_metadata.json    # SEO metadata
```

**Metadata JSON format:**
```json
{
  "title": "5 Habits That Changed My Life Forever",
  "description": "Discover powerful habits...\n\n#motivation #shorts #selfimprovement",
  "tags": ["motivation", "self improvement", "productivity", ...],
  "category_id": "22",
  "original_title": "Transform Your Life",
  "original_description": "A story about...",
  "profile": "frank_motivational"
}
```

**Benefits:**
- ✅ Saves time: No manual title/description writing
- ✅ Consistency: Professional metadata for every video
- ✅ Discoverability: Optimized for YouTube search and recommendations
- ✅ Scalable: Ready for multi-channel workflows

**To disable SEO optimization:**
```bash
# In .env
SEO_ENABLED=false
```

### Logging System

The application includes a comprehensive logging system with two modes:

**Simple Mode (default)**:
```bash
# Normal operation with progress bars
python -m src.main generate --count 1
```
- INFO level logging
- Console output only
- Progress bars and status updates
- Clean, minimal output

**Verbose Mode**:
```bash
# Detailed debugging with file logs
python -m src.main --verbose generate --count 1

# Or using short flag
python -m src.main -v generate --count 1
```
- DEBUG level logging
- Console + file output
- Detailed operation timing
- API call tracking
- Full stack traces on errors

**Log Files**:

When enabled, logs are saved to `output/logs/`:
```
output/logs/
├── youtube_shorts_20250107_153045.log
├── youtube_shorts_20250107_160212.log
└── ...
```

**Features**:
- 📝 **Automatic Rotation**: 10MB max per file, keeps 5 backups
- 🗑️ **Auto Cleanup**: Removes logs older than 7 days (configurable)
- ⏱️ **Performance Metrics**: Times every major operation
- 🔍 **API Tracking**: Logs all Gemini/Together.ai/Media server calls
- 📊 **Per-Scene Breakdown**: Detailed timing for each video scene

**Configuration**:
```bash
# In .env

# Enable/disable file logging
LOG_TO_FILE=true

# Log directory
LOG_DIR=output/logs

# Log retention (1-30 days)
LOG_MAX_AGE_DAYS=7
```

**Example Verbose Output**:
```
[LLM script generation] Completed in 5.23s
[Scene 1 - Image generation] Completed in 6.45s
[Scene 1 - TTS generation] Completed in 18.32s
[Scene 1 - Video generation] Completed in 2.11s
...
[Video merge with music] Completed in 1.05s
[Generate video: Transform Your Life] Completed in 182.45s
```

**Use Cases**:
- ✅ **Debugging**: Use verbose mode when something fails
- ✅ **Performance Tuning**: Identify bottlenecks in your workflow
- ✅ **Production Runs**: Use simple mode for clean output
- ✅ **Multi-Channel**: Separate logs help track different channel generations

## Project Structure

```
youtube-shorts-factory/
├── src/
│   ├── main.py                 # CLI entry point with multi-channel commands
│   ├── config.py               # Configuration management
│   ├── models.py               # Data models
│   ├── workflow.py             # Main orchestrator (channel-aware)
│   ├── channel_config.py       # Channel configuration loader
│   └── services/
│       ├── reddit.py           # Reddit scraping
│       ├── sheets.py           # Google Sheets
│       ├── llm.py              # Gemini LLM
│       ├── media.py            # Media server client
│       ├── youtube.py          # YouTube upload (multi-channel support)
│       ├── youtube_downloader.py  # YouTube video downloader (yt-dlp)
│       ├── video_compiler.py   # Video compilation (FFmpeg)
│       ├── scheduler.py        # Smart video scheduling
│       ├── seo_optimizer.py    # SEO metadata generation
│       └── profile_manager.py  # Voice/music profiles
│
├── channels/                   # Multi-channel system
│   ├── momentum_mindset/      # Channel 1
│   │   ├── channel.yaml       # Channel configuration
│   │   ├── profiles.yaml      # Voice/music profiles (optional)
│   │   ├── credentials.json   # YouTube OAuth (gitignored)
│   │   ├── token_youtube.json # OAuth token (gitignored)
│   │   ├── assets/            # Channel assets
│   │   └── output/            # Generated videos
│   ├── wealth_wisdom/         # Channel 2
│   └── finance_wins/          # Channel 3
│
├── .github/
│   └── MULTI_CHANNEL_SYSTEM.md  # Multi-channel documentation
│
├── docs/legacy/workflow_youtube_shorts/  # Original n8n workflow
│
├── config/
│   └── profiles.yaml          # Global voice & music profiles
│
├── pyproject.toml             # Dependencies
├── .env.example               # Environment template
└── README.md
```

## Workflow Details

### 1. Reddit Scraping

- Uses public JSON endpoints (no API authentication required)
- Fetches top posts from specified subreddit
- Filters by content length and type
- Saves to Google Sheets

### 2. Content Generation (Gemini)

- Creates motivational speech from story
- Splits into 5-8 scenes
- Generates image prompts for each scene

### 3. Media Generation

**Sequential Processing:**
- **Images**: Generated one at a time (Together.ai FLUX-Free requirement)
- **TTS**: Profile-based voice configuration from `config/profiles.yaml`
- **Videos**: Generated with captions as each TTS completes
- **Music**: Selected from profile playlist (random or sequential rotation)

### 4. Video Assembly

- Merges all scene videos
- Adds background music (optional)
- Applies transitions

### 5. YouTube Upload

- Downloads final video
- Uploads with metadata
- Updates Google Sheets

### 6. Cleanup

- Deletes temporary files from media server

## Advantages Over n8n

✅ **Type Safety**: Full type hints and Pydantic validation
✅ **Error Handling**: Robust retry logic with tenacity
✅ **Async Performance**: Concurrent processing where possible
✅ **Testing**: Easy to unit test individual services
✅ **Customization**: Direct SDK access for fine-tuning
✅ **Versioning**: Git-friendly Python code
✅ **Debugging**: Better logging and error messages
✅ **IDE Support**: Autocomplete and refactoring
✅ **Performance**: GPU encoding support, optimized prompts
✅ **Profile System**: Easy voice/music management with YAML configuration

## Troubleshooting

### Execution Mode Issues

**Local Mode (Default):**
```bash
# Verify FFmpeg is installed
ffmpeg -version

# Check GPU availability (NVIDIA)
nvidia-smi

# Test TTS generation
python tests/test_integration.py

# Test video generation
python tests/test_video_local.py
```

**Common Issues:**
- **"No module named pip"**: Run `uv pip install pip`
- **FFmpeg not found**: Install FFmpeg and add to PATH
- **Models downloading slowly**: First run downloads 1-2GB (one-time)
- **GPU not detected**: System falls back to CPU automatically

**Remote Mode (Docker):**
```bash
# Check if server is running
python -m src.main check-server

# Check Docker container logs
docker logs media-server
```

### Google OAuth Errors

- Delete `token.json` and `token_youtube.json`
- Run the workflow again to re-authenticate
- Ensure .credentials/credentials.json is valid

### Rate Limits

- Together.ai: Free tier has limits, retries handled automatically
- Reddit: Public endpoints have rate limits (respectful delays recommended)
- YouTube: Daily upload quota (varies by account)

### TTS/Video Generation Timeouts

- Increase `MEDIA_PROCESSING_TIMEOUT` in .env
- Check media server resources (CPU/RAM/GPU)
- Try shorter scenes if timeout persists

## Development

### Run with uv

```bash
uv run python -m src.main --help
```

### Install dev dependencies

```bash
uv pip install -e ".[dev]"
```

### Code formatting

```bash
ruff check src/
ruff format src/
```

## Contributing

This is a personal project migrated from n8n. Feel free to fork and adapt to your needs, and if you do so,
don't you F!!!!kng dare to sell it. Give back to the community and you shall always find what you need.

## License

See LICENSE file.

## Credits

- Original n8n workflow, concept and project was/is from "ai agents az" and even though this developer actually DELETED the FOSS version project out of nowhere and now just sells the workflow on the well known `skool.com` where you can buy N8N workflows to backup your N8N nodes straight to github and YES with plain text json credentials included 🤣🤣🤣🤣.
- Uses: Gemini, FLUX, Kokoro, Chatterbox, FFmpeg, Together.ai
- Built with: Python, uv, httpx, pydantic, rich and a LOT! ... A LOT !!!!!! of DEBUGGING. This thing is very fragile like a dandelion on the middle of florida.
- Resemble.ai/Chatterbox even though the actual python multilingual chatterbox documentation is the size of 10 sentences, the model is actually very very good. Even though the only way to make it to work is with python 3.10 and removing all torch ecosystem like 10 times, when it builds it's pure magic.

---

**Note**: This project requires a local media processing server. See the original n8n workflow for server setup details.
