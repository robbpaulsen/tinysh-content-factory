# YouTube Shorts Factory

Automated YouTube Shorts generation from Reddit stories using AI. Transform stories into engaging videos with generated images, voiceovers, captions, and background music.

## Features

- 🤖 **AI-Powered Content**: Uses Google Gemini to create motivational speeches from Reddit stories
- 🎨 **Image Generation**: FLUX (via Together.ai) creates cinematic images for each scene
- 🗣️ **Text-to-Speech**: Local TTS using Kokoro or Chatterbox with voice cloning
- 🎬 **Video Processing**: Automatic captioning, merging, and background music
- 📊 **Google Sheets Integration**: Store and manage stories
- 📤 **YouTube Upload**: Automatic upload with metadata
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

### Required Services

1. **Local Media Server**: Running on `http://localhost:8000` (or configure your own)
   - Handles TTS generation (Kokoro/Chatterbox)
   - Video processing with FFmpeg
   - Caption generation
   - File storage

2. **API Keys**:
   - Google Gemini API key
   - Together.ai API key
   - Google OAuth credentials (for Sheets & YouTube)
   - Reddit (no API keys needed - uses public endpoints)

### System Requirements

- Python 3.11+
- `uv` package manager
- Media server with:
  - FFmpeg
  - Kokoro TTS or Chatterbox TTS
  - 4+ CPU cores, 8GB+ RAM recommended

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
5. Download `credentials.json` and place in project root

### 5. API Keys

- **Gemini**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- **Together.ai**: Sign up at [Together.ai](https://together.ai/)

## Usage

### Validate Configuration

```bash
python -m src.main validate-config
```

### Check Media Server

```bash
python -m src.main check-server
```

### Update Stories from Reddit

```bash
# Fetch 25 stories from configured subreddit
python -m src.main update-stories

# Custom subreddit and limit
python -m src.main update-stories --subreddit getdisciplined --limit 50
```

### Generate Videos

```bash
# Generate 1 video from Google Sheets
python -m src.main generate --count 1

# Generate 3 videos and update stories first
python -m src.main generate --count 3 --update
```

### Generate from Single Story

```bash
# Use Reddit post ID
python -m src.main generate-single abc123xyz
```

## Configuration Options

Key settings in `.env`:

### Content Generation

```bash
SUBREDDIT=selfimprovement
CONTENT_TYPE="motivational speech"
ART_STYLE="Create a cinematic image..."  # Full prompt in .env.example
```

### Voice & Music Profiles

The system uses **profiles** to manage voice and music configurations, defined in `profiles.yaml`:

```bash
# Optional: Override default profile from profiles.yaml
ACTIVE_PROFILE=frank_motivational

# Optional: Path to profiles configuration
PROFILES_PATH=profiles.yaml
```

**Profile Configuration (`profiles.yaml`):**

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

## Project Structure

```
youtube-shorts-factory/
├── src/
│   ├── main.py              # CLI entry point
│   ├── config.py            # Configuration management
│   ├── models.py            # Data models
│   ├── workflow.py          # Main orchestrator
│   └── services/
│       ├── reddit.py        # Reddit scraping
│       ├── sheets.py        # Google Sheets
│       ├── llm.py          # Gemini LLM
│       ├── media.py        # Media server client
│       ├── youtube.py      # YouTube upload
│       └── profile_manager.py  # Voice/music profiles
├── workflow_youtube_shorts/
│   └── workflow_motivational_shorts.json  # Original n8n workflow (reference)
├── profiles.yaml           # Voice & music profiles
├── pyproject.toml          # Dependencies
├── .env.example            # Environment template
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
- **TTS**: Profile-based voice configuration from `profiles.yaml`
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

### Media Server Issues

```bash
# Check if server is running
python -m src.main check-server

# Check server logs
# (depends on your media server setup)
```

### Google OAuth Errors

- Delete `token.json` and `token_youtube.json`
- Run the workflow again to re-authenticate
- Ensure credentials.json is valid

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
