# YouTube Channel Scanner

<p align="left">
  <img src="yt-scanner.png" alt="YT Scanner" width="120">
</p>

[![PyPI version](https://badge.fury.io/py/yt-scanner.svg)](https://badge.fury.io/py/yt-scanner)
[![Python Versions](https://img.shields.io/pypi/pyversions/yt-scanner.svg)](https://pypi.org/project/yt-scanner/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Python script to scan YouTube channel playlists and detect **unlisted** videos.

## Description

This script analyzes a YouTube channel by:

1. Retrieving all public videos from the channel
2. Listing all public playlists
3. Extracting videos from each playlist
4. Comparing both lists to identify videos present in playlists but missing from public videos (= potentially unlisted)

## Installation

### Requirements

- Python 3.7+
- yt-dlp

### Installing yt-dlp

```bash
pip install yt-dlp
```

Or with pipx:

```bash
pipx install yt-dlp
```

## Usage

### Basic command

```bash
python youtube_scanner.py "https://www.youtube.com/@ChannelName"
```

### Available options

| Option             | Description                                                                 |
| ------------------ | --------------------------------------------------------------------------- |
| `-o`, `--output`   | Output JSON filename (default: `youtube_scan_YYYY-MM-DD_HHMMSS.json`)       |
| `--playlists-only` | Scan playlists only (faster, skips public videos)                           |
| `--detailed`       | Fetch detailed metadata for each unlisted video (slower but accurate dates) |

### Examples

**Full scan:**

```bash
python youtube_scanner.py "https://www.youtube.com/@IronKingLoL"
```

**Quick scan (playlists only):**

```bash
python youtube_scanner.py "https://www.youtube.com/@IronKingLoL" --playlists-only
```

**With accurate dates (slower):**

```bash
python youtube_scanner.py "@IronKingLoL" --detailed
```

**With custom filename:**

```bash
python youtube_scanner.py "https://www.youtube.com/@IronKingLoL" -o ironking_scan.json
```

### Supported URL formats

- `https://www.youtube.com/@username`
- `https://www.youtube.com/c/ChannelName`
- `https://www.youtube.com/channel/UCxxxxx`

## Output files

The script generates two files:

### 1. JSON file (`youtube_scan_YYYY-MM-DD_HHMMSS.json`)

Contains all structured data:

```json
{
  "channel_url": "https://www.youtube.com/@example",
  "scan_date": "2025-11-29T14:30:52.123456",
  "public_videos": [],
  "playlist_videos": [],
  "playlists": [],
  "potentially_unlisted": [
    {
      "id": "dQw4w9WgXcQ",
      "title": "Video title",
      "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
      "availability": "unlisted",
      "upload_date": "2024-03-15",
      "found_in_playlist": "Playlist name"
    }
  ]
}
```

### 2. Text file (`youtube_scan_YYYY-MM-DD_HHMMSS_links.txt`)

Simple list of links with dates:

```
# Potentially unlisted videos

[2025-03-16] https://www.youtube.com/watch?v=xxxxx - Video title
[2025-02-11] https://www.youtube.com/watch?v=yyyyy - Another video

# All playlist videos

[2025-03-16] https://www.youtube.com/watch?v=xxxxx - Video title
...
```

## How it works

**Unlisted** videos on YouTube:

- Are not visible on the channel page
- Are not indexed by YouTube search
- **But** can be added to public playlists

This script exploits this behavior: if a video appears in a channel's playlist but not in its public videos, it's likely unlisted.

## Limitations

- **Private videos**: Inaccessible (different from "unlisted")
- **Private playlists**: Not scanned
- **Possible false positives**: A video can be in a playlist without belonging to the channel
- **Deleted videos**: Sometimes appear in playlists but are no longer accessible
- **Rate limiting**: YouTube may throttle requests if too frequent
- **Approximate dates**: By default, dates are approximate (extracted from "X months ago"). Use `--detailed` for exact dates (slower)
- **Availability field**: May show as "NA" in fast mode; use `--detailed` to get accurate availability status

## Troubleshooting

### "yt-dlp is not installed"

```bash
pip install yt-dlp
```

### Timeout on large channels

The script has a 5-minute timeout per command. For very large channels, use `--playlists-only` to reduce scan time.

### No unlisted videos found

This is normal if:

- The channel has no unlisted videos in its playlists
- All playlists are private
- The channel has no playlists

## Author

**Thomas Lamarche** - _Initial work_ - [OloZ17](https://github.com/OloZ17)

## License

MIT License - Free to use and modify.

## Contributing

Contributions are welcome! Feel free to open an issue or pull request.
