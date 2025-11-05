# Technical Decisions & Implementation Notes

This document records technical decisions made during development, especially those made with Claude Code assistance.

## Phase 1: Performance Optimization (2025-01)

### Context
Original workflow took ~7 minutes per video. Goal: reduce to ~4 minutes through optimization.

### Decision 1: FFmpeg GPU Encoding (NVENC)

**Problem**: Video encoding was CPU-bound and slow with libx264.

**Solution**: Implemented NVENC hardware encoding for systems with NVIDIA GPUs.

**Implementation** (`workflow_youtube_shorts/builder-version-mas-nueva.py:279-295`):
```python
# Changed from:
cmd.extend(["-c:v", "libx264", "-preset", "ultrafast"])

# To:
cmd.extend(["-c:v", "h264_nvenc"])
cmd.extend(["-preset", "p4"])  # p4 = balanced quality/speed
cmd.extend(["-tune", "hq"])
cmd.extend(["-rc", "vbr"])
cmd.extend(["-cq", "23"])
cmd.extend(["-b:v", "5M"])
```

**Configuration** (`.env`):
- `FFMPEG_ENCODER=auto` - Auto-detect GPU, fallback to CPU
- `FFMPEG_PRESET=p4` - NVENC preset (p1-p7)
- `FFMPEG_CQ=23` - Quality level (18=best, 28=worst)
- `FFMPEG_BITRATE=5M` - Target bitrate

**Results**:
- Sequential mode: ~7min → ~3min (57% reduction)
- Individual mode: 5-7 minutes (model loading overhead)
- 5-10x speedup vs CPU encoding

**Trade-offs**:
- ✅ Massive speed improvement
- ✅ Configurable fallback to CPU
- ⚠️ Requires NVIDIA GPU with NVENC support
- ⚠️ Slightly different encoding characteristics than x264

### Decision 2: Gemini Prompt Optimization

**Problem**: Generated content varied in length, causing inconsistent video durations.

**Solution**: Token-aware prompts with explicit duration constraints.

**Implementation** (`src/services/llm.py:67-86, 128-154`):

1. **Motivational Speech Generation**:
```python
Instructions:
- TARGET LENGTH: 15-45 seconds when spoken (480-1440 tokens)
- For YouTube Shorts: Keep between 15s minimum and 45s maximum
- Gemini measures 32 tokens = 1 second of speech
```

2. **Mandatory YouTube Structure**:
```python
MANDATORY SCRIPT STRUCTURE:
1. [OPENING HOOK]: Brief (max 5s) energetic welcome
2. [MAIN CONTENT]: The 10-45s content
3. [CLOSING CTA]: Explicit mention "MommentumMindset"
```

**Results**:
- Consistent 15-45 second videos
- Better YouTube engagement with hooks/CTAs
- Token counting helps predict duration

**Trade-offs**:
- ✅ Predictable video lengths
- ✅ Better viewer retention
- ⚠️ Less creative freedom (structured format)

### Decision 3: Bug Fixes

**3a. Double Extension Bug**:
- **Problem**: Files named `video_xxx.mp4.mp4`
- **Cause**: `file_id` already includes extension
- **Fix**: Removed `.mp4` suffix in 3 locations (`src/workflow.py:151,235,294`)

**3b. Download Endpoint**:
- **Problem**: 404 errors on `/api/v1/media/storage/{file_id}/download`
- **Fix**: Removed `/download` suffix (`src/services/media.py:527`)

**3c. Voice Sample Upload**:
- **Problem**: Repeated warnings about local voice sample path
- **Fix**: Auto-upload local files to media server (`src/services/media.py:220-231`)

## Phase 2: Profile System (2025-01)

### Context
Managing multiple voice styles and music tracks was cumbersome with environment variables. Needed flexible system for different content types.

### Decision 4: YAML-Based Profile System

**Problem**: Hard to manage multiple voice/music configurations in `.env`.

**Alternative Considered**:
- JSON configuration
- Multiple .env files
- Database storage

**Choice**: YAML configuration file (`profiles.yaml`)

**Rationale**:
1. **Human-readable**: Easy to edit manually
2. **Comments**: Can document each profile inline
3. **Native Python support**: PyYAML library
4. **Git-friendly**: Diffs readable in version control
5. **No database overhead**: Simple file-based

**Structure**:
```yaml
profiles:
  profile_id:
    name: "Display Name"
    description: "Profile description"
    voice:
      engine: chatterbox  # or kokoro
      sample_path: "path/to/sample.mp3"
      temperature: 0.7
      cfg_weight: 0.65
      exaggeration: 0.55
    music:
      playlist:
        - path: "path/to/track.mp3"
          name: "Track Name"
      volume: 0.1
      rotation: random  # or sequential

default_profile: profile_id
rotation_state:  # auto-managed
  profile_id: 0
```

**Trade-offs**:
- ✅ Easy to edit and understand
- ✅ Supports comments and documentation
- ✅ Multiple profiles in one file
- ✅ Git-friendly diffs
- ⚠️ Requires PyYAML dependency
- ⚠️ No built-in schema validation (handled by Pydantic)

### Decision 5: ProfileManager Service

**Architecture** (`src/services/profile_manager.py`):

**Key Classes**:
1. `VoiceConfig` - Pydantic model for voice settings
2. `MusicTrack` - Individual music file with metadata
3. `MusicConfig` - Playlist configuration
4. `Profile` - Complete profile model
5. `ProfileManager` - Service to load and manage profiles

