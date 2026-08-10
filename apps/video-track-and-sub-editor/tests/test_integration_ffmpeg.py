from pathlib import Path
import subprocess
import tempfile
import unittest

from media_engine import ExportProcess, FFmpegTools, build_ffmpeg_command, probe_media


class FFmpegIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.tools = FFmpegTools.discover()
        except Exception as exc:  # pragma: no cover - depends on the host machine
            raise unittest.SkipTest(str(exc)) from exc

    def test_remux_keeps_video_packets_and_changes_tracks(self) -> None:
        fixture = Path(__file__).parent / "fixtures" / "sample.srt"
        with tempfile.TemporaryDirectory() as raw_directory:
            directory = Path(raw_directory)
            source = directory / "source.mkv"
            output = directory / "output.mkv"
            create_command = [
                self.tools.ffmpeg,
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=160x90:rate=10",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:sample_rate=48000",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=660:sample_rate=48000",
                "-t",
                "1",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-map",
                "2:a:0",
                "-metadata:s:a:0",
                "language=ita",
                "-metadata:s:a:1",
                "language=eng",
                "-c:v",
                "ffv1",
                "-c:a",
                "pcm_s16le",
                str(source),
            ]
            created = subprocess.run(create_command, capture_output=True, text=True, check=False)
            self.assertEqual(created.returncode, 0, created.stderr)

            info = probe_media(source, self.tools)
            self.assertEqual(len(info.audio_tracks), 2)
            info.audio_tracks[1].selected = False
            subtitle_info = probe_media(fixture, self.tools, external=True)
            subtitle = subtitle_info.subtitle_tracks[0]
            subtitle.language = "ita"
            subtitle.title = "Italiano"
            tracks = [*info.tracks, subtitle]

            command = build_ffmpeg_command(self.tools, source, output, tracks)
            process = ExportProcess()
            progress_values: list[float | None] = []
            ok, error = process.run(command, info.duration, progress_values.append)
            self.assertTrue(ok, error)
            self.assertTrue(progress_values)
            self.assertEqual(progress_values[-1], 1.0)

            result = probe_media(output, self.tools)
            self.assertEqual(len(result.audio_tracks), 1)
            self.assertEqual(len(result.subtitle_tracks), 1)
            self.assertEqual(result.audio_tracks[0].language, "ita")
            self.assertEqual(result.subtitle_tracks[0].title, "Italiano")
            self.assertEqual(self._video_hash(source), self._video_hash(output))

    def _video_hash(self, path: Path) -> str:
        command = [
            self.tools.ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-c",
            "copy",
            "-f",
            "hash",
            "-hash",
            "sha256",
            "-",
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()


if __name__ == "__main__":
    unittest.main()
