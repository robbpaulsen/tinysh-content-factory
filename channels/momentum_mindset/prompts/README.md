# Prompts for MomentumMindset Channel

This directory contains custom prompts for AI generation.

## Files

### script.txt
Gemini prompt for generating motivational speeches from Reddit stories.

Variables available:
- `{story}` - The Reddit story text
- `{content_type}` - From channel config ("motivational speech")
- `{topics}` - List of topics from config

### image.txt
FLUX prompt for generating scene images.

Variables available:
- `{image_prompt}` - Scene description from Gemini
- `{art_style}` - From channel config

### seo.txt
Gemini prompt for generating SEO-optimized metadata.

Variables available:
- `{video_title}` - Original title from script
- `{video_description}` - Original description
- `{script_text}` - Full video script
- `{channel_name}` - From SEO config
- `{target_audience}` - From SEO config

## Usage

If these files don't exist, the system will use default prompts from the codebase.
Create these files to customize prompts for this specific channel.
