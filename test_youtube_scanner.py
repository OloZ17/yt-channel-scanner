"""
Unit tests for YouTube Channel Scanner
"""

import unittest
from unittest.mock import patch, MagicMock, mock_open, call
import subprocess
import json
from datetime import datetime
import youtube_scanner


class TestRunYtdlp(unittest.TestCase):
    """Tests for run_ytdlp function."""

    @patch('subprocess.run')
    def test_run_ytdlp_success(self, mock_run):
        """Test successful yt-dlp execution."""
        mock_run.return_value = MagicMock(stdout="output data")
        result = youtube_scanner.run_ytdlp(["--version"])

        self.assertEqual(result, "output data")
        mock_run.assert_called_once_with(
            ["yt-dlp", "--version"],
            capture_output=True,
            text=True,
            timeout=300
        )

    @patch('subprocess.run')
    def test_run_ytdlp_timeout(self, mock_run):
        """Test yt-dlp timeout handling."""
        mock_run.side_effect = subprocess.TimeoutExpired("yt-dlp", 300)
        result = youtube_scanner.run_ytdlp(["--version"])

        self.assertEqual(result, "")

    @patch('subprocess.run')
    @patch('sys.exit')
    def test_run_ytdlp_not_found(self, mock_exit, mock_run):
        """Test yt-dlp not installed."""
        mock_run.side_effect = FileNotFoundError()
        youtube_scanner.run_ytdlp(["--version"])

        mock_exit.assert_called_once_with(1)


class TestFormatDate(unittest.TestCase):
    """Tests for format_date function."""

    def test_format_date_yyyymmdd(self):
        """Test formatting YYYYMMDD date."""
        result = youtube_scanner.format_date("20231225", "NA")
        self.assertEqual(result, "2023-12-25")

    def test_format_date_with_timestamp(self):
        """Test formatting with timestamp fallback."""
        result = youtube_scanner.format_date("NA", "1703548800")
        expected = datetime.fromtimestamp(1703548800).strftime("%Y-%m-%d")
        self.assertEqual(result, expected)

    def test_format_date_invalid_timestamp(self):
        """Test invalid timestamp handling."""
        result = youtube_scanner.format_date("NA", "invalid")
        self.assertEqual(result, "NA")

    def test_format_date_none_values(self):
        """Test None values."""
        result = youtube_scanner.format_date(None, None)
        self.assertEqual(result, "NA")

    def test_format_date_short_date(self):
        """Test date string that's too short."""
        result = youtube_scanner.format_date("2023", "NA")
        self.assertEqual(result, "2023")

    def test_format_date_empty_string(self):
        """Test empty string."""
        result = youtube_scanner.format_date("", "")
        self.assertEqual(result, "NA")


class TestFormatVideoLine(unittest.TestCase):
    """Tests for format_video_line function."""

    def test_format_video_line_complete(self):
        """Test formatting complete video data."""
        video = {
            'upload_date': '2023-12-25',
            'url': 'https://www.youtube.com/watch?v=abc123',
            'title': 'Test Video'
        }
        result = youtube_scanner.format_video_line(video)
        expected = "[2023-12-25] https://www.youtube.com/watch?v=abc123 - Test Video\n"
        self.assertEqual(result, expected)

    def test_format_video_line_missing_fields(self):
        """Test formatting with missing fields."""
        video = {}
        result = youtube_scanner.format_video_line(video)
        self.assertEqual(result, "[N/A]  - \n")


class TestParseVideoEntry(unittest.TestCase):
    """Tests for parse_video_entry function."""

    def test_parse_video_entry_with_availability(self):
        """Test parsing video entry with availability."""
        parts = ['abc123', 'Test Video', 'public', '20231225', '1703548800']
        result = youtube_scanner.parse_video_entry(parts, include_availability=True)

        self.assertEqual(result['id'], 'abc123')
        self.assertEqual(result['title'], 'Test Video')
        self.assertEqual(result['url'], 'https://www.youtube.com/watch?v=abc123')
        self.assertEqual(result['availability'], 'public')
        self.assertEqual(result['upload_date'], '2023-12-25')

    def test_parse_video_entry_without_availability(self):
        """Test parsing video entry without availability."""
        parts = ['xyz789', 'Another Video', '20231226', '1703635200']
        result = youtube_scanner.parse_video_entry(parts, include_availability=False)

        self.assertEqual(result['id'], 'xyz789')
        self.assertEqual(result['title'], 'Another Video')
        self.assertEqual(result['availability'], 'public')
        self.assertEqual(result['upload_date'], '2023-12-26')

    def test_parse_video_entry_minimal(self):
        """Test parsing with minimal data."""
        parts = ['id123', 'Title Only']
        result = youtube_scanner.parse_video_entry(parts, include_availability=True)

        self.assertEqual(result['id'], 'id123')
        self.assertEqual(result['title'], 'Title Only')
        self.assertEqual(result['availability'], 'unknown')
        self.assertEqual(result['upload_date'], 'NA')


