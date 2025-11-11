# Video Generation Optimization Analysis

**Date**: 2025-11-06
**Goal**: Optimize video generation workflow to reduce total processing time

---

## 📊 Current Workflow Analysis

### Flow Diagram (Sequential):

```
Story → Gemini Script Generation
      ↓
   Scene 1:
      → Generate Image (15-30s)
      → Generate TTS (10-20s)
      → Generate Video (5-10s)
   Scene 2:
      → Generate Image (15-30s)
      → Generate TTS (10-20s)
      → Generate Video (5-10s)
   Scene N:
      → Generate Image (15-30s)
      → Generate TTS (10-20s)
      → Generate Video (5-10s)
      ↓
   Merge Videos (10-20s)
      ↓
   Final Video
```

### Current Timing (3 scenes example):

| Operation | Time per scene | Total Time (3 scenes) |
|-----------|---------------|----------------------|
| Image Generation | 15-30s | 45-90s |
| TTS Generation | 10-20s | 30-60s |
| Video Generation | 5-10s | 15-30s |
| Video Merge | 10-20s | 10-20s |
| **TOTAL** | | **100-200s** (1.5-3.5 min) |

---

## 🎯 Bottleneck Identification

### 1. **Sequential Image + TTS** ❌ (Biggest Opportunity)
**Current Code** (`workflow.py:114-121`):
```python
# Sequential - TTS waits for image
image = await self.media.generate_and_upload_image(scene.image_prompt)
tts = await self.media.generate_tts(scene.text, voice_config=voice_config)
```

**Problem**: Image and TTS are independent but processed sequentially
**Impact**: ~15-30s wasted per scene
**Solution**: Run in parallel with `asyncio.gather()`

### 2. **Sequential Scene Processing** ⚠️ (Limited by Rate Limits)
**Current Code** (`workflow.py:111-130`):
```python
for idx, scene in enumerate(script.scenes, 1):
    # Process one scene at a time
```

**Problem**: Scenes could be processed in parallel
**Limitation**: Together.ai FLUX has strict rate limits (6 images/min)
**Impact**: Moderate - can parallelize TTS but not images
**Solution**: Parallel TTS + batched image generation with delays

### 3. **Video Generation Wait** ❌
**Current Code** (`workflow.py:124-127`):
```python
# Waits for both image and TTS before starting
video = await self.media.generate_captioned_video(
    image.file_id, tts.file_id, scene.text
)
```

**Problem**: Video generation could start as soon as BOTH image + TTS are ready
**Impact**: ~5-10s per scene
**Solution**: Start video gen immediately when dependencies ready

---

## 🚀 Optimization Strategies

### Strategy 1: **Parallel Image + TTS per Scene** (SAFE ✅)

**Before**:
```python
image = await self.media.generate_and_upload_image(scene.image_prompt)  # 20s
tts = await self.media.generate_tts(scene.text, voice_config)          # 15s
video = await self.media.generate_captioned_video(...)                  # 8s
# Total: 43s per scene
```

**After**:
```python
# Run image + TTS in parallel
image, tts = await asyncio.gather(
    self.media.generate_and_upload_image(scene.image_prompt),  # 20s
    self.media.generate_tts(scene.text, voice_config)          # 15s
)
# Start video immediately when both ready
video = await self.media.generate_captioned_video(...)          # 8s
# Total: max(20, 15) + 8 = 28s per scene
```

**Savings**: ~15s per scene (35% faster per scene)
**Risk**: None - operations are independent
**Rate Limits**: No impact (same number of API calls)

---

### Strategy 2: **Batch All TTS First** (MODERATE ⚠️)

**Approach**:
1. Generate ALL TTS audio first (parallel)
2. Generate images sequentially (rate limit safe)
3. Generate videos as image+TTS pairs become ready

