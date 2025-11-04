# Changelog

All notable changes to the YouTube Shorts Factory migration project.

## [Unreleased] - 2025-11-03

### Migration Progress: ~85% Complete

#### ✅ Completed

##### Project Setup
- Created Python project structure with `uv` package manager
- Implemented modular service architecture
- Added CLI interface with Click
- Configured Pydantic settings with environment variables
- Set up comprehensive logging

##### Services Implemented
1. **Reddit Service** (`src/services/reddit.py`)
   - ✅ Uses public JSON endpoints (no API authentication)
   - ✅ Fetches top stories from subreddit
   - ✅ Filters by content type and length
   - Status: **Working**

2. **Google Sheets Service** (`src/services/sheets.py`)
   - ✅ OAuth2 authentication
   - ✅ Read stories from spreadsheet
   - ✅ Write stories to spreadsheet
   - ✅ Update video_id column
   - ✅ Safe by default (no auto-updates unless --update flag)
   - Status: **Working**

3. **LLM Service** (`src/services/llm.py`)
   - ✅ Integrated Google Gemini 2.0 Flash (stable)
   - ✅ Async wrapper for sync Gemini SDK
   - ✅ Generates motivational speeches from stories
   - ✅ Creates video scripts with scenes
   - ✅ Generates image prompts per scene
   - ✅ Cleans <think> tags from output
   - Status: **Working**

4. **Media Service** (`src/services/media.py`)
   - ✅ Together.ai FLUX integration for image generation
   - ✅ Rate limiting (6 images/min for FLUX Free tier)
   - ✅ Fixed image upload endpoint to media server
   - ⚠️ TTS integration (Kokoro/Chatterbox) - **IN PROGRESS**
   - ⏳ Video generation with captions - **UNTESTED**
   - ⏳ Video merging with background music - **UNTESTED**
   - Status: **Partially Working**

5. **YouTube Service** (`src/services/youtube.py`)
   - ✅ OAuth2 authentication
   - ✅ Video upload functionality
   - ⚠️ Disabled by default per user request
   - Status: **Working (Disabled)**

6. **Workflow Orchestrator** (`src/workflow.py`)
   - ✅ Complete pipeline implementation
   - ✅ Progress indicators with Rich
   - ✅ Downloads videos to ./output/ directory
   - ✅ Error handling and logging
   - Status: **Working (Pending Media Service fixes)**

##### API Fixes
- ✅ Reddit: Removed PRAW dependency, using httpx with public endpoints
- ✅ Together.ai FLUX: Removed unsupported "n" parameter, updated to 768x1344 dimensions
- ✅ Media Server: Fixed image upload endpoint from `/upload-from-url` to `/storage` with multipart/form-data
- ⚠️ Media Server TTS: Discovered endpoints return `file_id` directly (not async `task_id`)

##### Configuration
- ✅ Gemini model updated to `gemini-2.0-flash` (from deprecated 1.5)
- ✅ Image dimensions set to 768x1344 (official FLUX recommendations)
- ✅ TTS engine configurable (Kokoro/Chatterbox)
- ✅ YouTube upload disabled by default
- ✅ Rate limiting enabled for FLUX API

#### 🚧 In Progress

##### Media Service TTS Integration
**Current Issue**: TTS endpoint behavior differs from expected async pattern

**Expected Behavior**:
```python
# POST returns task_id, then poll for completion
response = post("/api/v1/tts/chatterbox", json={...})
task_id = response["task_id"]
# Poll until ready...
```

**Actual Behavior**:
```python
# POST returns file_id directly (synchronous)
response = post("/api/v1/media/audio-tools/tts/chatterbox", data={...})
file_id = response["file_id"]  # Ready immediately
```

**Changes Made**:
1. Updated endpoints:
   - Kokoro: `/api/v1/media/audio-tools/tts/kokoro`
   - Chatterbox: `/api/v1/media/audio-tools/tts/chatterbox`
2. Changed request format from `json=` to `data=` (multipart/form-data)
3. Renamed method to `generate_tts_direct()` to reflect synchronous behavior
4. Removed polling logic from `generate_tts()`

**Still Failing**: Getting 404 errors despite endpoints existing in OpenAPI spec
- Manual curl tests work correctly
- Python httpx client fails with 404
- Possible issue: URL encoding, httpx client configuration, or headers

**Next Steps**:
1. Debug httpx request vs curl request differences
2. Check if base_url has trailing issues
3. Verify httpx timeout/follow_redirects settings
4. Test with explicit headers matching curl

