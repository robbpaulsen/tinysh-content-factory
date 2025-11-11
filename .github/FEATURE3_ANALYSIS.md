# Feature 3: Local Media Processing - Analysis & Design

**Date**: 2025-11-06
**Goal**: Migrate Docker container media processing to local Python execution

---

## 📊 Server Analysis (Docker Container)

### Architecture Overview

**Current Setup**: FastAPI server in Docker container
- **Entry Point**: `server.py` - FastAPI app with /api/v1/media endpoints
- **Device Detection**: Intelligent CUDA > MPS > CPU with thread configuration
- **Main Components**:
  1. TTS engines (Chatterbox + Kokoro)
  2. FFmpeg video processing (VideoBuilder)
  3. Caption generation
  4. File storage and serving

---

### Component Breakdown

#### 1. TTS Engines

**A. Chatterbox TTS** (PRIORITY - Voice Cloning)
- **File**: `video/tts_chatterbox.py` (257 lines)
- **Dependencies**:
  - `chatterbox-tts >= 0.1.2`
  - PyTorch + torchaudio
  - NLTK (punkt tokenizer)
- **Key Features**:
  - `ChatterboxTTS.from_pretrained()` - Model loading
  - Voice cloning via `audio_prompt_path`
  - Text chunking for long inputs (max 1024 chars/chunk)
  - Tensor-based audio generation
  - Inter-chunk silence (350ms default)
- **Parameters**:
  - `temperature` (0.8 default)
  - `cfg_weight` (0.5 default)
  - `exaggeration` (0.5 default)
- **Output**: WAV file (stereo, 24kHz)

**B. Kokoro TTS** (FALLBACK - Generic Voices)
- **File**: `video/tts.py` (444 lines)
- **Dependencies**:
  - `kokoro` library
  - KPipeline
- **Features**:
  - 20+ pre-defined voices (US/GB English, Spanish, French, etc.)
  - Sentence-based processing
  - Returns captions with timestamps
  - No voice cloning
- **Output**: WAV file + captions array

#### 2. Video Processing

**A. VideoBuilder**
- **File**: `video/builder.py`
- **Pattern**: Fluent/Builder pattern
- **Capabilities**:
  - Background: Image (with Ken Burns effect) or Video
  - Audio: From file
  - Captions: Subtitle rendering
  - Effects: Ken Burns zoom, pan
- **FFmpeg Command Construction**:
  - Detects audio duration
  - Builds complex filter_complex chains
  - NVENC GPU encoding support
  - H.264 output

**B. Caption**
- **File**: `video/caption.py`
- **Purpose**: Subtitle segmentation
- **Features**:
  - English word-level captions
  - International sentence-level captions
  - Max length per line (80 chars)
  - Multi-line support (2 lines default)
  - Prevents overlap

**C. MediaUtils**
- **File**: `video/media.py`
- **Purpose**: FFmpeg utilities
- **Key Methods**:
  - `get_audio_info()` - Duration, sample rate
  - `get_video_info()` - Dimensions, fps
  - `merge_videos()` - Concatenate with music
  - Probe audio/video metadata

#### 3. Device Configuration

**File**: `video/config.py`
- **Device Priority**: CUDA > MPS > CPU
- **CPU Optimization**: Thread count from cgroups or os.cpu_count()
- **Torch Patching**: Auto map_location for all torch.load()

#### 4. Storage

**File**: `video/storage.py` (not read yet, but exists)
- File management
- Temp file cleanup
- Download serving

---

## 🎯 Migration Strategy

### Architecture Design: `src/media_local/`

```
src/media_local/
├── __init__.py           # Main exports
├── config.py             # Device detection, torch setup
├── tts/
│   ├── __init__.py
│   ├── chatterbox.py     # ChatterboxTTS wrapper (PRIORITY)
│   ├── kokoro.py         # KokoroTTS wrapper (FALLBACK)
│   └── base.py           # Base TTS interface
├── video/
│   ├── __init__.py
│   ├── builder.py        # FFmpeg command builder
│   ├── caption.py        # Subtitle generation
│   ├── effects.py        # Ken Burns, pan, etc.
│   └── processor.py      # High-level video operations
├── ffmpeg/
│   ├── __init__.py
│   ├── wrapper.py        # ffmpeg-python wrapper
│   ├── nvenc.py          # GPU encoding detection
│   └── utils.py          # Probing, info extraction
└── storage/
    ├── __init__.py
    ├── manager.py        # Local file management
    └── temp.py           # Temp file cleanup
```

---

## 🔧 Implementation Plan

### Phase 1: Core Infrastructure (High Priority)

#### Task 3.1: Device Configuration ✅ COMPLETED
- Create `src/media_local/config.py`
- Port device detection logic from server
- CUDA > MPS > CPU priority
- Thread configuration for CPU

#### Task 3.2: FFmpeg Wrapper (CRITICAL)
- Create `src/media_local/ffmpeg/wrapper.py`
- Use `ffmpeg-python` library
- Implement:
  - `probe_audio()` - Get audio info
  - `probe_video()` - Get video info
  - `build_video()` - Image + audio + captions → video
  - `merge_videos()` - Concatenate videos with music
- NVENC detection and fallback
- Test with sample files

#### Task 3.3: Chatterbox TTS (HIGH PRIORITY)
- Create `src/media_local/tts/chatterbox.py`
- Port from `video/tts_chatterbox.py`
- Implement:
  - `TTSChatterbox` class
  - Text chunking (NLTK)
  - Voice cloning support
  - Audio generation pipeline