**Before** (3 scenes):
```
Scene 1: Image(20s) → TTS(15s) → Video(8s) = 43s
Scene 2: Image(20s) → TTS(15s) → Video(8s) = 43s
Scene 3: Image(20s) → TTS(15s) → Video(8s) = 43s
Total: 129s
```

**After** (3 scenes):
```
ALL TTS in parallel: max(15s, 15s, 15s) = 15s
Image 1: 20s → Video 1: 8s
Image 2: 20s → Video 2: 8s
Image 3: 20s → Video 3: 8s
Total: 15s + (20+8)*3 = 99s
```

**Savings**: ~30s for 3 scenes (23% faster overall)
**Risk**: Low - TTS has no strict rate limits
**Complexity**: Medium - need to manage parallel TTS then sequential images

---

### Strategy 3: **Full Pipeline Parallelization** (RISKY ❌)

**Approach**:
- Process multiple scenes completely in parallel
- Respect image rate limits with semaphore/delays

**Problem**: Together.ai FLUX rate limit (6 images/min)
**Risk**: HIGH - can trigger 15min API block
**Status**: ❌ Not recommended (learned from previous attempts)

---

## ✅ Recommended Implementation

### **Hybrid Approach**: Strategy 1 + Controlled Strategy 2

```python
async def generate_video_from_story_optimized(self, story: StoryRecord):
    # Step 1: Generate script (unchanged)
    script = await self.llm.create_complete_workflow(story.title, story.content)

    # Step 2: Generate ALL TTS in parallel (no rate limits)
    console.print("[cyan]  → Generating TTS for all scenes...[/cyan]")
    tts_tasks = [
        self.media.generate_tts(scene.text, voice_config=voice_config)
        for scene in script.scenes
    ]
    all_tts = await asyncio.gather(*tts_tasks)
    console.print(f"[green]  ✓ Generated {len(all_tts)} TTS audios[/green]")

    # Step 3: Process each scene (image + video) with TTS already ready
    scene_videos = []
    for idx, (scene, tts) in enumerate(zip(script.scenes, all_tts), 1):
        console.print(f"[cyan]  → Scene {idx}/{len(script.scenes)}...[/cyan]")

        # Generate image (sequential - respect rate limits)
        image = await self.media.generate_and_upload_image(scene.image_prompt)

        # Generate video immediately (TTS already ready)
        video = await self.media.generate_captioned_video(
            image.file_id, tts.file_id, scene.text
        )

        scene_videos.append(video)

    # Step 4: Merge videos (unchanged)
    final_video_id = await self.media.merge_videos(...)

    return final_video_id, script
```

### Expected Performance Improvement:

**Before** (3 scenes):
- Scene 1: Image(20s) + TTS(15s) + Video(8s) = 43s
- Scene 2: Image(20s) + TTS(15s) + Video(8s) = 43s
- Scene 3: Image(20s) + TTS(15s) + Video(8s) = 43s
- Merge: 15s
- **Total: 144s (2.4 min)**

**After** (3 scenes):
- ALL TTS parallel: max(15s, 15s, 15s) = 15s
- Scene 1: Image(20s) + Video(8s) = 28s
- Scene 2: Image(20s) + Video(8s) = 28s
- Scene 3: Image(20s) + Video(8s) = 28s
- Merge: 15s
- **Total: 114s (1.9 min)**

**Improvement**: ~30s saved (21% faster) for 3-scene video

---

## 🔬 Alternative: Strategy 1 Only (Safest)

If we want to be more conservative:

```python
for idx, scene in enumerate(script.scenes, 1):
    # Parallel image + TTS per scene
    image, tts = await asyncio.gather(
        self.media.generate_and_upload_image(scene.image_prompt),
        self.media.generate_tts(scene.text, voice_config=voice_config)
    )

    # Video generation
    video = await self.media.generate_captioned_video(
        image.file_id, tts.file_id, scene.text
    )

    scene_videos.append(video)
```

