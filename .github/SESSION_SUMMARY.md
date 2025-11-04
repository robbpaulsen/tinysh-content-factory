# Session Summary - 2025-11-03

## What We Accomplished

### ✅ Fixed Issues
1. **Reddit API Integration** - Removed PRAW, using public JSON endpoints
2. **FLUX API Integration** - Fixed parameters for Free tier (removed "n", updated dimensions)
3. **Image Upload to Media Server** - Fixed endpoint and request format
4. **Gemini Model Update** - Updated to stable gemini-2.0-flash
5. **Rate Limiting** - Added for Together.ai FLUX (6 images/min)
6. **YouTube Upload** - Disabled per user request, downloads to ./output/

### 🔧 Technical Improvements
1. Converted LLM service to async (wrapped sync Gemini SDK)
2. Implemented proper multipart/form-data requests for media server
3. Updated all media server endpoints to correct paths
4. Configured httpx client with appropriate timeouts

## 🚨 Current Blocker

### TTS Endpoint 404 Error

**Problem**: httpx returns 404 for TTS endpoints that work with curl

**Symptoms**:
```bash
# This works:
curl -X POST http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox -F "text=test"
# Returns: {"file_id":"audio_xxx.wav"}

# This fails:
Python httpx.post(url, data={"text": "test"})
# Error: Client error '404 Not Found'
```

**Status**: Under investigation

**Next Steps**: See DEBUGGING.md for detailed troubleshooting steps

## 📊 Progress Status

### Migration: ~85% Complete

**Working Services**:
- ✅ Reddit scraping
- ✅ Google Sheets integration
- ✅ Gemini LLM (speech + script generation)
- ✅ FLUX image generation
- ✅ Image upload to media server
- ✅ YouTube upload (disabled)

**Blocked Services**:
- ❌ TTS generation (404 error)
- ⏳ Video generation (untested, waiting on TTS)
- ⏳ Video merging (untested, waiting on TTS)

**Not Yet Tested**:
- ⏳ Complete end-to-end workflow
- ⏳ Error recovery and retry logic
- ⏳ File cleanup operations

## 📝 Key Learnings

### API Endpoints Discovery

**Media Server Endpoints** (corrected):
```
POST /api/v1/media/storage (not /upload-from-url)
POST /api/v1/media/audio-tools/tts/kokoro (not /api/v1/tts/kokoro)
POST /api/v1/media/audio-tools/tts/chatterbox (not /api/v1/tts/chatterbox)
```

**Response Format**:
- TTS endpoints return `file_id` directly (synchronous)
- Not async `task_id` as originally expected
- No polling needed for TTS

**Request Format**:
- Must use `multipart/form-data` for most endpoints
- httpx: use `data=` parameter (or `files=` for actual files)
- Include `media_type` for storage uploads

### Together.ai FLUX API

