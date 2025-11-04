# TODO - YouTube Shorts Factory Migration

## 🚨 Critical - Blocking Issues

### 1. Fix TTS Endpoint 404 Error
**Priority**: CRITICAL
**Status**: In Progress
**Blocking**: Complete workflow

**Problem**:
```python
# This fails with 404:
response = await self.client.post(
    f"{self.base_url}/api/v1/media/audio-tools/tts/chatterbox",
    data={"text": "test", ...}
)
# httpx.HTTPStatusError: Client error '404 Not Found'
```

**But this works**:
```bash
curl -X POST http://localhost:8000/api/v1/media/audio-tools/tts/chatterbox \
  -F "text=test"
# Returns: {"file_id":"audio_xxx.wav"}
```

**Possible Causes**:
- [ ] httpx client configuration issue
- [ ] URL construction problem (base_url trailing slash?)
- [ ] Headers mismatch between curl and httpx
- [ ] Content-Type header not set correctly for multipart/form-data
- [ ] httpx timeout/redirect settings

**Debug Steps**:
1. [ ] Print exact URL being called by httpx
2. [ ] Compare httpx headers vs curl headers
3. [ ] Try with explicit `Content-Type: multipart/form-data` header
4. [ ] Test with `files=` parameter instead of `data=`
5. [ ] Check if media server logs show the request arriving
6. [ ] Try httpx.Client() with different settings (follow_redirects, etc)

**File**: `src/services/media.py:154-192`

---

## 🔧 High Priority

