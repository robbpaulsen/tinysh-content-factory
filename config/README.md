# Configuration Directory

This directory contains all configuration files for the project.

## Files

### `profiles.yaml`
Voice and music profile configurations. Edit this file to:
- Add new voice profiles (TTS engine, voice samples, parameters)
- Configure music playlists with rotation modes (random/sequential)
- Set default profile for video generation

Example structure:
```yaml
profiles:
  profile_name:
    voice:
      engine: chatterbox  # or kokoro
      sample_path: "path/to/voice.mp3"
    music:
      playlist:
        - path: "path/to/track.mp3"
      volume: 0.1
      rotation: random

default_profile: profile_name
```

### `.env.example` (reference)
A copy of the main `.env.example` for reference. The actual `.env` file should be in the project root.

## Usage

Set active profile in `.env`:
```bash
ACTIVE_PROFILE=your_profile_name
PROFILES_PATH=config/profiles.yaml
```

Or use CLI flag:
```bash
python -m src.main generate --profile your_profile_name
```
