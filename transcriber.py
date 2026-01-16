#!/usr/bin/env python3
"""
YouTube Caption to Markdown Transcriber
Extracts captions from YouTube videos and converts them to clean Markdown.
"""

import argparse
import os
import re
import sys
import tempfile
import threading
import time
from pathlib import Path
import yt_dlp


class Spinner:
    """Simple loading spinner for console output."""

    def __init__(self, message="Loading"):
        self.message = message
        self.running = False
        self.thread = None
        self.spinner_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def _spin(self):
        """Run the spinner animation."""
        idx = 0
        while self.running:
            char = self.spinner_chars[idx % len(self.spinner_chars)]
            sys.stdout.write(f"\r{char} {self.message}...")
            sys.stdout.flush()
            idx += 1
            time.sleep(0.1)

    def start(self):
        """Start the spinner in a background thread."""
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()

    def stop(self, final_message=None):
        """Stop the spinner and optionally print a final message."""
        self.running = False
        if self.thread:
            self.thread.join()
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")  # Clear the line
        if final_message:
            print(final_message)
        sys.stdout.flush()


class SubtitleParser:
    """Parse VTT and SRT subtitle formats."""

    # Regex patterns
    VTT_TIMESTAMP_PATTERN = re.compile(r'^\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}.*$')
    SRT_TIMESTAMP_PATTERN = re.compile(r'^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}.*$')
    SRT_NUMBER_PATTERN = re.compile(r'^\d+$')
    VTT_HEADER_PATTERN = re.compile(r'^WEBVTT.*$')
    VTT_NOTE_PATTERN = re.compile(r'^NOTE.*$')
    VTT_CUE_SETTINGS = re.compile(r'\s*(align|position|size|line|vertical):[^\s]+', re.IGNORECASE)

    @staticmethod
    def parse_vtt(content: str, keep_labels: bool = False) -> list:
        """Parse WebVTT format subtitles."""
        lines = content.split('\n')
        captions = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines, WEBVTT header, NOTE blocks
            if not line or SubtitleParser.VTT_HEADER_PATTERN.match(line) or SubtitleParser.VTT_NOTE_PATTERN.match(line):
                i += 1
                continue

            # Check if it's a timestamp line
            if SubtitleParser.VTT_TIMESTAMP_PATTERN.match(line):
                i += 1
                # Collect caption text (can be multiple lines)
                caption_text = []
                while i < len(lines) and lines[i].strip() and not SubtitleParser.VTT_TIMESTAMP_PATTERN.match(lines[i].strip()):
                    text = lines[i].strip()
                    # Remove VTT formatting tags like <c>, <v>, etc.
                    text = re.sub(r'<[^>]+>', '', text)
                    # Remove speaker labels if requested
                    if not keep_labels:
                        text = re.sub(r'\[.*?\]', '', text)
                        text = re.sub(r'\(.*?\)', '', text)
                    caption_text.append(text)
                    i += 1

                if caption_text:
                    captions.append(' '.join(caption_text).strip())
            else:
                i += 1

        return captions

    @staticmethod
    def parse_srt(content: str, keep_labels: bool = False) -> list:
        """Parse SubRip (SRT) format subtitles."""
        lines = content.split('\n')
        captions = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines and sequence numbers
            if not line or SubtitleParser.SRT_NUMBER_PATTERN.match(line):
                i += 1
                continue

            # Check if it's a timestamp line
            if SubtitleParser.SRT_TIMESTAMP_PATTERN.match(line):
                i += 1
                # Collect caption text (can be multiple lines)
                caption_text = []
                while i < len(lines) and lines[i].strip() and not SubtitleParser.SRT_NUMBER_PATTERN.match(lines[i].strip()):
                    text = lines[i].strip()
                    # Remove HTML-like tags
                    text = re.sub(r'<[^>]+>', '', text)
                    # Remove speaker labels if requested
                    if not keep_labels:
                        text = re.sub(r'\[.*?\]', '', text)
                        text = re.sub(r'\(.*?\)', '', text)
                    caption_text.append(text)
                    i += 1

                if caption_text:
                    captions.append(' '.join(caption_text).strip())
            else:
                i += 1

        return captions

    @staticmethod
    def parse(content: str, keep_labels: bool = False) -> list:
        """Auto-detect format and parse subtitles."""
        if 'WEBVTT' in content[:100]:
            return SubtitleParser.parse_vtt(content, keep_labels)
        else:
            return SubtitleParser.parse_srt(content, keep_labels)