#### ❌ Not Yet Tested

- Video generation with captions endpoint
- Video merging functionality
- Background music integration
- File cleanup operations
- Complete end-to-end workflow

#### 📋 Known Issues

1. **TTS Endpoint 404 Error** (Priority: HIGH)
   - Location: `src/services/media.py:185`
   - Error: `Client error '404 Not Found' for url 'http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox'`
   - Curl works, httpx fails
   - Blocking video generation

2. **Video Generation Untested** (Priority: MEDIUM)
   - Endpoint: `/api/v1/video/captioned` or similar (needs verification)
   - May have similar issues as TTS endpoints

3. **Video Merging Untested** (Priority: MEDIUM)
   - Endpoint: `/api/v1/video/merge` or similar (needs verification)
   - May have similar issues as TTS endpoints

### Dependencies

#### Core
- python = ">=3.11"
- httpx = ">=0.27.0"
- pydantic = ">=2.0.0"
- pydantic-settings = ">=2.0.0"
- google-generativeai = ">=0.3.0"
- google-auth = ">=2.23.0"
- google-auth-oauthlib = ">=1.1.0"
- google-api-python-client = ">=2.100.0"
- tenacity = ">=8.2.0"
- click = ">=8.1.0"
- rich = ">=13.0.0"
- aiolimiter = ">=1.1.0"

#### Removed
- ❌ praw (Reddit API - replaced with httpx public endpoints)

### Configuration Changes

#### .env.example Updates
```bash
# Removed:
REDDIT_CLIENT_ID
REDDIT_CLIENT_SECRET
REDDIT_USER_AGENT

# Updated:
IMAGE_WIDTH=768  # Was 720
IMAGE_HEIGHT=1344  # Was 1280

# Added comment:
# Reddit (uses public JSON endpoints - no API keys required)
```

#### config.py Updates
```python
# Removed Reddit credentials fields
# Updated default dimensions
# Added TTS engine selection
# Added Chatterbox parameters
```

### API Endpoint Documentation

#### Working Endpoints
```
GET  /health
POST /api/v1/media/storage (multipart/form-data)
  - url: string
  - media_type: "image" | "video" | "audio"
  → Returns: {file_id: string}

POST https://api.together.xyz/v1/images/generations
  - model: string
  - prompt: string
  - width: int
  - height: int
  - steps: int
  → Returns: {data: [{url: string}]}
```

#### Problematic Endpoints
```
POST /api/v1/media/audio-tools/tts/kokoro (multipart/form-data)
  - text: string
  - voice: string (optional)
  - speed: float (optional)
  → Expected: {file_id: string}
  → Status: 404 via httpx (works via curl)

POST /api/v1/media/audio-tools/tts/chatterbox (multipart/form-data)
  - text: string
  - exaggeration: float (optional)
  - cfg_weight: float (optional)
  - temperature: float (optional)
  - sample_audio_id: string (optional)
  → Expected: {file_id: string}
  → Status: 404 via httpx (works via curl)
```

#### Untested Endpoints
```
POST /api/v1/video/captioned
  - image_id: string
  - audio_id: string
  - text: string
  → Expected: {task_id: string} or {file_id: string}

POST /api/v1/video/merge
  - video_ids: list[string]
  - background_music_id: string (optional)
  - music_volume: float (optional)
  → Expected: {task_id: string} or {file_id: string}

GET /api/v1/tasks/{task_id}/status
  → Expected: {status: string, file_id?: string, error?: string}
```

### Testing Notes

#### Successful Tests
- ✅ Reddit story fetching
- ✅ Google Sheets read/write
- ✅ Gemini speech generation
- ✅ Gemini script creation
- ✅ FLUX image generation
- ✅ Image upload to media server

#### Failed Tests
- ❌ TTS generation (endpoint 404)

#### Pending Tests
- ⏳ Video generation
- ⏳ Video merging
- ⏳ Complete workflow
- ⏳ YouTube upload

### Migration from n8n

#### Advantages Achieved
- ✅ Type safety with Pydantic
- ✅ Better error handling
- ✅ Async/await performance
- ✅ Clean code structure
- ✅ Version control friendly
- ✅ IDE support

#### Challenges Encountered
1. API endpoint discrepancies between documentation and implementation
2. Sync/async model differences (Gemini SDK is sync)
3. Media server API behavior different from n8n expectations
4. httpx vs curl behavior differences

### Next Session Tasks

See TODO.md for detailed task breakdown.
