from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from media_engine import FFmpegTools, Track, build_ffmpeg_command, parse_probe, remove_original


class ParseProbeTests(unittest.TestCase):
    def test_extracts_tracks_and_video_information(self) -> None:
        payload = {
            "streams": [
                {"index": 0, "codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080},
                {
                    "index": 1,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "channels": 2,
                    "channel_layout": "stereo",
                    "tags": {"language": "ita", "title": "Italiano"},
                    "disposition": {"default": 1, "forced": 0},
                },
                {
                    "index": 2,
                    "codec_type": "subtitle",
                    "codec_name": "subrip",
                    "tags": {"language": "eng"},
                    "disposition": {"default": 0, "forced": 1},
                },
            ],
            "format": {"duration": "125.25", "size": "1000", "format_name": "matroska"},
        }
        info = parse_probe(Path("film.mkv"), payload)

        self.assertEqual(len(info.video_streams), 1)
        self.assertEqual(len(info.audio_tracks), 1)
        self.assertEqual(len(info.subtitle_tracks), 1)
        self.assertEqual(info.audio_tracks[0].language, "ita")
        self.assertEqual(info.audio_tracks[0].title, "Italiano")
        self.assertTrue(info.audio_tracks[0].default)
        self.assertTrue(info.subtitle_tracks[0].forced)
        self.assertEqual(info.duration, 125.25)


class CommandTests(unittest.TestCase):
    def test_builds_stream_copy_command_with_only_selected_tracks(self) -> None:
        tools = FFmpegTools("ffmpeg", "ffprobe")
        source = Path("source.mkv")
        external = Path("new audio.flac")
        tracks = [
            Track("a1", "audio", 1, source, codec="aac", language="ita", title="Italiano"),
            Track("a2", "audio", 2, source, codec="aac", language="eng", selected=False),
            Track(
                "s1",
                "subtitle",
                0,
                external,
                codec="subrip",
                language="eng",
                title="English",
                external=True,
                disposition={"default": 0, "forced": 1},
            ),
        ]

        command = build_ffmpeg_command(tools, source, Path("output.mkv"), tracks)

        self.assertEqual(command.count("-i"), 2)
        self.assertIn("1:0", command)
        self.assertIn("0:1", command)
        self.assertNotIn("0:2", command)
        self.assertIn("copy", command)
        self.assertIn("language=ita", command)
        self.assertIn("title=English", command)
        self.assertIn("forced", command)

    def test_external_file_is_added_only_once_for_multiple_streams(self) -> None:
        tools = FFmpegTools("ffmpeg", "ffprobe")
        source = Path("source.mkv")
        external = Path("audio.mka")
        tracks = [
            Track("a1", "audio", 0, external, external=True),
            Track("a2", "audio", 1, external, external=True),
        ]
        command = build_ffmpeg_command(tools, source, Path("output.mkv"), tracks)
        self.assertEqual(command.count("-i"), 2)
        self.assertIn("1:0", command)
        self.assertIn("1:1", command)


class OriginalRemovalTests(unittest.TestCase):
    def test_permanent_removal_deletes_only_the_requested_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            original = directory / "original.mkv"
            neighbour = directory / "keep.mkv"
            original.write_bytes(b"original")
            neighbour.write_bytes(b"keep")

            remove_original(original, "permanent")

            self.assertFalse(original.exists())
            self.assertEqual(neighbour.read_bytes(), b"keep")

    def test_trash_uses_a_separate_path_argument_and_checks_the_result(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            original = Path(raw_directory) / "film con spazi e ' apice.mkv"
            original.write_bytes(b"original")

            def fake_run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                self.assertEqual(command[0], "osascript")
                self.assertEqual(command[-1], str(original))
                self.assertIn("set targetFile to POSIX file targetPath as alias", command)
                self.assertIn('tell application "Finder" to delete targetFile', command)
                self.assertNotIn('tell application "Finder" to delete (POSIX file targetPath)', command)
                original.unlink()
                return subprocess.CompletedProcess(command, 0, "", "")

            with patch("media_engine.sys.platform", "darwin"), patch(
                "media_engine.subprocess.run", side_effect=fake_run
            ):
                remove_original(original, "trash")

            self.assertFalse(original.exists())

    def test_unknown_removal_mode_is_rejected_without_touching_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_directory:
            original = Path(raw_directory) / "original.mkv"
            original.write_bytes(b"original")

            with self.assertRaises(ValueError):
                remove_original(original, "unknown")

            self.assertTrue(original.exists())


if __name__ == "__main__":
    unittest.main()
