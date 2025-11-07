# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2025-01-07

### Added
- **SEO Optimizer Service** - Automatic YouTube metadata generation with Google Gemini
  - SEO-optimized titles (50-60 characters for max visibility)
  - Keyword-rich descriptions with strategic hashtags
  - 10-15 relevant tags per video
  - Automatic YouTube category selection
  - Profile-aware content optimization
  - Configurable via `SEO_ENABLED` environment variable (default: true)
- **SEO Metadata Model** - Type-safe Pydantic model for metadata validation
- **Metadata JSON Export** - Each video now generates `video_XXX_metadata.json` with:
  - SEO-optimized metadata ready for YouTube upload
  - Original title/description preserved for reference
  - Profile context for tracking
- **Configuration** - New `SEO_ENABLED` setting in `.env.example`

### Changed
- **WorkflowOrchestrator** - Integrated SEO metadata generation after video creation
- **Video Output** - Now produces both video file and metadata JSON
- **README** - Updated with SEO optimizer documentation

### Benefits
- Saves manual time writing YouTube titles and descriptions
- Improves video discoverability with optimized tags
- Consistent metadata quality across all videos
- Ready for multi-channel scaling with different SEO strategies

## [0.2.0] - 2025-01-XX

### Added
- **Voice & Music Profile System** - Manage multiple voice and music configurations via `profiles.yaml`
  - Define profiles with voice settings (Chatterbox/Kokoro) and music playlists
  - CLI `--profile` flag to select profiles at runtime
  - Music rotation modes: random or sequential
  - Automatic voice sample upload to media server
  - Path validation for voice samples and music files
  - `ProfileManager` service for loading and managing profiles
- **CLI Profile Support** - Added `--profile` flag to `generate` and `generate-single` commands

### Changed
- **Config System** - Removed hardcoded voice/music settings from `.env` in favor of profiles
- **MediaService** - Updated to accept `voice_config` and `music_volume` parameters
- **WorkflowOrchestrator** - Now uses ProfileManager for voice/music configuration
- **.env.example** - Simplified to point users to profiles.yaml for voice/music settings
- **Project Structure** - Added `src/services/profile_manager.py` and `profiles.yaml`

### Fixed
- Auto-uploads local voice sample files to media server (fixes repeated warnings)
- Music volume now configurable per profile instead of global setting

### Added (v0.2.0 features)
- **FFmpeg GPU Optimization** - NVENC hardware encoding support for 5-10x faster video processing
  - Configurable encoder: auto-detect, NVENC (GPU), or x264 (CPU)
  - Advanced NVENC settings: preset, CQ, bitrate, spatial/temporal AQ
  - Reduced audio bitrate to 128k (sufficient for Shorts)
- **Gemini Prompt Optimization** - Token-aware content generation
  - Target duration constraints: 15-45 seconds (480-1440 tokens)
  - Explicit token counting guidance (32 tokens = 1 second)
  - Mandatory YouTube Shorts structure with hooks and CTAs
- **YouTube Content Structure** - Enforced 3-part format:
  - Opening hook (max 5 seconds)
  - Main content (10-45 seconds)
  - Closing CTA mentioning "MommentumMindset"

### Changed
- **Video Encoding** - Switched from libx264 CPU encoding to h264_nvenc GPU encoding
- **Audio Bitrate** - Reduced from 192k to 128k for faster processing
- **Script Generation** - Added structured prompts for better YouTube engagement

### Fixed
- **Double Extension Bug** - Fixed `.mp4.mp4` filenames (file_id already includes extension)
- **Download Endpoint** - Removed incorrect `/download` suffix from media API calls
- **Voice Sample Upload** - Automatically uploads local voice samples to media server

### Performance
- **Video Generation Time**: Reduced from ~7 minutes to ~3 minutes (sequential mode)
- **Individual Mode**: 5-7 minutes (model loads/unloads each time)
- **GPU Encoding**: 5-10x faster than CPU encoding with NVIDIA GPU

## [0.1.0] - 2025-01-XX

### Added
- Initial Python implementation migrated from n8n workflow
- Reddit story scraping (public API, no authentication required)
- Google Sheets integration for story management
- Gemini LLM for motivational speech generation
- FLUX image generation via Together.ai
- TTS support: Kokoro and Chatterbox with voice cloning
- Local media server integration for video processing
- Automatic captioning with FFmpeg
- Video merging with background music
- YouTube upload with OAuth2
- Rich CLI with progress indicators
- Async/await architecture with httpx
- Retry logic with tenacity
- Type-safe configuration with Pydantic
- Environment-based configuration (.env)

### Features
- CLI commands:
  - `init` - Initialize .env from template
  - `validate-config` - Validate environment configuration
  - `check-server` - Health check media server
  - `update-stories` - Fetch stories from Reddit
  - `generate` - Generate videos from Google Sheets
  - `generate-single` - Generate video from single Reddit post

### Technical
- Python 3.11+ with type hints
- uv package manager for fast dependency management
- Pydantic for configuration validation
- httpx for async HTTP requests
- tenacity for retry logic
- rich for beautiful CLI output
- Google API clients for Sheets and YouTube

---

## Migration from n8n

This project replaces the original n8n workflow with a pure Python implementation, providing:
- Better type safety and IDE support
- Easier debugging and testing
- Git-friendly version control
- Direct SDK access for customization
- Improved error handling and logging