class AIProcessor:
    """Process captions using Ollama for semantic understanding."""

    def __init__(self, model='llama3', enabled=True):
        self.model = model
        self.enabled = enabled
        self.ollama_available = self._check_ollama()

    def _check_ollama(self):
        """Check if Ollama is installed and running."""
        if not self.enabled:
            return False

        try:
            import ollama
            # Test connection with a simple list call
            ollama.list()
            return True
        except ImportError:
            print("Warning: ollama library not installed. Install with: pip install ollama")
            return False
        except Exception as e:
            print(f"Warning: Ollama not available ({str(e)}). Falling back to basic formatting.")
            return False

    def generate_summary(self, full_text: str) -> str:
        """Generate executive summary using Ollama."""
        if not self.ollama_available:
            return ""

        try:
            import ollama

            prompt = f"""You are a professional transcript summarizer. Generate a concise executive summary of the following video transcript.

Your summary should:
- Be 2-4 sentences maximum
- Capture the main topic and key points
- Be written in present tense
- Focus on what the video covers, not who is speaking

Transcript:
{full_text[:3000]}

Summary:"""

            spinner = Spinner("Generating AI summary")
            spinner.start()

            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.3,
                    'num_predict': 200,
                }
            )

            spinner.stop()
            summary = response['response'].strip()
            return summary

        except Exception as e:
            print(f"Warning: Failed to generate summary ({str(e)})")
            return ""

    def detect_paragraph_breaks(self, captions: list) -> list:
        """Use AI to detect semantic paragraph breaks."""
        if not self.ollama_available or len(captions) < 5:
            return self._basic_paragraph_breaks(captions)

        try:
            import ollama

            # Join all captions into one text
            full_text = ' '.join(captions)

            # For very long texts, chunk them
            if len(full_text) > 8000:
                return self._chunked_paragraph_detection(captions)

            prompt = f"""You are analyzing a video transcript. Insert paragraph breaks at semantically meaningful points (topic changes, major transitions).

Rules:
- Insert <BREAK> markers where natural paragraph breaks should occur
- Keep existing text exactly as-is
- Only add <BREAK> markers, don't modify content
- Aim for paragraphs of 3-6 sentences
- Break at topic transitions, not mid-thought

Text:
{full_text}

Output the text with <BREAK> markers inserted:"""

            spinner = Spinner("Detecting paragraph breaks with AI")
            spinner.start()

            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                options={
                    'temperature': 0.2,
                    'num_predict': len(full_text) + 500,
                }
            )

            spinner.stop()

            # Parse the response to extract paragraphs
            processed_text = response['response'].strip()
            paragraphs = [p.strip() for p in processed_text.split('<BREAK>') if p.strip()]

            # Validate output (fallback if AI output is malformed)
            if len(paragraphs) < 2 or sum(len(p) for p in paragraphs) < len(full_text) * 0.7:
                print("Warning: AI paragraph detection produced unexpected output, using fallback")
                return self._basic_paragraph_breaks(captions)

            return paragraphs

        except Exception as e:
            print(f"Warning: AI paragraph detection failed ({str(e)}), using fallback")
            return self._basic_paragraph_breaks(captions)

    def _chunked_paragraph_detection(self, captions: list) -> list:
        """Process very long transcripts in chunks."""
        chunk_size = 100
        chunks = [captions[i:i + chunk_size] for i in range(0, len(captions), chunk_size)]

        all_paragraphs = []
        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)}...")
            chunk_paragraphs = self.detect_paragraph_breaks(chunk)
            all_paragraphs.extend(chunk_paragraphs)

        return all_paragraphs

    def _basic_paragraph_breaks(self, captions: list) -> list:
        """Fallback to basic heuristic paragraph detection."""
        paragraphs = []
        current_paragraph = []

        for i, caption in enumerate(captions):
            current_paragraph.append(caption)

            ends_with_sentence = caption and caption[-1] in '.!?'
            is_last = i == len(captions) - 1
            next_starts_with_capital = False
            if not is_last and captions[i + 1]:
                next_starts_with_capital = captions[i + 1][0].isupper()

            if (ends_with_sentence and next_starts_with_capital) or is_last:
                paragraph_text = ' '.join(current_paragraph)
                paragraph_text = re.sub(r'\s+', ' ', paragraph_text).strip()
                if paragraph_text:
                    paragraphs.append(paragraph_text)
                current_paragraph = []

        return paragraphs

    def _remove_duplicates(self, captions: list) -> list:
        """Remove duplicate consecutive captions."""
        cleaned = []
        prev_caption = None

        for caption in captions:
            if not caption.strip():
                continue

            normalized = re.sub(r'[^\w\s]', '', caption.lower())
            prev_normalized = re.sub(r'[^\w\s]', '', prev_caption.lower()) if prev_caption else None

            if prev_normalized and normalized == prev_normalized:
                continue

            cleaned.append(caption.strip())
            prev_caption = caption

        return cleaned

    def process(self, captions: list, video_title: str = None) -> dict:
        """
        Process captions with AI to generate summary and detect paragraphs.

        Returns:
            dict with keys:
                - 'paragraphs': list of paragraph strings
                - 'summary': executive summary string (empty if disabled)
                - 'title': video title
        """
        # First, clean captions (remove duplicates)
        cleaned_captions = self._remove_duplicates(captions)

        # Generate paragraphs (with or without AI)
        if self.ollama_available:
            paragraphs = self.detect_paragraph_breaks(cleaned_captions)
        else:
            paragraphs = self._basic_paragraph_breaks(cleaned_captions)

        # Generate summary if enabled
        summary = ""
        if self.ollama_available:
            full_text = ' '.join(paragraphs)
            summary = self.generate_summary(full_text)

        return {
            'paragraphs': paragraphs,
            'summary': summary,
            'title': video_title
        }


