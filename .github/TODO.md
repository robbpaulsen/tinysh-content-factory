# TODO List

Project task tracker for YouTube Shorts Factory.

## ✅ Completed (Phase 1 - Optimization)

### Performance Optimization
- [x] **FFmpeg GPU Encoding (NVENC)** - Implemented h264_nvenc for 5-10x faster encoding
  - Configurable encoder: auto, nvenc, x264
  - Advanced NVENC params: preset, CQ, bitrate, spatial/temporal AQ
  - Reduced audio bitrate to 128k
  - **Result**: ~7min → ~3min per video (sequential mode)

- [x] **Gemini Prompt Optimization** - Token-aware content generation
  - Duration constraints: 15-45 seconds (480-1440 tokens)
  - Explicit token counting guidance
  - Mandatory YouTube structure (hook + content + CTA)

- [x] **Bug Fixes**
  - Fixed double extension issue (.mp4.mp4)
  - Fixed download endpoint (removed /download suffix)
  - Auto-upload voice samples to media server

## ✅ Completed (Phase 2 - Profile System)

### Voice & Music Profiles
- [x] **profiles.yaml** - YAML-based configuration system
  - Voice settings (engine, sample path, parameters)
  - Music playlists with rotation (random/sequential)
  - Per-profile volume settings
  - Path validation

- [x] **ProfileManager Service** - Profile management
  - Load and validate profiles from YAML
  - Music rotation logic (random/sequential)
  - Auto-save rotation state
  - Voice/music config providers

- [x] **CLI Integration**
  - `--profile` flag on generate commands
  - Default profile from profiles.yaml
  - Profile validation on startup

- [x] **Workflow Integration**
  - WorkflowOrchestrator uses ProfileManager
  - Voice config passed to TTS generation
  - Music config passed to video merging
  - Logging which profile/track is used

- [x] **Documentation**
  - README.md updated with profile system
  - CHANGELOG.md created with version history
  - .env.example updated to point to profiles.yaml

## ✅ Completed (Phase 3 - SEO Optimization)

### SEO Optimizer
- [x] **SEOOptimizerService** - Gemini-based metadata generation
  - SEO-optimized titles (50-60 chars)
  - Descriptions with keywords and hashtags
  - Tag suggestions (10-15 tags)
  - YouTube category selection
  - Profile-aware context

- [x] **SEOMetadata Model** - Pydantic model for metadata
  - Title, description, tags, category_id fields
  - Validation and type safety

- [x] **Workflow Integration**
  - Automatic metadata generation after video creation
  - JSON file output (video_XXX_metadata.json)
  - Configurable via SEO_ENABLED flag
  - Preserves original title/description for reference

- [x] **Configuration**
  - SEO_ENABLED environment variable
  - Defaults to enabled
  - Can be disabled without breaking workflow

## ✅ Completed (Phase 4 - Logging System)

### Logging Service
- [x] **LoggerService** - Comprehensive logging infrastructure
  - Simple mode (INFO level, console only with progress bars)
  - Verbose mode (DEBUG level, console + file with detailed traces)
  - File logging with rotation (10MB max, 5 backups)
  - Timestamped log files in `output/logs/`
  - Automatic cleanup of old logs (configurable retention)

- [x] **Performance Metrics**
  - `log_performance` context manager for timing operations
  - Tracks video generation, LLM calls, image/TTS/video generation, merging
  - Detailed per-scene timing in verbose mode
  - Total workflow duration tracking

- [x] **API Call Logging**
  - `log_api_call` function for tracking external API interactions
  - Logs Gemini API calls (speech generation, script creation)
  - Success/error/retry status tracking
  - Response details (chars generated, scenes created, etc.)

- [x] **CLI Integration**
  - `--verbose` global flag for all commands
  - Automatic log cleanup on startup
  - Configurable via environment variables

- [x] **Configuration**
  - `LOG_TO_FILE` - Enable/disable file logging
  - `LOG_DIR` - Log directory path
  - `LOG_MAX_AGE_DAYS` - Log retention period (1-30 days)

## 🔄 In Progress

None

## 📋 Planned Features

### Scheduling Improvements
- [ ] **Smart Gap-Filling Logic Enhancement**: Refine `VideoScheduler.calculate_next_available_slot` to prioritize finding the earliest available slot *from the current moment*, including filling gaps in *today's* schedule before moving to subsequent days.
  - **Problem**: Current logic defaults to starting from "tomorrow" and sometimes misses available slots or gaps earlier in the schedule.
  - **Goal**: Ensure the scheduler checks for and fills today's open slots first, then systematically finds the earliest possible publish time across all configured daily windows, respecting interval and start/end hours.

### General Improvements
- [ ] Unit tests for services
- [ ] Integration tests for workflow
- [ ] CI/CD pipeline setup
- [ ] Docker containerization
- [ ] Web UI for monitoring (optional)

## 🐛 Known Issues

None currently

## 📝 Notes

### API Limitations
- **Together.ai FLUX-Free**: Sequential only (~5-6 images/min max)
- **Chatterbox TTS**: Requires Python 3.10, complex torch setup
- **YouTube API**: Daily upload quotas vary by account

### Performance Benchmarks
- **Sequential Mode**: ~3 minutes per video (recommended)
- **Individual Mode**: 5-7 minutes (model overhead)
- **GPU vs CPU**: 5-10x speedup with NVENC

### Profile System Design
- YAML chosen over JSON for human-readability and comments
- Rotation state auto-saved to avoid repetition
- Backward compatible with old .env settings