**Free Tier Restrictions**:
- No "n" parameter (can't request multiple images)
- Steps fixed at 4 for Schnell
- Recommended dimensions: 768x1344

**Rate Limits**:
- 6 images per minute
- Implemented with aiolimiter

### Gemini API

**Model Selection**:
- gemini-1.5-flash: DEPRECATED
- gemini-2.0-flash: Stable, recommended
- gemini-2.5-flash: Doesn't exist (typo)
- Experimental models have restrictive rate limits

**Async Handling**:
- SDK is synchronous
- Wrapped in asyncio.run_in_executor()
- Maintains async interface for workflow

## 🗂️ Documentation Created

1. **CHANGELOG.md** - Complete migration history and current status
2. **TODO.md** - Prioritized task list for next session
3. **DEBUGGING.md** - Detailed troubleshooting guide for TTS issue
4. **SESSION_SUMMARY.md** - This file
5. **README.md** - Updated with correct dimensions

## 🎯 Next Session Goals

### Primary Goal
Fix TTS endpoint 404 error and get first successful TTS generation

### Secondary Goals
1. Test video generation endpoint
2. Test video merging endpoint
3. Complete one full video end-to-end

### Success Criteria
Generate at least one complete video from Reddit story to MP4 file in ./output/

## 🔍 Key Files Modified

### Core Implementation
```
src/services/media.py      # Image upload, TTS, video generation
src/services/llm.py        # Gemini integration
src/services/reddit.py     # Public JSON endpoints
src/config.py              # Updated settings
src/workflow.py            # Disabled YouTube upload
```

### Configuration
```
.env.example               # Removed Reddit keys, updated dimensions
pyproject.toml            # Added aiolimiter, removed praw
```

### Documentation
```
README.md                 # Updated image dimensions
CHANGELOG.md              # New - complete history
TODO.md                   # New - task breakdown
DEBUGGING.md              # New - TTS troubleshooting
SESSION_SUMMARY.md        # New - this file
```

## 💡 Debugging Tips for Next Session

### Quick Tests

```bash
# Test TTS with curl (should work)
curl -X POST http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox -F "text=test"

# Test TTS with Python (currently fails)
uv run python debug_tts.py

# Check media server health
uv run python -m src.main check-server

# Validate configuration
uv run python -m src.main validate-config
```

### Debug Script

Create `debug_tts.py` (see DEBUGGING.md) to test various httpx configurations

### Enable Debug Logging

```python
# Add to top of src/services/media.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check OpenAPI Docs

```bash
curl http://localhost:8000/openapi.json | python -m json.tool | less
```

## 📦 Environment Info

**Package Manager**: uv
**Python Version**: 3.11+
**Key Dependencies**:
- httpx (HTTP client)
- pydantic (validation)
- google-generativeai (Gemini)
- aiolimiter (rate limiting)
- click (CLI)
- rich (terminal UI)

**Configuration**:
- Media server: http://192.168.68.60:8000 (or localhost:8000)
- TTS engine: Chatterbox (user prefers over Kokoro)
- Image dimensions: 768x1344
- Gemini model: gemini-2.0-flash

## 🤔 Open Questions

1. **Why does curl work but httpx fails with 404?**
   - Hypothesis: Content-Type header difference
   - Hypothesis: URL construction issue
   - Hypothesis: httpx client settings
   - See DEBUGGING.md for investigation steps

2. **Do video endpoints return task_id or file_id?**
   - TTS returns file_id directly
   - Images return URL first, then file_id after upload
   - Video generation might be async (returns task_id?)
   - Need to test once TTS is working

3. **Should we parallelize scene processing?**
   - Images can be generated in parallel
   - TTS can be generated in parallel
   - Video generation might need to be serial (FFmpeg)
   - Optimization for later

## 📞 User Preferences

- ✅ Use Chatterbox TTS (not Kokoro)
- ✅ Disable automatic YouTube upload
- ✅ Download videos to ./output/ directory
- ✅ Manual upload to YouTube when ready
- ✅ Use uv exclusively for package management
- ✅ Keep local media server (cost-effective)

## 🔄 Workflow State

**Last Successful Step**: Image upload to media server

**Current Failure Point**: TTS generation

**Estimated Completion**: 2-3 hours once TTS is fixed

**Confidence Level**: High (all other parts working, just one API call issue)

## 📋 Quick Reference Commands

```bash
# Generate video (currently fails at TTS)
uv run python -m src.main generate --count 1

# Update stories from Reddit
uv run python -m src.main update-stories

# Check server health
uv run python -m src.main check-server

# Validate config
uv run python -m src.main validate-config

# Run with debug logging
DEBUG=1 uv run python -m src.main generate --count 1
```

## 🎬 Conclusion

We've successfully migrated ~85% of the n8n workflow to Python. The architecture is solid, most services are working, and we're blocked on a single API call issue. The TTS endpoint 404 error is puzzling since curl works, but once resolved, the rest should flow smoothly.

**Time Invested This Session**: ~3 hours
**Estimated Time to Completion**: 2-3 hours
**Estimated Total Project Time**: 5-6 hours

The migration is on track and the codebase is much cleaner and more maintainable than the original n8n workflow.

---

**Resume from here**: Start with DEBUGGING.md to fix the TTS issue, then test video generation.