class MarkdownFormatter:
    """Format captions as clean Markdown with optional AI enhancements."""

    @staticmethod
    def format(captions: list, title: str = None, ai_data: dict = None) -> str:
        """
        Convert captions or AI-processed data to formatted Markdown.

        Args:
            captions: Raw caption list (used if ai_data is None)
            title: Video title
            ai_data: Dict with 'paragraphs' and 'summary' from AIProcessor

        Returns:
            Formatted Markdown string
        """
        if ai_data:
            # Use AI-processed data
            paragraphs = ai_data.get('paragraphs', [])
            summary = ai_data.get('summary', '')
            title = ai_data.get('title', title)
        else:
            # Fallback to basic processing
            paragraphs = MarkdownFormatter._basic_format(captions)
            summary = ''

        if not paragraphs:
            return ""

        # Build final Markdown
        markdown_lines = []

        # Add title if provided
        if title:
            markdown_lines.append(f"# {title}")
            markdown_lines.append("")

        # Add executive summary if available
        if summary:
            markdown_lines.append("## Executive Summary")
            markdown_lines.append("")
            markdown_lines.append(summary)
            markdown_lines.append("")
            markdown_lines.append("---")
            markdown_lines.append("")
            markdown_lines.append("## Full Transcript")
            markdown_lines.append("")

        # Add paragraphs
        for paragraph in paragraphs:
            markdown_lines.append(paragraph)
            markdown_lines.append("")

        return '\n'.join(markdown_lines).strip()

    @staticmethod
    def _basic_format(captions: list) -> list:
        """Basic paragraph formatting (original logic)."""
        if not captions:
            return []

        # Remove empty captions and clean up
        captions = [cap.strip() for cap in captions if cap.strip()]

        # Remove duplicate consecutive captions (common in auto-generated captions)
        cleaned_captions = []
        prev_caption = None
        for caption in captions:
            # Normalize for comparison (lowercase, no punctuation)
            normalized = re.sub(r'[^\w\s]', '', caption.lower())
            prev_normalized = re.sub(r'[^\w\s]', '', prev_caption.lower()) if prev_caption else None

            # Skip if too similar to previous caption
            if prev_normalized and normalized == prev_normalized:
                continue

            cleaned_captions.append(caption)
            prev_caption = caption

        # Merge captions into paragraphs
        # Simple strategy: merge all consecutive captions into one paragraph
        # Add paragraph break on sentence endings followed by capital letters
        paragraphs = []
        current_paragraph = []

        for i, caption in enumerate(cleaned_captions):
            current_paragraph.append(caption)

            # Check if this caption ends with sentence-ending punctuation
            ends_with_sentence = caption and caption[-1] in '.!?'

            # Check if next caption starts with capital letter or is last caption
            is_last = i == len(cleaned_captions) - 1
            next_starts_with_capital = False
            if not is_last and cleaned_captions[i + 1]:
                next_starts_with_capital = cleaned_captions[i + 1][0].isupper()

            # Create paragraph break if sentence ends and next starts with capital
            if (ends_with_sentence and next_starts_with_capital) or is_last:
                # Join current paragraph
                paragraph_text = ' '.join(current_paragraph)
                # Clean up extra spaces
                paragraph_text = re.sub(r'\s+', ' ', paragraph_text).strip()
                if paragraph_text:
                    paragraphs.append(paragraph_text)
                current_paragraph = []

        return paragraphs