class TestGetChannelPlaylists(unittest.TestCase):
    """Tests for get_channel_playlists function."""

    @patch('youtube_scanner.run_ytdlp')
    def test_get_channel_playlists_success(self, mock_run_ytdlp):
        """Test getting channel playlists."""
        mock_run_ytdlp.return_value = "PLabc123|||Playlist 1\nPLxyz789|||Playlist 2\n"

        result = youtube_scanner.get_channel_playlists("https://www.youtube.com/@testuser")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'PLabc123')
        self.assertEqual(result[0]['title'], 'Playlist 1')
        self.assertEqual(result[0]['url'], 'https://www.youtube.com/playlist?list=PLabc123')
        self.assertEqual(result[1]['id'], 'PLxyz789')

    @patch('youtube_scanner.run_ytdlp')
    def test_get_channel_playlists_empty(self, mock_run_ytdlp):
        """Test getting playlists from channel with none."""
        mock_run_ytdlp.return_value = ""

        result = youtube_scanner.get_channel_playlists("https://www.youtube.com/@testuser")

        self.assertEqual(len(result), 0)

    @patch('youtube_scanner.run_ytdlp')
    def test_get_channel_playlists_malformed_output(self, mock_run_ytdlp):
        """Test handling malformed output."""
        mock_run_ytdlp.return_value = "invalid line\nno separator here"

        result = youtube_scanner.get_channel_playlists("https://www.youtube.com/@testuser")

        self.assertEqual(len(result), 0)


class TestGetPlaylistVideos(unittest.TestCase):
    """Tests for get_playlist_videos function."""

    @patch('youtube_scanner.run_ytdlp')
    def test_get_playlist_videos_success(self, mock_run_ytdlp):
        """Test getting videos from playlist."""
        mock_run_ytdlp.return_value = (
            "vid1|||Video 1|||public|||20231225|||1703548800\n"
            "vid2|||Video 2|||unlisted|||20231226|||1703635200\n"
        )

        result = youtube_scanner.get_playlist_videos("https://www.youtube.com/playlist?list=PLabc123")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'vid1')
        self.assertEqual(result[0]['availability'], 'public')
        self.assertEqual(result[1]['id'], 'vid2')
        self.assertEqual(result[1]['availability'], 'unlisted')

    @patch('youtube_scanner.run_ytdlp')
    def test_get_playlist_videos_empty(self, mock_run_ytdlp):
        """Test empty playlist."""
        mock_run_ytdlp.return_value = ""

        result = youtube_scanner.get_playlist_videos("https://www.youtube.com/playlist?list=PLempty")

        self.assertEqual(len(result), 0)


class TestGetChannelVideos(unittest.TestCase):
    """Tests for get_channel_videos function."""

    @patch('youtube_scanner.run_ytdlp')
    def test_get_channel_videos_success(self, mock_run_ytdlp):
        """Test getting channel videos."""
        mock_run_ytdlp.return_value = (
            "vid1|||Video 1|||20231225|||1703548800\n"
            "vid2|||Video 2|||20231226|||1703635200\n"
        )

        result = youtube_scanner.get_channel_videos("https://www.youtube.com/@testuser")

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'vid1')
        self.assertEqual(result[0]['availability'], 'public')


class TestGetVideoDetails(unittest.TestCase):
    """Tests for get_video_details function."""

    @patch('youtube_scanner.run_ytdlp')
    def test_get_video_details_success(self, mock_run_ytdlp):
        """Test getting video details."""
        mock_run_ytdlp.return_value = "vid123|||Test Video|||unlisted|||20231225\n"

        result = youtube_scanner.get_video_details("vid123")

        self.assertEqual(result['availability'], 'unlisted')
        self.assertEqual(result['upload_date'], '2023-12-25')

    @patch('youtube_scanner.run_ytdlp')
    def test_get_video_details_invalid_output(self, mock_run_ytdlp):
        """Test handling invalid output."""
        mock_run_ytdlp.return_value = "invalid output"

        result = youtube_scanner.get_video_details("vid123")

        self.assertEqual(result, {})


