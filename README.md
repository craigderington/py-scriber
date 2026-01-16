# YouTube Caption to Markdown Transcriber

A Python CLI tool that extracts existing captions from YouTube videos and converts them into clean, well-formatted Markdown documents.

## Features

- **Simple Video ID Support** - Use just `dQw4w9WgXcQ` instead of full URLs
- **Clean Output** - Quiet mode with animated spinner, no yt-dlp noise
- **Organized Files** - Auto-saves to `transcriptions/` folder
- **Smart Formatting** - Removes timestamps, combines into paragraphs
- **Global Installation** - Install once with `uv tool install`, use anywhere
- Extracts YouTube video captions/subtitles (both manual and auto-generated)
- Supports both VTT and SRT subtitle formats
- Automatically removes duplicate captions
- Formats video title as H1 header
- Multi-language support (English, Spanish, French, German, Japanese, etc.)
- **AI-Powered Formatting** (Optional) - Use Ollama for smart paragraph detection and executive summaries

## Requirements

- Python 3.8 or higher
- uv (recommended) for installation

## Installation

### Option 1: Install as a Global Tool (Recommended)

Install the `transcribe` command globally using uv:

1. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install from the repository:
```bash
# Clone the repo
git clone <repository-url>
cd yt-dlp-transcriber

# Install as a global tool
uv tool install .
```

3. Use the `transcribe` command anywhere:
```bash
transcribe dQw4w9WgXcQ
transcribe VIDEO_ID -o my-notes.md
```

The `transcribe` command is now available globally on your system!

### Option 2: Run Directly with uv (No Installation)

Run the script directly without installing:

```bash
cd yt-dlp-transcriber
uv run python transcriber.py VIDEO_ID
```

### Option 3: Using pip

1. Navigate to the repository:
```bash
cd yt-dlp-transcriber
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the script:
```bash
python transcriber.py VIDEO_ID
```

## Optional: AI Enhancement with Ollama

For AI-powered summarization and semantic paragraph detection:

### 1. Install Ollama

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Pull a Model

```bash
ollama pull llama3
```

### 3. Use the `--ai` Flag

```bash
transcribe VIDEO_ID --ai
```

### Recommended Models

- **llama3** (default) - Best balance of speed and quality (4.7GB)
- **mistral** - Fast alternative (4.1GB)
- **llama3.1** - More accurate summaries (4.7GB)
- **llama3.2** - Lightweight option for lower-spec systems (2GB)

### AI Features

When you use the `--ai` flag:
- **Executive Summary**: Adds a 2-4 sentence summary at the top of the transcript
- **Better Paragraph Breaks**: Uses semantic understanding to detect topic changes, not just punctuation
- **Graceful Fallback**: If Ollama isn't available, automatically falls back to basic formatting

### Example Output with AI

```markdown
# Video Title

## Executive Summary

This video covers the fundamentals of Python programming, including variables, functions, and data structures. The instructor demonstrates practical examples and explains best practices for writing clean, maintainable code.

---

## Full Transcript

[Semantically-organized paragraphs with better topic detection...]
```

## Usage

If you installed with `uv tool install`, use the `transcribe` command. Otherwise, use `uv run python transcriber.py` or `python transcriber.py`.

### Basic Usage

Extract captions from a YouTube video using just the video ID:
```bash
# If installed as a tool (recommended)
transcribe dQw4w9WgXcQ

# Or with uv run (no installation)
uv run python transcriber.py NOyi6fCWWK8

# Or direct Python
python transcriber.py NOyi6fCWWK8
```

You can also use the full URL if you prefer:
```bash
transcribe "https://www.youtube.com/watch?v=VIDEO_ID"
```

By default, transcripts are saved to a `transcriptions/` folder in your current directory (e.g., `transcriptions/My-Video-Title.md`). The folder is created automatically if it doesn't exist.

### Specify Output File

Save to a specific file or location:
```bash
transcribe dQw4w9WgXcQ -o my-transcript.md
transcribe VIDEO_ID -o ~/Documents/notes.md
```

### Different Language

Extract captions in a different language:
```bash
transcribe VIDEO_ID --language es -o spanish-transcript.md
```

Common language codes:
- `en` - English
- `es` - Spanish
- `fr` - French
- `de` - German
- `ja` - Japanese
- `ko` - Korean
- `pt` - Portuguese

### Keep Speaker Labels

By default, labels like `[Music]`, `[Applause]`, `(laughter)` are removed. To keep them:
```bash
transcribe VIDEO_ID --keep-labels
```

### AI-Enhanced Transcripts

Generate a transcript with AI-powered summary and better paragraph detection:
```bash
# With default model (llama3)
transcribe VIDEO_ID --ai