class YouTubeTranscriber:
    """Main transcriber class."""

    def __init__(self, language='en', keep_labels=False, use_ai=False, ai_model='llama3'):
        self.language = language
        self.keep_labels = keep_labels
        self.use_ai = use_ai
        self.ai_processor = AIProcessor(model=ai_model, enabled=use_ai)

    def download_captions(self, url: str, output_dir: str = None) -> tuple:
        """
        Download captions from YouTube video.
        Returns: (subtitle_file_path, video_title)
        """
        if output_dir is None:
            output_dir = tempfile.mkdtemp()

        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': [self.language],
            'subtitlesformat': 'vtt/srt',
            'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
        }

        spinner = Spinner("Downloading captions")
        try:
            spinner.start()
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)

                video_title = info.get('title', 'Untitled')
                spinner.stop()

                # Find the downloaded subtitle file
                subtitle_file = None
                for ext in ['.vtt', '.srt']:
                    potential_file = os.path.join(output_dir, f"{video_title}{ext}")
                    if os.path.exists(potential_file):
                        subtitle_file = potential_file
                        break

                    # Try with language code
                    potential_file = os.path.join(output_dir, f"{video_title}.{self.language}{ext}")
                    if os.path.exists(potential_file):
                        subtitle_file = potential_file
                        break

                if not subtitle_file:
                    # Search for any subtitle file in the directory
                    for file in os.listdir(output_dir):
                        if file.endswith(('.vtt', '.srt')):
                            subtitle_file = os.path.join(output_dir, file)
                            break

                if not subtitle_file:
                    raise Exception("No captions found. This video may not have captions available.")

                return subtitle_file, video_title

        except Exception as e:
            spinner.stop()
            raise Exception(f"Failed to download captions: {str(e)}")

    def transcribe(self, url: str, output_file: str = None) -> str:
        """
        Main transcription method.
        Downloads captions and converts to Markdown.
        """
        temp_dir = tempfile.mkdtemp()

        try:
            # Download captions
            subtitle_file, video_title = self.download_captions(url, temp_dir)

            # Read subtitle file
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                subtitle_content = f.read()

            # Parse subtitles
            print("Parsing captions...")
            captions = SubtitleParser.parse(subtitle_content, self.keep_labels)

            # Process with AI if enabled
            if self.use_ai:
                ai_data = self.ai_processor.process(captions, video_title)
                markdown = MarkdownFormatter.format(None, video_title, ai_data=ai_data)
            else:
                # Basic formatting
                print("Formatting as Markdown...")
                markdown = MarkdownFormatter.format(captions, video_title, ai_data=None)

            # Save to file or return
            if output_file:
                output_path = Path(output_file)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                print(f"Transcript saved to: {output_file}")
            else:
                # Generate filename from video title and save to transcriptions folder
                safe_title = re.sub(r'[^\w\s-]', '', video_title)
                safe_title = re.sub(r'[-\s]+', '-', safe_title)

                # Create transcriptions directory if it doesn't exist
                transcriptions_dir = Path("transcriptions")
                transcriptions_dir.mkdir(exist_ok=True)

                output_file = transcriptions_dir / f"{safe_title}.md"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(markdown)
                print(f"Transcript saved to: {output_file}")

            return markdown

        finally:
            # Cleanup temp files
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)