class TestScanAllPlaylists(unittest.TestCase):
    """Tests for _scan_all_playlists internal function."""

    @patch('youtube_scanner.get_playlist_videos')
    def test_scan_all_playlists_success(self, mock_get_videos):
        """Test scanning multiple playlists."""
        mock_get_videos.side_effect = [
            [{'id': 'vid1', 'title': 'Video 1'}],
            [{'id': 'vid2', 'title': 'Video 2'}, {'id': 'vid1', 'title': 'Video 1'}]
        ]

        playlists = [
            {'title': 'Playlist 1', 'url': 'https://youtube.com/playlist?list=PL1'},
            {'title': 'Playlist 2', 'url': 'https://youtube.com/playlist?list=PL2'}
        ]

        result = youtube_scanner._scan_all_playlists(playlists)

        self.assertEqual(len(result), 2)
        self.assertIn('vid1', result)
        self.assertIn('vid2', result)
        self.assertEqual(result['vid1']['found_in_playlist'], 'Playlist 1')

    @patch('youtube_scanner.get_playlist_videos')
    def test_scan_all_playlists_empty(self, mock_get_videos):
        """Test scanning with no playlists."""
        result = youtube_scanner._scan_all_playlists([])

        self.assertEqual(len(result), 0)


class TestIdentifyUnlistedVideos(unittest.TestCase):
    """Tests for _identify_unlisted_videos internal function."""

    def test_identify_unlisted_videos(self):
        """Test identifying unlisted videos."""
        all_playlist_videos = {
            'vid1': {'id': 'vid1', 'title': 'Public Video'},
            'vid2': {'id': 'vid2', 'title': 'Unlisted Video'},
            'vid3': {'id': 'vid3', 'title': 'Another Unlisted'}
        }
        public_ids = {'vid1'}

        result = youtube_scanner._identify_unlisted_videos(all_playlist_videos, public_ids)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['id'], 'vid2')
        self.assertEqual(result[1]['id'], 'vid3')
        self.assertTrue(all(v.get('reason') for v in result))

    def test_identify_unlisted_videos_all_public(self):
        """Test when all videos are public."""
        all_playlist_videos = {
            'vid1': {'id': 'vid1', 'title': 'Video 1'},
            'vid2': {'id': 'vid2', 'title': 'Video 2'}
        }
        public_ids = {'vid1', 'vid2'}

        result = youtube_scanner._identify_unlisted_videos(all_playlist_videos, public_ids)

        self.assertEqual(len(result), 0)


class TestFetchDetailedMetadata(unittest.TestCase):
    """Tests for _fetch_detailed_metadata internal function."""

    @patch('youtube_scanner.get_video_details')
    def test_fetch_detailed_metadata(self, mock_get_details):
        """Test fetching detailed metadata."""
        mock_get_details.return_value = {'availability': 'unlisted', 'upload_date': '2023-12-25'}

        videos = [
            {'id': 'vid1', 'title': 'Video 1'},
            {'id': 'vid2', 'title': 'Video 2'}
        ]

        youtube_scanner._fetch_detailed_metadata(videos)

        self.assertEqual(videos[0]['availability'], 'unlisted')
        self.assertEqual(videos[1]['upload_date'], '2023-12-25')
        self.assertEqual(mock_get_details.call_count, 2)