# With custom model
transcribe VIDEO_ID --ai --ai-model mistral

# Combined with other options
transcribe VIDEO_ID --ai --language es -o spanish-summary.md
```

### Get Help

```bash
transcribe --help
```

## Command-Line Options

```
usage: transcriber.py [-h] [-o OUTPUT] [-l LANGUAGE] [--keep-labels] [--ai] [--ai-model MODEL] url

positional arguments:
  url                   YouTube video URL or video ID

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output Markdown file path (default: auto-generated from video title)
  -l LANGUAGE, --language LANGUAGE
                        Caption language code (default: en)
  --keep-labels         Keep speaker labels like [Music] or [Applause]
  --ai                  Enable AI-powered features (requires Ollama)
  --ai-model MODEL      Ollama model to use (default: llama3)
                        Choices: llama3, llama3.1, llama3.2, mistral, mixtral, gemma, phi3
```

## What You'll See

When you run the tool, you'll see clean, minimal output:

```
⠋ Downloading captions...
Parsing captions...
Formatting as Markdown...
Transcript saved to: transcriptions/Video-Title.md

Done!
```

The animated spinner shows progress during caption download, then you get status messages for each step. No clutter, no noise!

## Managing the Installation

### Update the Tool

To update to the latest version:
```bash
cd yt-dlp-transcriber
git pull
uv tool install --reinstall .
```

### Uninstall

To remove the tool:
```bash
uv tool uninstall yt-dlp-transcriber
```

### List Installed Tools

To see all installed uv tools:
```bash
uv tool list
```

## Example Output

Given a YouTube video about Python programming, the output might look like:

```markdown
# Introduction to Python Programming

Welcome to this tutorial about Python. In this video we'll cover the basics of Python programming including variables functions and data structures.

Let's start with variables. Variables in Python are containers that store data values. You don't need to declare the type of a variable Python figures it out automatically.

Now let's talk about functions. Functions are reusable blocks of code that perform specific tasks. You define a function using the def keyword followed by the function name and parentheses.
```

## How It Works

1. **Download Captions**: Uses yt-dlp in quiet mode to download subtitle files (VTT or SRT format) from YouTube
   - Shows animated spinner during download for visual feedback
   - Suppresses all yt-dlp noise for clean output
2. **Parse Subtitles**: Parses the subtitle file and extracts text while removing:
   - Timestamps
   - Sequence numbers
   - Formatting tags
   - Speaker labels (optional)
   - Position/alignment metadata
3. **Format Markdown**: Combines captions into paragraphs using intelligent detection:
   - Removes duplicate consecutive captions
   - Merges related sentences
   - Creates paragraph breaks at natural stopping points
   - Adds video title as H1 header
4. **Save to File**: Automatically saves to `transcriptions/` folder with video title as filename

## Troubleshooting

### "No captions found"

This error means the video doesn't have captions available. Solutions:
- Try a different video
- Check if captions exist by manually viewing the video on YouTube
- Some videos have captions only in specific languages

### "Failed to download captions"

Possible causes:
- Invalid URL
- Network connection issues
- Video is private or deleted
- Age-restricted or region-locked content

### Missing captions in specific language

If captions aren't available in your requested language:
- Check available languages on YouTube
- Try with `-l en` (English) which is most commonly available
- Some videos only have auto-generated captions in certain languages

## Limitations

- Only works with videos that have captions (manual or auto-generated)
- Cannot transcribe videos without existing captions
- Basic paragraph detection is heuristic-based (use `--ai` for semantic detection)
- Very long videos may take a moment to process
- AI features require Ollama to be installed and running locally

## Future Enhancements

Potential improvements:
- ~~AI-powered formatting with headers and bullet points~~ ✅ Implemented with `--ai` flag
- Section headers and bullet point detection (AI enhancement)
- Batch processing multiple videos
- Export to additional formats (PDF, DOCX)
- Timestamp preservation mode
- GUI/web interface

## License

MIT License - feel free to use and modify as needed.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## Acknowledgments

- Built with [yt-dlp](https://github.com/yt-dlp/yt-dlp) - the excellent YouTube downloader
- AI features powered by [Ollama](https://ollama.ai) - local LLM runtime
