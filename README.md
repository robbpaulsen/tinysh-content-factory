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

### TTS Configuration

```bash
# Kokoro (fast, good quality)
TTS_ENGINE=kokoro
KOKORO_VOICE=af_bella
KOKORO_SPEED=1.0

# OR Chatterbox (voice cloning, slower)
TTS_ENGINE=chatterbox
CHATTERBOX_VOICE_SAMPLE_ID=your-file-id  # Optional for voice cloning
```

### Image Generation

```bash
FLUX_MODEL=black-forest-labs/FLUX.1-schnell-Free
IMAGE_WIDTH=768
IMAGE_HEIGHT=1344
```

### Background Music (Optional)

```bash
BACKGROUND_MUSIC_ID=your-file-id
BACKGROUND_MUSIC_VOLUME=0.2
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
│       └── youtube.py      # YouTube upload
├── workflow_youtube_shorts/
│   └── workflow_motivational_shorts.json  # Original n8n workflow (reference)
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

### 3. Media Generation (Per Scene)

- **Image**: FLUX generates cinematic image
- **TTS**: Local server creates voiceover
- **Video**: Combines image + TTS + captions

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