### 2. Verify Video Generation Endpoint
**Priority**: HIGH
**Status**: Not Started
**Depends On**: TTS fix (#1)

**Tasks**:
- [ ] Find correct endpoint in media server docs
- [ ] Determine if it returns `task_id` or `file_id`
- [ ] Update `start_captioned_video_generation()` method
- [ ] Test with sample image_id and tts_id
- [ ] Handle polling if async, direct response if sync

**File**: `src/services/media.py:275-306`

**Current Code**:
```python
async def start_captioned_video_generation(
    self, image_id: str, tts_id: str, text: str
) -> str:
    # Endpoint may be wrong
    endpoint = f"{self.base_url}/api/v1/video/captioned"
    # ...
```

**Action**: Check OpenAPI docs for actual endpoint

### 3. Verify Video Merge Endpoint
**Priority**: HIGH
**Status**: Not Started
**Depends On**: Video generation (#2)

**Tasks**:
- [ ] Find correct endpoint in media server docs
- [ ] Determine if it returns `task_id` or `file_id`
- [ ] Update `start_video_merge()` method
- [ ] Test with sample video_ids
- [ ] Handle polling if async

**File**: `src/services/media.py:332-361`

---

## 🧪 Testing

### 4. End-to-End Testing
**Priority**: MEDIUM
**Status**: Blocked
**Depends On**: All critical fixes

**Test Cases**:
- [ ] Fetch Reddit stories
- [ ] Generate motivational speech
- [ ] Generate video script
- [ ] Generate image for scene
- [ ] Upload image to media server
- [ ] Generate TTS for scene
- [ ] Generate captioned video
- [ ] Merge multiple videos
- [ ] Add background music
- [ ] Download final video
- [ ] Update Google Sheets
- [ ] (Optional) Upload to YouTube

**Command**:
```bash
uv run python -m src.main generate --count 1
```

### 5. Error Recovery Testing
**Priority**: MEDIUM
**Status**: Not Started

**Test Scenarios**:
- [ ] Media server offline
- [ ] Together.ai rate limit hit
- [ ] Gemini API error
- [ ] Google Sheets auth expired
- [ ] Partial video generation failure
- [ ] Retry logic verification

---

## 📚 Documentation

### 6. Update README.md
**Priority**: LOW
**Status**: Partially Done

**Updates Needed**:
- [ ] Add troubleshooting section for TTS issues
- [ ] Document httpx vs curl differences
- [ ] Add debugging tips
- [ ] Update image dimensions (already 768x1344)
- [ ] Add section on testing individual services
- [ ] Update workflow diagram if needed

### 7. Add API Documentation
**Priority**: LOW
**Status**: Not Started

**Create**: `docs/API.md`
- [ ] Document all media server endpoints
- [ ] Include request/response examples
- [ ] Note sync vs async endpoints
- [ ] Document rate limits
- [ ] Add curl examples for testing

### 8. Add Development Guide
**Priority**: LOW
**Status**: Not Started

**Create**: `docs/DEVELOPMENT.md`
- [ ] How to add new services
- [ ] How to add new TTS engines
- [ ] How to modify video processing
- [ ] Testing guidelines
- [ ] Code style guidelines

---

## 🔄 Improvements

### 9. Better Error Messages
**Priority**: LOW
**Status**: Not Started

**Tasks**:
- [ ] Add more descriptive error messages
- [ ] Include API endpoint in errors
- [ ] Show request/response in debug mode
- [ ] Add suggestions for common errors

### 10. Configuration Validation
**Priority**: LOW
**Status**: Partially Done

**Enhancements**:
- [ ] Validate media server URL is reachable
- [ ] Check API keys are valid (test calls)
- [ ] Verify Google credentials exist
- [ ] Test TTS engine availability
- [ ] Check background music file exists

### 11. Parallel Processing
**Priority**: LOW
**Status**: Not Started

**Optimization**:
- [ ] Generate images in parallel for all scenes
- [ ] Generate TTS in parallel for all scenes
- [ ] Only serialize video generation (FFmpeg)
- [ ] Estimate time savings

---

## 🐛 Known Issues

### Issue #1: TTS Endpoint 404
- **Status**: Under Investigation
- **Impact**: Blocks workflow
- **Workaround**: None yet
- **See**: TODO #1

### Issue #2: Untested Video Endpoints
- **Status**: Waiting on TTS fix
- **Impact**: Unknown if will work
- **Workaround**: N/A
- **See**: TODO #2, #3

---

## ✅ Completed

### ~~Reddit API Migration~~
- ✅ Removed PRAW dependency
- ✅ Using public JSON endpoints
- ✅ No authentication required
- ✅ Tested and working

### ~~FLUX API Integration~~
- ✅ Removed unsupported "n" parameter
- ✅ Updated dimensions to 768x1344
- ✅ Added rate limiting (6/min)
- ✅ Tested and working

### ~~Image Upload to Media Server~~
- ✅ Fixed endpoint: `/api/v1/media/storage`
- ✅ Changed to multipart/form-data
- ✅ Added media_type parameter
- ✅ Tested and working

### ~~Gemini Model Update~~
- ✅ Updated to gemini-2.0-flash
- ✅ Removed deprecated 1.5 model
- ✅ Async wrapper implemented
- ✅ Tested and working

### ~~Google Sheets Integration~~
- ✅ OAuth2 authentication
- ✅ Read/write operations
- ✅ Safe defaults (no auto-update)
- ✅ Tested and working

### ~~YouTube Upload (Disabled)~~
- ✅ Implemented and working
- ✅ Disabled per user request
- ✅ Downloads videos to ./output/
- ✅ Manual upload workflow

---

## 📋 Quick Reference

### Commands to Test Individual Services

```bash
# Test Reddit
uv run python -c "from src.services.reddit import RedditService; r = RedditService(); print(len(r.get_top_stories()))"

# Test Sheets (requires OAuth)
uv run python -c "from src.services.sheets import GoogleSheetsService; s = GoogleSheetsService(); print(s.get_story_without_video())"

# Test Gemini
uv run python -c "import asyncio; from src.services.llm import LLMService; l = LLMService(); print(asyncio.run(l.create_motivational_speech('Test', 'This is a test')))"

# Test FLUX Image Generation
uv run python -c "import asyncio; from src.services.media import MediaService; m = MediaService(); print(asyncio.run(m.generate_image_together('A beautiful sunset')))"

# Test Media Server Health
uv run python -m src.main check-server

# Test TTS (currently failing)
uv run python -c "import asyncio; from src.services.media import MediaService; m = MediaService(); print(asyncio.run(m.generate_tts('test')))"
```

### Debug Mode

Add to `src/services/media.py` for debugging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check Media Server Endpoints

```bash
curl http://localhost:8000/openapi.json | python -m json.tool | grep -A 5 "tts"
```

---

## 🎯 Next Session Goals

1. **Primary**: Fix TTS 404 error
2. **Secondary**: Test video generation
3. **Tertiary**: Complete one full video

**Estimated Time**: 2-3 hours

**Success Criteria**: Generate at least one complete video from Reddit story to MP4 file.
