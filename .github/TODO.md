# TODO List

Project task tracker for YouTube Shorts Factory.

## ✅ Completed (Phase 6 - Retention & Polish)

### Visual Improvements (Visual Polish)
- [x] **Viral Subtitle Styles** - Configurable styles in `channel.yaml`
  - "Hormozi-style" presets: Large font, yellow text, thick black outline
  - Pacing controls: `max_lines` (1) and `max_length` (15) for dynamic speed-reading effect
  - Support for custom fonts (e.g., Arial Black, DejaVu Sans Bold)
- [x] **Negative Prompt Integration** - Native support for FLUX
  - Switched to native `negative_prompt` API parameter instead of prompt injection
  - Dramatically improves image quality by respecting "deformed, ugly, text" exclusions

### Workflow Optimization
- [x] **Semi-Parallel Processing** - Optimized generation pipeline
  - **Parallel TTS**: All audio generated simultaneously (Local resource)
  - **Sequential Imaging**: Strictly serialized image generation (`Semaphore(1)` + 12s cooldown) to respect free tier limits
  - **Resource Protection**: Global `Semaphore(2)` for heavy local tasks (TTS/Video) to prevent RAM/VRAM exhaustion
  - **Result**: Faster generation without 429 errors or crashes

### Scheduling Logic
- [x] **Smart Gap-Filling** - Intelligent scheduling
  - Prioritizes filling gaps in *today's* schedule
  - Scans 30-day horizon for first available slot
  - Correctly handles timezones from `channel.yaml`
  - Enforces channel category (e.g., "22") over AI guesses

## ✅ Completed (Phase 5 - 2-Phase Upload)

- [x] **Batch Upload/Schedule System**
  - Phase 1: Upload as private with metadata
  - Phase 2: Calculate schedule and update publishAt
  - Smart gap filling logic
  - Timezone awareness

## ✅ Completed (Phase 1-4)
*(Previous phases: Optimization, Profile System, SEO, Logging - see CHANGELOG)*

## 📋 Planned Features (v0.4.0)

### Analytics Sync (The Feedback Loop)
- [ ] **Stats Synchronization Command (`sync-stats`)**
  - Query YouTube API for Views, Likes, Comments on uploaded videos
  - Update Google Sheets with performance metrics
  - Enable data-driven decisions on which topics/subreddits perform best

### Future Enhancements
- [ ] **Compilations Mode**: Merge multiple Shorts into long-form (10min) horizontal videos
- [ ] **Web UI**: Simple dashboard for monitoring generation and schedule
- [ ] **Docker**: Full containerization of the client app

## 🐛 Known Issues

- **Font Limitations**: Server currently limited to "DejaVu Sans" family. For true "Hormozi" style, need to install "The Bold Font" or similar on the server.

## 📝 Notes

### API Limitations
- **Together.ai FLUX-Free**: Strict limit of 6 images/min (10s/image). Enforced by code.
- **Local Server**: TTS and Video rendering are RAM/VRAM intensive. Concurrency limited to 2.