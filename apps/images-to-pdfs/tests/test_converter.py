from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from image_to_pdfs.converter import (
    ExistingFilePolicy,
    ImageFolderConverter,
    natural_sorted,
)


class NaturalSortTests(unittest.TestCase):
    def test_numeric_parts_are_sorted_naturally(self) -> None:
        paths = [Path("10.png"), Path("2.png"), Path("1.png")]
        self.assertEqual(
            [path.name for path in natural_sorted(paths)],
            ["1.png", "2.png", "10.png"],
        )

    def test_sort_is_case_insensitive(self) -> None:
        paths = [Path("B2.PNG"), Path("b10.png"), Path("b1.PnG")]
        self.assertEqual(
            [path.name for path in natural_sorted(paths)],
            ["b1.PnG", "B2.PNG", "b10.png"],
        )


class ConversionTests(unittest.TestCase):
    def test_direct_images_take_priority_over_subfolders(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary)
            selected = workspace / "Raccolta"
            nested = selected / "Sottocartella da ignorare"
            output = workspace / "risultati"
            selected.mkdir()
            nested.mkdir()

            Image.new("RGB", (20, 20), "red").save(selected / "10.jpg")
            Image.new("RGB", (20, 20), "blue").save(selected / "2.png")
            Image.new("RGB", (20, 20), "green").save(nested / "1.jpg")

            log: list[str] = []
            summary = ImageFolderConverter(
                selected, output, on_log=log.append
            ).run()

            self.assertEqual(summary.folders_found, 1)
            self.assertEqual(summary.pdfs_created, 1)
            self.assertTrue((output / "Raccolta.pdf").is_file())
            self.assertFalse(
                (output / "Sottocartella da ignorare.pdf").exists()
            )
            self.assertTrue(any("Modalità cartella singola" in line for line in log))
            self.assertTrue(any("2 pagine valide" in line for line in log))

    def test_transparency_is_flattened_on_white(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image_path = Path(temporary) / "trasparente.png"
            Image.new("RGBA", (2, 2), (10, 20, 30, 0)).save(image_path)

            page = ImageFolderConverter._read_page(image_path)
            try:
                self.assertEqual(page.mode, "RGB")
                self.assertEqual(page.getpixel((0, 0)), (255, 255, 255))
            finally:
                page.close()

    def test_exif_orientation_is_applied(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            image_path = Path(temporary) / "ruotata.jpg"
            exif = Image.Exif()
            exif[274] = 6
            Image.new("RGB", (40, 20), "blue").save(image_path, exif=exif)

            page = ImageFolderConverter._read_page(image_path)
            try:
                self.assertEqual(page.size, (20, 40))
            finally:
                page.close()

    def test_all_declared_formats_and_uppercase_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            chapter = root / "Formati"
            output = root / "risultati"
            chapter.mkdir()

            formats = [
                ("01.JPG", "JPEG"),
                ("02.jpeg", "JPEG"),
                ("03.PNG", "PNG"),
                ("04.WeBp", "WEBP"),
                ("05.BMP", "BMP"),
                ("06.tif", "TIFF"),
                ("07.TIFF", "TIFF"),
            ]
            for filename, image_format in formats:
                Image.new("RGB", (16, 12), "purple").save(
                    chapter / filename, format=image_format
                )
            Image.new("RGB", (16, 12), "orange").save(chapter / "08.gif")

            log: list[str] = []
            summary = ImageFolderConverter(
                root, output, on_log=log.append
            ).run()

            self.assertEqual(summary.pdfs_created, 1)
            self.assertEqual(summary.images_failed, 0)
            self.assertTrue(any("7 pagine valide" in line for line in log))

    def test_conversion_continues_and_reports_invalid_images(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            chapter_one = root / "Capitolo 01"
            chapter_two = root / "Capitolo 02"
            empty_chapter = root / "Capitolo 03"
            output = root / "PDF creati"
            chapter_one.mkdir()
            chapter_two.mkdir()
            empty_chapter.mkdir()
            output.mkdir()

            Image.new("RGB", (20, 30), "red").save(chapter_one / "10.JPG")
            transparent = Image.new("RGBA", (30, 20), (0, 0, 255, 100))
            transparent.save(chapter_one / "2.png")
            (chapter_two / "1.webp").write_bytes(b"non e una immagine")
            (root / "file-da-ignorare.txt").write_bytes(b"irrilevante")

            log: list[str] = []
            summary = ImageFolderConverter(
                root,
                output,
                ExistingFilePolicy.OVERWRITE,
                on_log=log.append,
            ).run()

            # La cartella di output, essendo dentro la sorgente, viene esclusa.
            self.assertEqual(summary.folders_found, 3)
            self.assertEqual(summary.pdfs_created, 1)
            self.assertEqual(summary.folders_skipped, 2)
            self.assertEqual(summary.images_failed, 1)
            self.assertEqual(summary.error_count, 1)
            result = output / "Capitolo 01.pdf"
            self.assertTrue(result.is_file())
            self.assertTrue(result.read_bytes().startswith(b"%PDF"))
            self.assertTrue(any("2 pagine valide" in line for line in log))
            self.assertTrue(any("Capitolo 02/1.webp" in line for line in log))

    def test_existing_file_policies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            chapter = root / "Capitolo"
            output = root / "output-esterno"
            chapter.mkdir()
            Image.new("RGB", (10, 10), "green").save(chapter / "1.png")

            first = ImageFolderConverter(root, output).run()
            skipped = ImageFolderConverter(
                root, output, ExistingFilePolicy.SKIP
            ).run()
            copied = ImageFolderConverter(
                root, output, ExistingFilePolicy.NUMBERED_COPY
            ).run()

            self.assertEqual(first.pdfs_created, 1)
            self.assertEqual(skipped.pdfs_created, 0)
            self.assertEqual(skipped.folders_skipped, 1)
            self.assertEqual(copied.pdfs_created, 1)
            self.assertTrue((output / "Capitolo (1).pdf").is_file())


if __name__ == "__main__":
    unittest.main()
