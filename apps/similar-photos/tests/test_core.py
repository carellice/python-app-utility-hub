import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageEnhance

from similar_photos.core import PhotoInfo, safe_move_to_trash, scan_folder


class ScanFolderTests(unittest.TestCase):
    def test_groups_exact_duplicates_and_similar_photos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "original.jpg"
            duplicate = root / "duplicate.jpg"
            similar = root / "similar.jpg"
            different = root / "different.jpg"

            image = Image.new("RGB", (160, 120), "navy")
            for x in range(20, 120):
                for y in range(30, 80):
                    image.putpixel((x, y), (230, 220, 80))
            image.save(original, quality=95)
            duplicate.write_bytes(original.read_bytes())

            brighter = ImageEnhance.Brightness(image).enhance(1.03)
            brighter.save(similar, quality=95)

            Image.new("RGB", (160, 120), "white").save(different)

            result = scan_folder(root, hamming_threshold=10)

            grouped_paths = [set(photo.path.name for photo in group.photos) for group in result.groups]
            self.assertIn({"original.jpg", "duplicate.jpg", "similar.jpg"}, grouped_paths)
            self.assertFalse(any("different.jpg" in paths and len(paths) > 1 for paths in grouped_paths))

    def test_move_to_trash_avoids_name_collisions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            trash = root / "trash"
            source = root / "photo.jpg"
            source.write_bytes(b"photo")
            trash.mkdir()
            (trash / "photo.jpg").write_bytes(b"existing")

            photo = PhotoInfo(path=source, rel_path="photo.jpg", sha256="x", size_bytes=5, mtime=0)
            destination = safe_move_to_trash(photo, trash_root=trash)

            self.assertEqual(destination.name, "photo_2.jpg")
            self.assertFalse(source.exists())
            self.assertEqual(destination.read_bytes(), b"photo")

    def test_converts_supported_non_jpeg_images_before_scan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "sample.png"
            Image.new("RGBA", (80, 60), (10, 120, 200, 180)).save(source)

            result = scan_folder(root)
            converted = root / "sample.jpg"

            self.assertTrue(converted.exists())
            self.assertTrue(source.exists())
            self.assertEqual([photo.path.name for photo in result.photos], ["sample.jpg"])


if __name__ == "__main__":
    unittest.main()