- Handle PyTorch dependencies
- Test with voice samples

### Phase 2: Video Processing

#### Task 3.4: Video Builder
- Port `VideoBuilder` class
- Fluent interface for FFmpeg commands
- Ken Burns effect support
- Caption rendering

#### Task 3.5: Caption System
- Port `Caption` class
- Subtitle segmentation
- English + International support

### Phase 3: Storage & Integration

#### Task 3.6: Storage Manager
- Local file management
- Temp directory handling
- Auto-cleanup (30min)
- Path resolution

#### Task 3.7: Kokoro TTS (Optional Fallback)
- Create `src/media_local/tts/kokoro.py`
- Port from `video/tts.py`
- Lower priority than Chatterbox

### Phase 4: Integration & Fallback

#### Task 3.8: Fallback System
- Detect if local processing available
- Fall back to Docker if needed
- Graceful degradation
- Configuration flag

#### Task 3.9: MediaService Integration
- Update `src/services/media.py`
- Add `use_local_processing` flag
- Route to local or Docker based on config
- Maintain same interface

---

## 📦 Dependencies to Add

### Required (pyproject.toml)
```toml
dependencies = [
    # Existing...

    # TTS & Audio
    "chatterbox-tts>=0.1.2",  # Voice cloning (CRITICAL)
    "torch>=2.0.0",            # PyTorch (HEAVY - ~2GB)
    "torchaudio>=2.0.0",       # Audio processing
    "nltk>=3.8",               # Text processing
    "soundfile>=0.12.1",       # Audio I/O

    # Video Processing
    "ffmpeg-python>=0.2.0",    # FFmpeg wrapper

    # Optional fallback
    # "kokoro",                # Fallback TTS (lighter)
]
```

### System Requirements
- **FFmpeg**: Must be installed and in PATH
- **CUDA** (optional): For GPU acceleration
- **PyTorch**: CPU or CUDA version depending on hardware
- **Python**: 3.11 (recommended for Chatterbox TTS)

**⚠️ Chatterbox Installation**: See `.github/CHATTERBOX_INSTALLATION.md` for proven installation method that works

---

## ⚠️ Challenges & Solutions

### Challenge 1: PyTorch Size (~2GB)
**Impact**: Heavy dependency
**Solution**:
- Accept the trade-off (essential for Chatterbox)
- Optional: CPU-only torch for lighter installs
- Consider lazy loading

### Challenge 2: CUDA Configuration
**Impact**: Complex GPU setup
**Solution**:
- Auto-detect CUDA availability
- Fallback to CPU seamlessly
- Clear error messages for GPU issues

### Challenge 3: FFmpeg Command Complexity
**Impact**: Complex filter_complex chains
**Solution**:
- Use `ffmpeg-python` for cleaner API
- Build incrementally
- Test each component separately

### Challenge 4: Cross-Platform
**Impact**: Windows vs Linux differences
**Solution**:
- Path handling with pathlib
- Platform-specific thread counts
- Test on both platforms

---

## 🎯 Success Criteria

### Functional Requirements
- ✅ Generate TTS with Chatterbox (voice cloning)
- ✅ Generate video (image + audio + captions)
- ✅ Merge videos with background music
- ✅ NVENC GPU encoding support
- ✅ Fallback to Docker if local fails

### Performance Requirements
- ⚡ **Target**: Faster than Docker (eliminate HTTP overhead)
- ⚡ **Expected**: 10-20% speed improvement
- ⚡ **TTS**: Same speed (same engine)
- ⚡ **FFmpeg**: Slightly faster (no network)

### Quality Requirements
- 🎭 Voice quality identical to Docker version
- 📹 Video quality identical (same encoding settings)
- 🎬 No degradation in captions or effects

---

## 🔄 Migration Phases

### Phase A: Parallel Execution (Safe)
1. Implement local processing
2. Keep Docker as primary
3. A/B test both systems
4. Compare outputs

### Phase B: Local Primary (Transition)
1. Make local processing default
2. Docker as fallback
3. Monitor for issues
4. Collect performance metrics

### Phase C: Docker Optional (Final)
1. Local processing proven stable
2. Docker purely optional
3. Update documentation
4. Simplify setup guide

---

## 📈 Expected Benefits

### Development Experience
- 🚀 **Faster iteration**: No container restarts
- 🔧 **Easier debugging**: Direct Python debugging
- 💻 **Full control**: Modify code instantly
- 🤝 **Better collaboration**: Shared codebase

### Performance
- ⚡ **10-20% faster**: No HTTP overhead
- 📉 **Lower latency**: Direct function calls
- 💾 **Less memory**: No FastAPI server

### Stability
- 🛡️ **Type safety**: Python type hints
- 🧪 **Easier testing**: Unit tests without containers
- 📝 **Better logging**: Integrated with main app
- 🔄 **Simpler deployment**: One Python process

---

## 🚀 Next Steps

1. ✅ Analysis complete
2. ⏭️ Create `src/media_local/` structure
3. ⏭️ Implement FFmpeg wrapper (most reusable)
4. ⏭️ Implement Chatterbox TTS (highest value)
5. ⏭️ Test with actual workflows
6. ⏭️ Performance benchmark vs Docker
7. ⏭️ Gradual rollout with fallback

---

**Status**: Analysis complete, ready for implementation
**Priority**: HIGH - Core stability improvement
**Risk**: Medium (heavy dependencies, but isolated)
**Estimated Time**: 10-15 hours total implementation
