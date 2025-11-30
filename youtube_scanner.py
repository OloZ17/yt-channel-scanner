#!/usr/bin/env python3
"""
YouTube Channel Scanner
Scans YouTube channel playlists to extract all video links,
including unlisted videos that may be in public playlists.
"""

import subprocess
import json
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any, Optional, Union


def run_ytdlp(args: List[str]) -> str:
    """Execute yt-dlp with the given arguments."""
    cmd = ["yt-dlp"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.stdout
    except subprocess.TimeoutExpired:
        print("Timeout - command took too long")
        return ""
    except FileNotFoundError:
        print("yt-dlp is not installed. Install it with: pip install yt-dlp")
        sys.exit(1)


def get_channel_playlists(channel_url: str) -> List[Dict[str, Any]]:
    """Retrieve all playlists from a channel."""
    print("Searching for channel playlists...")

    # Get playlists (flat-playlist is OK here, we only need playlist metadata)
    playlists_url = channel_url.rstrip('/') + "/playlists"
    output = run_ytdlp([
        "--flat-playlist",
        "--print", "%(id)s|||%(title)s",
        playlists_url
    ])

    playlists = []
    for line in output.strip().split('\n'):
        if '|||' in line:
            pl_id, title = line.split('|||', 1)
            playlists.append({
                'id': pl_id,
                'title': title,
                'url': f"https://www.youtube.com/playlist?list={pl_id}"
            })

    return playlists


def format_date(date_raw: Union[str, int, None] = "NA", timestamp: Union[str, int, None] = "NA") -> str:
    """Format date from YYYYMMDD to YYYY-MM-DD or convert timestamp."""
    # Ensure we have strings
    date_str = str(date_raw) if date_raw is not None else "NA"
    ts_str = str(timestamp) if timestamp is not None else "NA"

    if date_str and date_str != "NA" and date_str != "None":
        if len(date_str) == 8:
            return f"{date_str[0:4]}-{date_str[4:6]}-{date_str[6:8]}"

    if ts_str and ts_str != "NA" and ts_str != "None":
        try:
            ts = int(ts_str)
            if ts > 0:
                return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            pass

    # Return original date_raw if it's not "NA", otherwise return "NA"
    if date_str and date_str not in ("NA", "None"):
        return date_str

    return "NA"


def format_video_line(video: Dict[str, Any]) -> str:
    """Format a video entry as a text line."""
    date = str(video.get('upload_date', 'N/A'))
    url = str(video.get('url', ''))
    title = str(video.get('title', ''))
    return f"[{date}] {url} - {title}\n"


def _get_field(parts: List[str], index: int, default: str = "NA") -> str:
    """Safely get field from parts list."""
    return parts[index] if len(parts) > index else default


def _extract_date_fields(parts: List[str], include_availability: bool) -> tuple:
    """Extract date-related fields from parts based on availability flag."""
    offset = 3 if include_availability else 2

    upload_date_raw = _get_field(parts, offset)
    timestamp = _get_field(parts, offset + 1)
    release_date = _get_field(parts, offset + 2)
    release_timestamp = _get_field(parts, offset + 3)

    return upload_date_raw, timestamp, release_date, release_timestamp


def _get_best_date(upload_date_raw: str, timestamp: str, release_date: str, release_timestamp: str) -> str:
    """Get the best available date from upload_date or release_date."""
    # Ensure all inputs are strings
    upload_date = format_date(str(upload_date_raw), str(timestamp))
    if upload_date == "NA":
        upload_date = format_date(str(release_date), str(release_timestamp))
    return upload_date


def parse_video_entry(parts: List[str], include_availability: bool = True) -> Dict[str, Any]:
    """Parse video data from yt-dlp output parts."""
    video_id = parts[0] if len(parts) > 0 else ""
    title = parts[1] if len(parts) > 1 else ""

    if include_availability:
        availability = parts[2] if len(parts) > 2 else "unknown"
    else:
        availability = "public"

    upload_date_raw, timestamp, release_date, release_timestamp = _extract_date_fields(parts, include_availability)
    upload_date = _get_best_date(upload_date_raw, timestamp, release_date, release_timestamp)

    return {
        'id': video_id,
        'title': title,
        'url': f"https://www.youtube.com/watch?v={video_id}",
        'availability': availability,
        'upload_date': upload_date
    }


def get_playlist_videos(playlist_url: str) -> List[Dict[str, Any]]:
    """Retrieve all videos from a playlist."""
    output = run_ytdlp([
        "--skip-download",
        "--ignore-errors",
        "--print", "%(id)s|||%(title)s|||%(availability)s|||%(upload_date)s|||%(timestamp)s|||%(release_date)s|||%(release_timestamp)s",
        playlist_url
    ])

    videos: List[Dict[str, Any]] = []
    for line in output.strip().split('\n'):
        if '|||' in line:
            parts = line.split('|||')
            if len(parts) >= 2:
                videos.append(parse_video_entry(parts, include_availability=True))

    return videos


def get_channel_videos(channel_url: str) -> List[Dict[str, Any]]:
    """Retrieve public videos from the channel (Videos tab)."""
    print("🔍 Retrieving public videos from channel...")

    videos_url = channel_url.rstrip('/') + "/videos"
    output = run_ytdlp([
        "--skip-download",
        "--ignore-errors",
        "--print", "%(id)s|||%(title)s|||%(upload_date)s|||%(timestamp)s|||%(release_date)s|||%(release_timestamp)s",
        videos_url
    ])

    videos: List[Dict[str, Any]] = []
    for line in output.strip().split('\n'):
        if '|||' in line:
            parts = line.split('|||')
            if len(parts) >= 2:
                videos.append(parse_video_entry(parts, include_availability=False))

    return videos


def get_video_details(video_id: str) -> Dict[str, Any]:
    """Fetch detailed metadata for a single video."""
    output = run_ytdlp([
        "--skip-download",
        "--print", "%(id)s|||%(title)s|||%(availability)s|||%(upload_date)s",
        f"https://www.youtube.com/watch?v={video_id}"
    ])

    if '|||' in output:
        parts = output.strip().split('|||')
        upload_date_raw = parts[3] if len(parts) > 3 else "NA"
        upload_date = format_date(str(upload_date_raw))

        return {
            'availability': parts[2] if len(parts) > 2 else "unknown",
            'upload_date': upload_date
        }
    return {}


def _scan_all_playlists(playlists: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Scan all playlists and collect unique videos."""
    all_playlist_videos: Dict[str, Dict[str, Any]] = {}

    for i, playlist in enumerate(playlists, 1):
        title = str(playlist.get('title', ''))[:50]
        print(f"Scanning playlist {i}/{len(playlists)}: {title}...")
        playlist_url = str(playlist.get('url', ''))
        videos = get_playlist_videos(playlist_url)

        for video in videos:
            video['found_in_playlist'] = playlist.get('title', '')
            video_id = str(video.get('id', ''))
            if video_id and video_id not in all_playlist_videos:
                all_playlist_videos[video_id] = video

    return all_playlist_videos


def _identify_unlisted_videos(
    all_playlist_videos: Dict[str, Dict[str, Any]],
    public_ids: set
) -> List[Dict[str, Any]]:
    """Identify videos that are in playlists but not in public videos."""
    potentially_unlisted = []

    print("\n🔍 Analyzing videos...")
    print(f"   Total videos in playlists: {len(all_playlist_videos)}")
    print(f"   Total public videos: {len(public_ids)}")

    for video_id, video in all_playlist_videos.items():
        if video_id not in public_ids:
            video['reason'] = "In playlist but not in public videos"
            potentially_unlisted.append(video)
            # Show availability if present
            availability = video.get('availability', 'unknown')
            title = str(video.get('title', ''))[:50]
            print(f"   ✓ Found: {title} (availability: {availability})")

    return potentially_unlisted


def _fetch_detailed_metadata(videos: List[Dict[str, Any]]) -> None:
    """Fetch detailed metadata for a list of videos."""
    print(f"📥 Fetching detailed metadata for {len(videos)} videos...")

    for i, video in enumerate(videos, 1):
        video_dict = dict(video) if isinstance(video, dict) else {}
        title = str(video_dict.get('title', ''))[:40]
        print(f"   [{i}/{len(videos)}] {title}...")
        video_id = str(video_dict.get('id', ''))
        if video_id:
            details = get_video_details(video_id)
            if details and isinstance(video, dict):
                video.update(details)


def scan_channel(channel_url: str, include_public: bool = True, detailed: bool = False) -> Dict[str, Any]:
    """Scan a complete YouTube channel."""
    results: Dict[str, Any] = {
        'channel_url': channel_url,
        'scan_date': datetime.now().isoformat(),
        'public_videos': [],
        'playlist_videos': [],
        'playlists': [],
        'potentially_unlisted': []
    }

    # 1. Get public videos
    public_ids: set = set()
    if include_public:
        public_videos = get_channel_videos(channel_url)
        results['public_videos'] = public_videos
        public_ids = {v['id'] for v in public_videos}
        print(f"✓ {len(public_videos)} public videos found")
        if public_videos and len(public_videos) > 0:
            print(f"   Sample: {public_videos[0].get('title', 'N/A')[:50]}")

    # 2. Get playlists
    playlists = get_channel_playlists(channel_url)
    results['playlists'] = playlists
    print(f"\n✓ {len(playlists)} playlists found")
    for pl in playlists[:3]:  # Show first 3
        print(f"   - {pl.get('title', 'N/A')}")

    # 3. Scan each playlist
    print("")
    all_playlist_videos = _scan_all_playlists(playlists)
    results['playlist_videos'] = list(all_playlist_videos.values())
    print(f"\n✓ {len(all_playlist_videos)} unique videos found in playlists")

    # 4. Identify potentially unlisted videos
    if include_public:
        potentially_unlisted = _identify_unlisted_videos(all_playlist_videos, public_ids)
        results['potentially_unlisted'] = potentially_unlisted
        print(f"\n✓ {len(potentially_unlisted)} potentially unlisted videos found")

        # Fetch detailed metadata if requested
        if detailed and potentially_unlisted:
            _fetch_detailed_metadata(potentially_unlisted)

    return results


def print_results(results: Dict[str, Any]) -> None:
    """Display results in a readable format."""
    print("\n" + "=" * 60)
    print("SCAN RESULTS")
    print("=" * 60)

    public_videos: List[Any] = results.get('public_videos', [])
    playlists: List[Any] = results.get('playlists', [])
    playlist_videos: List[Any] = results.get('playlist_videos', [])
    potentially_unlisted: List[Any] = results.get('potentially_unlisted', [])

    print(f"\nPublic videos: {len(public_videos)}")
    print(f"Playlists scanned: {len(playlists)}")
    print(f"Videos in playlists: {len(playlist_videos)}")
    print(f"Potentially unlisted: {len(potentially_unlisted)}")

    if potentially_unlisted:
        print("\n" + "-" * 60)
        print("POTENTIALLY UNLISTED VIDEOS:")
        print("-" * 60)
        for video in potentially_unlisted:
            if isinstance(video, dict):
                title = str(video.get('title', 'Unknown'))[:60]
                url = str(video.get('url', 'N/A'))
                upload_date = str(video.get('upload_date', 'N/A'))
                found_in = str(video.get('found_in_playlist', 'N/A'))
                print(f"\n  📹 {title}")
                print(f"     URL: {url}")
                print(f"     Date: {upload_date}")
                print(f"     Found in: {found_in}")


def save_results(results: Dict[str, Any], filename: str) -> None:
    """Save results to JSON file."""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to: {filename}")


def get_default_filename():
    """Generate a filename with current date."""
    date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return f"youtube_scan_{date_str}.json"


def main():
    parser = argparse.ArgumentParser(
        description="Scan a YouTube channel to find unlisted videos"
    )
    parser.add_argument(
        "channel_url",
        help="YouTube channel URL (e.g., https://www.youtube.com/@username)"
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output JSON file (default: youtube_scan_YYYY-MM-DD_HHMMSS.json)"
    )
    parser.add_argument(
        "--playlists-only",
        action="store_true",
        help="Scan playlists only (faster)"
    )
    parser.add_argument(
        "--detailed",
        action="store_true",
        help="Fetch detailed metadata for each video (slower but more accurate dates)"
    )

    args = parser.parse_args()

    # Set filename with date if not specified
    output_file = args.output if args.output else get_default_filename()

    print("YouTube Channel Scanner")
    print("=" * 60)
    print(f"Channel: {args.channel_url}")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(
        f"Mode: {'Detailed' if args.detailed else 'Fast'} | {'Playlists only' if args.playlists_only else 'Full scan'}")
    print("=" * 60 + "\n")

    # Scan the channel
    results = scan_channel(
        args.channel_url,
        include_public=not args.playlists_only,
        detailed=args.detailed
    )

    # Display and save
    print_results(results)
    save_results(results, output_file)

    # Also create a simple text file with links
    links_file = output_file.replace('.json', '_links.txt')
    with open(links_file, 'w', encoding='utf-8') as f:
        f.write("# Potentially unlisted videos\n\n")
        for video in results.get('potentially_unlisted', []):
            if isinstance(video, dict):
                f.write(format_video_line(video))

        f.write("\n\n# All playlist videos\n\n")
        for video in results.get('playlist_videos', []):
            if isinstance(video, dict):
                f.write(format_video_line(video))

    print(f"Links saved to: {links_file}")


if __name__ == "__main__":
    main()