**Before** (per scene): 20s + 15s + 8s = 43s
**After** (per scene): max(20s, 15s) + 8s = 28s
**Improvement**: 15s per scene (35% faster per scene)

For 3 scenes:
- Before: 129s + 15s merge = 144s (2.4 min)
- After: 84s + 15s merge = 99s (1.65 min)
- **Savings: 45s (31% faster)**

---

## 📋 Implementation Plan

### Phase 1: Simple Parallel (Low Risk)
1. Implement Strategy 1 (parallel image + TTS per scene)
2. Test with 1 video
3. Measure timing improvement
4. **Risk**: Very low
5. **Expected gain**: 30-35% faster

### Phase 2: Batch TTS (Medium Risk)
1. Implement Strategy 2 (batch all TTS first)
2. Test with 3-scene video
3. Compare with Phase 1
4. **Risk**: Low (TTS has no rate limits)
5. **Expected gain**: Additional 10-15% faster

### Phase 3: Monitor & Tune
1. Add timing metrics to each step
2. Log performance data
3. Identify any new bottlenecks
4. Optimize based on real data

---

## ⚠️ Important Considerations

### Rate Limits (CRITICAL):
- ✅ TTS (Chatterbox): No strict rate limits - parallel is safe
- ❌ Images (Together.ai FLUX): **6 images/min max** - stay sequential
- ✅ Video Generation (FFmpeg): No rate limits - can parallelize
- ✅ Merge (FFmpeg): No rate limits

### Error Handling:
- If one TTS fails in batch, others should continue
- Need proper error propagation and logging
- Fallback to sequential if parallel fails

### Memory:
- Batching all TTS means holding more audio files in memory
- Should be fine for 3-5 scenes
- May need optimization for 10+ scenes

---

## 📊 Success Metrics

1. **Total video generation time** (main metric)
   - Target: <2 min for 3-scene video (currently 2.4 min)
   - Stretch goal: <1.5 min

2. **Per-scene processing time**
   - Target: <30s per scene (currently 43s)
   - Stretch goal: <25s

3. **TTS generation time**
   - Current: 15s per scene × N scenes (sequential)
   - Target: max(15s) for all scenes (parallel)

4. **No increase in error rate**
   - Must maintain current reliability
   - No rate limit violations

---

## 🚦 Decision

**Recommendation**: Start with **Phase 1** (Strategy 1 - parallel image+TTS per scene)

**Reasoning**:
1. Simplest to implement
2. Lowest risk
3. Significant gain (30-35%)
4. No rate limit concerns
5. Easy to test and rollback

**Next Steps**:
1. Implement Strategy 1 in `workflow.py`
2. Test with real video generation
3. Measure performance
4. If successful, consider Phase 2 (batch TTS)

---

## ✅ Implementation Status

**Phase 1 - IMPLEMENTED** (2025-11-06)

### Changes Made:
- Modified `src/workflow.py:111-133`
- Image + TTS now execute in parallel using `asyncio.gather()`
- Video generation starts immediately when both ready
- **No change in API call count** - same number of requests

### Code:
```python
# Before (sequential):
image = await self.media.generate_and_upload_image(scene.image_prompt)
tts = await self.media.generate_tts(scene.text, voice_config=voice_config)
video = await self.media.generate_captioned_video(...)

# After (parallel):
image, tts = await asyncio.gather(
    self.media.generate_and_upload_image(scene.image_prompt),
    self.media.generate_tts(scene.text, voice_config=voice_config)
)
video = await self.media.generate_captioned_video(...)
```

### Expected Results:
- **Per scene**: 43s → 28s (35% faster)
- **3 scenes**: 144s → 99s (31% faster)
- **API calls**: Unchanged (no rate limit impact)

### Next Steps:
- Test with real video generation
- Measure actual performance improvement
- Consider Phase 2 if results are positive

---

**Status**: Phase 1 implemented, awaiting testing
**Priority**: HIGH
**Risk**: LOW
**Expected Time**: Testing in progress
