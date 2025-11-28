# Workflow Optimizations & Performance

This document details the technical optimizations applied to the content generation workflow to balance speed, resource usage, and API constraints.

## Core Strategy: Semi-Parallel Processing

The workflow has been re-engineered from a purely sequential model to a hybrid **Semi-Parallel** model. This allows us to maximize the throughput of the local media server while strictly adhering to the rate limits of external APIs (specifically Together.ai's free tier).

### 1. Parallel TTS Generation (Local Server)
**Constraint:** None (Local resources).
**Optimization:**
Audio generation for *all* scenes in a script is launched simultaneously at the start of the process.
-   **Mechanism**: `asyncio.create_task()` is used to fire-and-forget the TTS requests to the local media server.
-   **Benefit**: The total time for TTS is reduced from `sum(scene_duration)` to `max(scene_duration)`.

### 2. Sequential Image Generation (External API)
**Constraint:** Together.ai / FLUX.1-schnell-Free model allows **max 1 concurrent request**.
**Optimization:**
Image generation is protected by a Semaphore to ensure strict serialization.
-   **Mechanism**: `asyncio.Semaphore(1)` wraps the `generate_and_upload_image` call.
-   **Behavior**: Although all scenes "start" at once, they queue up for image generation. As soon as Scene 1 finishes its image, Scene 2 begins.
-   **Benefit**: Prevents `429 Too Many Requests` errors while keeping the pipeline active.

### 3. Pipelined Video Assembly
**Constraint:** Requires both Image and TTS to be ready.
**Optimization:**
Video generation starts immediately for a scene as soon as its dependencies are met.
-   **Mechanism**: `await asyncio.gather()` inside the scene processing function.
-   **Behavior**:
    -   Scene 1 gets Image + Audio -> Starts Video Generation.
    -   While Scene 1 is generating video (local FFmpeg), Scene 2 acquires the semaphore and starts generating its image.
-   **Benefit**: Overlaps local CPU/GPU video rendering time with external API latency.

## Comparative Timeline

### Old Sequential Model
```
[Scene 1 Image] -> [Scene 1 TTS] -> [Scene 1 Video] -> [Scene 2 Image] ...
|-----20s-----|    |----15s----|    |-----10s-----|    |-----20s-----|
Total for 2 scenes: ~90s
```

### Optimized Semi-Parallel Model
```
[All TTS Tasks Start] -----------------------------> (Done in ~15s total)
[Scene 1 Image] -> [Scene 2 Image] -> [Scene 3 Image] ...
|-----20s-----|    |-----20s-----|
                   [Scene 1 Video] (Starts immediately after Img 1 + TTS)
                   |-----10s-----|
                                      [Scene 2 Video]
                                      |-----10s-----|
Total for 2 scenes: ~50s (Limited by sequential image generation)
```

## Negative Prompt Integration

To improve image quality without slowing down the pipeline, we implemented native support for `negative_prompt` in the Together.ai API payload.

-   **Previous Approach**: Appending "Avoid deformed hands" to the main prompt. (Ineffective for FLUX).
-   **New Approach**: Passing `"negative_prompt": "..."` in the JSON body.
-   **Result**: Higher yield of usable images, reducing the need for regeneration.