import unittest
from unittest.mock import patch, MagicMock
import os
import builtins
import io
import sys
import cloud_agents

real_import = builtins.__import__

class TestExtractYoutubeTranscripts(unittest.TestCase):
    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {'YOUTUBE_API_KEY': 'fake_key'})
        self.env_patcher.start()

    def tearDown(self):
        self.env_patcher.stop()

    @patch('builtins.__import__')
    def test_missing_dependencies(self, mock_import):
        def side_effect(name, *args, **kwargs):
            if name in ('youtube_transcript_api', 'requests'):
                raise ImportError(f"No module named '{name}'")
            return real_import(name, *args, **kwargs)
        mock_import.side_effect = side_effect

        self.assertIsNone(cloud_agents.extract_youtube_transcripts({}))

    def test_missing_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(cloud_agents.extract_youtube_transcripts({}))

    def test_no_micha_stocks_source(self):
        st = {'sources': [{'identifier': '@Some.Other', 'enabled': True}]}
        self.assertIsNone(cloud_agents.extract_youtube_transcripts(st))

    def test_micha_stocks_source_disabled(self):
        st = {'sources': [{'identifier': '@Micha.Stocks', 'enabled': False}]}
        self.assertIsNone(cloud_agents.extract_youtube_transcripts(st))

    @patch('requests.get')
    def test_requests_exception(self, mock_get):
        mock_get.side_effect = Exception("API limit reached")
        st = {'sources': [{'identifier': '@Micha.Stocks', 'enabled': True}]}

        captured_output = io.StringIO()
        sys.stdout = captured_output

        cloud_agents.extract_youtube_transcripts(st)

        sys.stdout = sys.__stdout__
        self.assertIn("YouTube Agent Error: API limit reached", captured_output.getvalue())

    @patch('requests.get')
    @patch('youtube_transcript_api.YouTubeTranscriptApi.get_transcript', create=True)
    def test_get_transcript_exception(self, mock_get_transcript, mock_get):
        mock_channel_response = MagicMock()
        mock_channel_response.json.return_value = {
            'items': [{'id': {'channelId': 'channel_123'}}]
        }

        mock_video_response = MagicMock()
        mock_video_response.json.return_value = {
            'items': [{'id': {'videoId': 'vid_123'}}]
        }

        mock_get.side_effect = [mock_channel_response, mock_video_response]
        mock_get_transcript.side_effect = Exception("Transcript disabled")

        st = {'sources': [{'identifier': '@Micha.Stocks', 'enabled': True}]}

        captured_output = io.StringIO()
        sys.stdout = captured_output

        cloud_agents.extract_youtube_transcripts(st)

        sys.stdout = sys.__stdout__

        output = captured_output.getvalue()
        self.assertIn("Transcript error for vid_123: Transcript disabled", output)

if __name__ == '__main__':
    unittest.main()