def normalize_youtube_url(url_or_id: str) -> str:
    """
    Convert a YouTube video ID or URL to a standard YouTube URL.

    Accepts:
    - Video ID: "dQw4w9WgXcQ"
    - Full URL: "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    - Short URL: "https://youtu.be/dQw4w9WgXcQ"

    Returns: Standard YouTube URL
    """
    url_or_id = url_or_id.strip()

    # If it's already a URL, return as-is
    if url_or_id.startswith('http://') or url_or_id.startswith('https://'):
        return url_or_id

    # If it looks like a bare video ID (typically 11 chars, alphanumeric + - and _)
    # Just prepend the YouTube watch URL
    if re.match(r'^[a-zA-Z0-9_-]+$', url_or_id):
        return f"https://www.youtube.com/watch?v={url_or_id}"

    # Otherwise, assume it's a URL without protocol
    if 'youtube.com' in url_or_id or 'youtu.be' in url_or_id:
        return f"https://{url_or_id}"

    # Last resort: treat as video ID
    return f"https://www.youtube.com/watch?v={url_or_id}"


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Extract YouTube video captions and convert to Markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s dQw4w9WgXcQ
  %(prog)s NOyi6fCWWK8 -o transcript.md
  %(prog)s https://www.youtube.com/watch?v=VIDEO_ID
  %(prog)s https://youtu.be/VIDEO_ID -o transcript.md
  %(prog)s VIDEO_ID --language es -o spanish-transcript.md
        """
    )

    parser.add_argument(
        'url',
        help='YouTube video URL or video ID'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output Markdown file path (default: auto-generated from video title)',
        default=None
    )

    parser.add_argument(
        '-l', '--language',
        help='Caption language code (default: en)',
        default='en'
    )

    parser.add_argument(
        '--keep-labels',
        help='Keep speaker labels like [Music] or [Applause]',
        action='store_true'
    )

    parser.add_argument(
        '--ai',
        help='Enable AI-powered summarization and paragraph formatting (requires Ollama)',
        action='store_true'
    )

    parser.add_argument(
        '--ai-model',
        help='Ollama model to use for AI processing (default: llama3)',
        default='llama3',
        choices=['llama3', 'llama3.1', 'llama3.2', 'mistral', 'mixtral', 'gemma', 'phi3']
    )

    args = parser.parse_args()

    # Validate URL
    if not args.url:
        parser.print_help()
        sys.exit(1)

    try:
        # Normalize URL or video ID to full YouTube URL
        youtube_url = normalize_youtube_url(args.url)

        transcriber = YouTubeTranscriber(
            language=args.language,
            keep_labels=args.keep_labels,
            use_ai=args.ai,
            ai_model=args.ai_model
        )

        transcriber.transcribe(youtube_url, args.output)
        print("\nDone!")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