class TestScanChannel(unittest.TestCase):
    """Tests for scan_channel main function."""

    @patch('youtube_scanner.get_channel_videos')
    @patch('youtube_scanner.get_channel_playlists')
    @patch('youtube_scanner._scan_all_playlists')
    @patch('youtube_scanner._identify_unlisted_videos')
    def test_scan_channel_full(self, mock_identify, mock_scan, mock_playlists, mock_videos):
        """Test full channel scan."""
        mock_videos.return_value = [{'id': 'vid1', 'title': 'Public Video'}]
        mock_playlists.return_value = [{'title': 'Playlist 1', 'url': 'url1'}]
        mock_scan.return_value = {'vid1': {'id': 'vid1'}, 'vid2': {'id': 'vid2'}}
        mock_identify.return_value = [{'id': 'vid2', 'title': 'Unlisted'}]

        result = youtube_scanner.scan_channel("https://www.youtube.com/@test", include_public=True)

        self.assertIn('channel_url', result)
        self.assertIn('scan_date', result)
        self.assertEqual(len(result['public_videos']), 1)
        self.assertEqual(len(result['playlists']), 1)
        self.assertEqual(len(result['potentially_unlisted']), 1)

    @patch('youtube_scanner.get_channel_playlists')
    @patch('youtube_scanner._scan_all_playlists')
    def test_scan_channel_playlists_only(self, mock_scan, mock_playlists):
        """Test scanning playlists only."""
        mock_playlists.return_value = []
        mock_scan.return_value = {}

        result = youtube_scanner.scan_channel(
            "https://www.youtube.com/@test",
            include_public=False
        )

        self.assertEqual(len(result['public_videos']), 0)
        self.assertEqual(len(result['potentially_unlisted']), 0)

    @patch('youtube_scanner.get_channel_videos')
    @patch('youtube_scanner.get_channel_playlists')
    @patch('youtube_scanner._scan_all_playlists')
    @patch('youtube_scanner._identify_unlisted_videos')
    @patch('youtube_scanner._fetch_detailed_metadata')
    def test_scan_channel_detailed(self, mock_fetch, mock_identify, mock_scan,
                                   mock_playlists, mock_videos):
        """Test scan with detailed metadata."""
        mock_videos.return_value = [{'id': 'vid1'}]
        mock_playlists.return_value = []
        mock_scan.return_value = {}
        mock_identify.return_value = [{'id': 'vid2'}]

        youtube_scanner.scan_channel(
            "https://www.youtube.com/@test",
            include_public=True,
            detailed=True
        )

        mock_fetch.assert_called_once()


class TestSaveResults(unittest.TestCase):
    """Tests for save_results function."""

    @patch('builtins.open', new_callable=mock_open)
    @patch('json.dump')
    def test_save_results(self, mock_json_dump, mock_file):
        """Test saving results to JSON."""
        results = {'test': 'data'}
        filename = 'test.json'

        youtube_scanner.save_results(results, filename)

        mock_file.assert_called_once_with(filename, 'w', encoding='utf-8')
        mock_json_dump.assert_called_once()


class TestGetDefaultFilename(unittest.TestCase):
    """Tests for get_default_filename function."""

    def test_get_default_filename_format(self):
        """Test default filename format."""
        result = youtube_scanner.get_default_filename()

        self.assertTrue(result.startswith('youtube_scan_'))
        self.assertTrue(result.endswith('.json'))
        self.assertIn('_', result)


class TestPrintResults(unittest.TestCase):
    """Tests for print_results function."""

    @patch('builtins.print')
    def test_print_results(self, mock_print):
        """Test printing results."""
        results = {
            'public_videos': [{'id': 'vid1'}],
            'playlists': [{'title': 'PL1'}],
            'playlist_videos': [{'id': 'vid1'}, {'id': 'vid2'}],
            'potentially_unlisted': [
                {
                    'title': 'Unlisted Video',
                    'url': 'https://youtube.com/watch?v=vid2',
                    'upload_date': '2023-12-25',
                    'found_in_playlist': 'Test Playlist'
                }
            ]
        }

        youtube_scanner.print_results(results)

        # Verify print was called (checking details would be too brittle)
        self.assertTrue(mock_print.called)
        self.assertGreater(mock_print.call_count, 5)