**Features**:
- Path validation (warns if files don't exist)
- Music rotation logic (random/sequential)
- Auto-save rotation state back to YAML
- Backward compatible (falls back to settings if no config)

**Integration Points**:
- `WorkflowOrchestrator.__init__()` - Loads ProfileManager
- `generate_video_from_story()` - Gets voice/music config
- `MediaService.generate_tts()` - Accepts voice_config dict
- `MediaService.merge_videos()` - Accepts music path and volume

### Decision 6: CLI Interface

**Implementation** (`src/main.py:79-84, 103-108`):

Added `--profile` flag to commands:
```bash
python -m src.main generate --count 1 --profile brody_calm
python -m src.main generate-single abc123 --profile denzel_powerful
```

**Default Behavior**:
- Uses `default_profile` from profiles.yaml
- Can override with CLI flag
- Can override with `ACTIVE_PROFILE` env var

**Priority**: CLI flag > env var > profiles.yaml default

### Decision 7: Backward Compatibility

**Approach**: Gradual migration, not breaking change.

**MediaService Changes**:
- `generate_tts()` accepts optional `voice_config` parameter
- `merge_videos()` accepts optional `background_music_path` and `music_volume`
- If no config provided, falls back to settings (old behavior)

**Config Changes**:
- Old TTS settings removed from config.py (no longer needed)
- Added `active_profile` and `profiles_path` fields
- .env.example updated to point to profiles.yaml

**Migration Path**:
1. Old .env files still work (fallback to settings)
2. Create profiles.yaml for new system
3. Gradually migrate to profile-based configs
4. Remove old settings from .env

## Image Generation Decisions

### Decision 8: Sequential Image Generation

**Context**: Together.ai FLUX-Free API has strict limits.

**Initial Attempt**: Parallel processing (3 images at once with delays)
- Result: HTTP 429 errors (rate limiting)

**Problem Discovery**:
- FLUX-Free accepts only 1 image at a time
- Rate limit ~5-6 images/minute
- Exceeding causes 15-minute block + API key regeneration

**Final Solution**: Sequential processing
- One image at a time
- Natural rate limiting through TTS generation time
- No artificial delays needed

**Code**: Reverted parallelization in `src/workflow.py:86-118`

**Trade-offs**:
- ✅ No rate limit errors
- ✅ Simpler code
- ✅ More reliable
- ⚠️ Slower (but TTS is bottleneck anyway)

## Architecture Patterns

### Pattern 1: Service-Oriented Design

Each service is independent and testable:
- `RedditService` - Story scraping
- `GoogleSheetsService` - Data storage
- `LLMService` - Content generation
- `MediaService` - TTS/video processing
- `YouTubeService` - Upload
- `ProfileManager` - Configuration

**Benefits**:
- Easy to mock for testing
- Clear separation of concerns
- Reusable components

### Pattern 2: Async/Await Architecture

**Rationale**: I/O-bound operations (API calls, file uploads)

**Implementation**:
- httpx for async HTTP
- asyncio for concurrency
- Retry logic with tenacity

**Not async**:
- Google API clients (blocking)
- File I/O (minimal overhead)

### Pattern 3: Configuration Management

**Pydantic Settings** (`src/config.py`):
- Type-safe environment variables
- Validation on startup
- IDE autocomplete
- Clear error messages

**Profile System**:
- YAML for human-editable configs
- Pydantic for runtime validation
- File-based (no database needed)

## Lessons Learned

### 1. API Rate Limits
- Always test with real API limits
- Free tiers have strict restrictions
- Design for sequential when necessary
- Retries with exponential backoff essential

### 2. FFmpeg Optimization
- Hardware encoding worth the complexity
- Configuration makes it flexible
- Fallback to CPU important for portability

### 3. Content Generation
- Token counting improves predictability
- Structured prompts better than freeform
- YouTube-specific formatting helps engagement

### 4. Configuration Systems
- YAML better than JSON for human editing
- Comments in config files invaluable
- Profile system more flexible than env vars
- Backward compatibility eases migration

### 5. Python Development
- Type hints catch bugs early
- Pydantic validation prevents runtime errors
- Rich CLI makes better UX
- uv package manager is fast

## Future Considerations

### Logging System (Planned Feature 1)
- Simple mode: Progress bars only
- Verbose mode: Full debugging
- Configurable log levels
- File output option

### SEO Optimizer (Planned Feature 3)
- Gemini-based metadata generation
- Title/description optimization
- Tag suggestions
- Thumbnail recommendations

### Testing Strategy
- Unit tests for each service
- Integration tests for workflow
- Mock external APIs
- CI/CD pipeline

### Deployment Options
- Docker containerization
- Web UI for monitoring
- Cloud deployment (serverless?)
- Scaling considerations

## References

### Documentation
- README.md - User guide
- CHANGELOG.md - Version history
- TODO.md - Task tracker
- profiles.yaml - Configuration examples

### Key Files
- `src/workflow.py` - Main orchestrator
- `src/services/profile_manager.py` - Profile system
- `src/services/media.py` - Media server client
- `src/services/llm.py` - Gemini integration
- `workflow_youtube_shorts/builder-version-mas-nueva.py` - Media server builder

### External Resources
- [Google Gemini API](https://ai.google.dev/)
- [Together.ai FLUX](https://www.together.ai/)
- [FFmpeg NVENC Guide](https://docs.nvidia.com/video-technologies/video-codec-sdk/ffmpeg-with-nvidia-gpu/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

---

*Document maintained by Claude Code assistance*
*Last updated: 2025-01-05*