class TestMain(unittest.TestCase):
    """Tests for main() function."""

    @patch('youtube_scanner.scan_channel')
    @patch('youtube_scanner.save_results')
    @patch('youtube_scanner.print_results')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['youtube_scanner.py', 'https://www.youtube.com/@test'])
    def test_main_default_args(self, mock_file, mock_print_results,
                               mock_save_results, mock_scan_channel):
        """Test main with default arguments."""
        mock_scan_channel.return_value = {
            'potentially_unlisted': [],
            'playlist_videos': []
        }

        youtube_scanner.main()

        # Verify scan_channel was called with correct args
        mock_scan_channel.assert_called_once()
        call_args = mock_scan_channel.call_args
        self.assertEqual(call_args[0][0], 'https://www.youtube.com/@test')
        self.assertTrue(call_args[1]['include_public'])
        self.assertFalse(call_args[1]['detailed'])

        # Verify results were printed and saved
        mock_print_results.assert_called_once()
        mock_save_results.assert_called_once()

        # Verify links file was written
        self.assertTrue(mock_file.called)

    @patch('youtube_scanner.scan_channel')
    @patch('youtube_scanner.save_results')
    @patch('youtube_scanner.print_results')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['youtube_scanner.py', 'https://www.youtube.com/@test',
                        '-o', 'custom_output.json'])
    def test_main_custom_output(self, mock_file, mock_print_results,
                                mock_save_results, mock_scan_channel):
        """Test main with custom output file."""
        mock_scan_channel.return_value = {
            'potentially_unlisted': [],
            'playlist_videos': []
        }

        youtube_scanner.main()

        # Verify custom filename was used
        mock_save_results.assert_called_once()
        self.assertEqual(mock_save_results.call_args[0][1], 'custom_output.json')

        # Verify links file has correct name
        calls = mock_file.call_args_list
        link_file_call = [c for c in calls if 'custom_output_links.txt' in str(c)]
        self.assertGreater(len(link_file_call), 0)

    @patch('youtube_scanner.scan_channel')
    @patch('youtube_scanner.save_results')
    @patch('youtube_scanner.print_results')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['youtube_scanner.py', 'https://www.youtube.com/@test',
                        '--playlists-only'])
    def test_main_playlists_only(self, mock_file, mock_print_results,
                                 mock_save_results, mock_scan_channel):
        """Test main with playlists-only flag."""
        mock_scan_channel.return_value = {
            'potentially_unlisted': [],
            'playlist_videos': []
        }

        youtube_scanner.main()

        # Verify include_public is False
        call_args = mock_scan_channel.call_args
        self.assertFalse(call_args[1]['include_public'])

    @patch('youtube_scanner.scan_channel')
    @patch('youtube_scanner.save_results')
    @patch('youtube_scanner.print_results')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['youtube_scanner.py', 'https://www.youtube.com/@test',
                        '--detailed'])
    def test_main_detailed_mode(self, mock_file, mock_print_results,
                                mock_save_results, mock_scan_channel):
        """Test main with detailed flag."""
        mock_scan_channel.return_value = {
            'potentially_unlisted': [],
            'playlist_videos': []
        }

        youtube_scanner.main()

        # Verify detailed is True
        call_args = mock_scan_channel.call_args
        self.assertTrue(call_args[1]['detailed'])

    @patch('youtube_scanner.scan_channel')
    @patch('youtube_scanner.save_results')
    @patch('youtube_scanner.print_results')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['youtube_scanner.py', 'https://www.youtube.com/@test'])
    def test_main_with_results(self, mock_file, mock_print_results,
                              mock_save_results, mock_scan_channel):
        """Test main with actual results including unlisted videos."""
        mock_scan_channel.return_value = {
            'potentially_unlisted': [
                {
                    'id': 'vid1',
                    'title': 'Unlisted Video',
                    'url': 'https://youtube.com/watch?v=vid1',
                    'upload_date': '2023-12-25'
                }
            ],
            'playlist_videos': [
                {
                    'id': 'vid2',
                    'title': 'Playlist Video',
                    'url': 'https://youtube.com/watch?v=vid2',
                    'upload_date': '2023-12-26'
                }
            ]
        }

        youtube_scanner.main()

        # Verify file writes include the video data
        mock_file.assert_called()
        write_calls = list(mock_file().write.call_args_list)
        self.assertGreater(len(write_calls), 0)

    @patch('youtube_scanner.get_default_filename')
    @patch('youtube_scanner.scan_channel')
    @patch('youtube_scanner.save_results')
    @patch('youtube_scanner.print_results')
    @patch('builtins.open', new_callable=mock_open)
    @patch('sys.argv', ['youtube_scanner.py', 'https://www.youtube.com/@test'])
    def test_main_default_filename_generation(self, mock_file, mock_print_results,
                                              mock_save_results, mock_scan_channel,
                                              mock_get_default_filename):
        """Test that default filename is generated when not specified."""
        mock_get_default_filename.return_value = 'youtube_scan_2023-12-25_120000.json'
        mock_scan_channel.return_value = {
            'potentially_unlisted': [],
            'playlist_videos': []
        }

        youtube_scanner.main()

        # Verify default filename generator was called
        mock_get_default_filename.assert_called_once()

        # Verify save_results was called with the generated filename
        mock_save_results.assert_called_once()
        self.assertEqual(
            mock_save_results.call_args[0][1],
            'youtube_scan_2023-12-25_120000.json'
        )


if __name__ == '__main__':
    unittest.main()
