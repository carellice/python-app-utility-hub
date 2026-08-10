#!/usr/bin/env python3
"""
Batch photo color correction tool.

Given an input folder, this script creates corrected copies of the images in an
output folder. It applies a conservative automatic enhancement pipeline designed
to make common snapshots look cleaner without destroying the original mood.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps, ImageStat


SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
    ".bmp",
}


@dataclass(frozen=True)
class CorrectionPreset:
    label: str
    white_balance: float = 1.0
    autocontrast: float = 1.0
    tone_curve: float = 1.0
    vibrance: float = 1.0
    clarity: float = 1.0
    saturation: float = 1.0
    contrast: float = 1.0
    brightness: float = 1.0
    sharpness: float = 1.0
    warmth: float = 0.0
    fade: float = 0.0
    shadows: float = 0.0
    highlights: float = 0.0
    landscape_boost: float = 0.0
    skin_lift: float = 0.0
    dehaze: float = 0.0
    monochrome: bool = False


PRESETS: dict[str, CorrectionPreset] = {
    "natural": CorrectionPreset(
        label="Naturale",
        autocontrast=0.78,
        tone_curve=0.72,
        vibrance=0.72,
        clarity=0.65,
        saturation=0.72,
        contrast=0.78,
        brightness=0.9,
        sharpness=0.75,
    ),
    "professional": CorrectionPreset(label="Professionale"),
    "vivid": CorrectionPreset(
        label="Vivace",
        autocontrast=1.05,
        tone_curve=1.08,
        vibrance=1.32,
        clarity=1.0,
        saturation=1.25,
        contrast=1.06,
        brightness=1.0,
        sharpness=1.0,
    ),
    "warm": CorrectionPreset(
        label="Caldo",
        autocontrast=0.9,
        tone_curve=0.92,
        vibrance=1.0,
        clarity=0.82,
        saturation=0.98,
        contrast=0.9,
        brightness=1.02,
        sharpness=0.82,
        warmth=0.22,
    ),
    "cool": CorrectionPreset(
        label="Freddo",
        autocontrast=0.95,
        tone_curve=1.0,
        vibrance=0.92,
        clarity=1.08,
        saturation=0.9,
        contrast=1.0,
        brightness=0.96,
        sharpness=1.05,
        warmth=-0.2,
    ),
    "portrait": CorrectionPreset(
        label="Ritratto",
        white_balance=0.78,
        autocontrast=0.62,
        tone_curve=0.68,
        vibrance=0.72,
        clarity=0.32,
        saturation=0.72,
        contrast=0.68,
        brightness=1.08,
        sharpness=0.46,
        warmth=0.12,
    ),
    "cinematic": CorrectionPreset(
        label="Cinematico",
        autocontrast=0.92,
        tone_curve=1.26,
        vibrance=0.9,
        clarity=1.18,
        saturation=0.8,
        contrast=1.22,
        brightness=0.86,
        sharpness=1.0,
        warmth=-0.08,
        fade=0.12,
    ),
    "spectacular": CorrectionPreset(
        label="Spettacolare",
        white_balance=0.92,
        autocontrast=0.98,
        tone_curve=1.12,
        vibrance=1.2,
        clarity=1.12,
        saturation=0.72,
        contrast=1.35,
        brightness=1.06,
        sharpness=1.18,
        warmth=0.34,
        shadows=1.0,
        highlights=-0.55,
        landscape_boost=1.0,
        skin_lift=0.9,
        dehaze=0.65,
    ),
    "black_white": CorrectionPreset(
        label="Bianco e nero",
        white_balance=0.0,
        autocontrast=1.0,
        tone_curve=1.18,
        vibrance=0.0,
        clarity=1.18,
        saturation=0.0,
        contrast=1.22,
        brightness=0.95,
        sharpness=1.08,
        monochrome=True,
    ),
}

DEFAULT_PRESET = "professional"


def preset_choices() -> list[str]:
    return list(PRESETS.keys())


def get_preset(name: str) -> CorrectionPreset:
    return PRESETS.get(name, PRESETS[DEFAULT_PRESET])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Corregge automaticamente colore, contrasto e nitidezza delle foto in una cartella.",
    )
    parser.add_argument(
        "input_folder",
        type=Path,
        help="Cartella che contiene le fotografie da correggere.",
    )
    parser.add_argument(
        "-o",
        "--output-folder",
        type=Path,
        default=None,
        help="Cartella di destinazione. Default: <input_folder>/corrected",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Include anche le sottocartelle.",
    )
    parser.add_argument(
        "-s",
        "--strength",
        type=float,
        default=1.0,
        help="Intensita' della correzione: 0.0-2.0. Default: 1.0",
    )
    parser.add_argument(
        "-p",
        "--preset",
        choices=preset_choices(),
        default=DEFAULT_PRESET,
        help="Preset colore da applicare. Default: professional",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sovrascrive i file gia' presenti nella cartella di output.",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        help="Qualita' JPEG/WebP in uscita: 1-100. Default: 95",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra cosa verrebbe elaborato senza scrivere file.",
    )
    return parser.parse_args()


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def discover_images(input_folder: Path, recursive: bool) -> list[Path]:
    pattern = "**/*" if recursive else "*"
    files = [
        path
        for path in input_folder.glob(pattern)
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files, key=lambda path: str(path).lower())


def gray_world_white_balance(image: Image.Image, strength: float) -> Image.Image:
    rgb = image.convert("RGB")
    channel_means = ImageStat.Stat(rgb).mean
    overall_mean = sum(channel_means) / len(channel_means)
    scales = [overall_mean / max(mean, 1.0) for mean in channel_means]

    blend = clamp(strength * 0.85, 0.0, 1.0)
    scales = [1.0 + (scale - 1.0) * blend for scale in scales]

    channels = []
    for channel, scale in zip(rgb.split(), scales):
        lookup = [int(clamp(value * scale, 0, 255)) for value in range(256)]
        channels.append(channel.point(lookup))

    return Image.merge("RGB", channels)


def apply_warmth(image: Image.Image, warmth: float, strength: float) -> Image.Image:
    amount = clamp(warmth * strength, -0.5, 0.5)
    if amount == 0:
        return image

    channels = []
    multipliers = (1.0 + amount * 0.18, 1.0 + abs(amount) * 0.02, 1.0 - amount * 0.18)
    for channel, multiplier in zip(image.convert("RGB").split(), multipliers):
        lookup = [int(clamp(value * multiplier, 0, 255)) for value in range(256)]
        channels.append(channel.point(lookup))
    return Image.merge("RGB", channels)


def apply_fade(image: Image.Image, amount: float, strength: float) -> Image.Image:
    fade = clamp(amount * strength, 0.0, 0.35)
    if fade <= 0:
        return image

    lookup = []
    for value in range(256):
        normalized = value / 255.0
        lifted = normalized * (1.0 - fade * 0.28) + fade * 0.1
        lookup.append(int(clamp(lifted * 255.0, 0, 255)))
    return image.point(lookup * len(image.getbands()))


def apply_shadow_highlight_recovery(
    image: Image.Image,
    shadows: float,
    highlights: float,
    strength: float,
) -> Image.Image:
    if shadows == 0 and highlights == 0:
        return image

    luma = ImageOps.grayscale(image)

    shadow_amount = clamp(shadows * strength, 0.0, 2.0)
    if shadow_amount > 0:
        shadow_mask = ImageOps.invert(luma).point(
            [int(clamp((value - 70) * 2.35, 0, 255)) for value in range(256)]
        )
        lifted = ImageEnhance.Brightness(image).enhance(1.0 + 0.12 * shadow_amount)
        image = Image.composite(lifted, image, shadow_mask)
        luma = ImageOps.grayscale(image)

    highlight_amount = clamp(abs(highlights) * strength, 0.0, 2.0)
    if highlights < 0 and highlight_amount > 0:
        highlight_mask = luma.point(
            [int(clamp((value - 150) * 2.15, 0, 255)) for value in range(256)]
        )
        recovered = ImageEnhance.Brightness(image).enhance(1.0 - 0.08 * highlight_amount)
        image = Image.composite(recovered, image, highlight_mask)

    return image


def range_mask(channel: Image.Image, ranges: list[tuple[int, int]], softness: int = 10) -> Image.Image:
    lookup = []
    for value in range(256):
        mask_value = 0
        for start, end in ranges:
            if start <= value <= end:
                mask_value = 255
            elif start - softness <= value < start:
                mask_value = max(mask_value, int(255 * (value - (start - softness)) / softness))
            elif end < value <= end + softness:
                mask_value = max(mask_value, int(255 * ((end + softness) - value) / softness))
        lookup.append(int(clamp(mask_value, 0, 255)))
    return channel.point(lookup)


def apply_selective_landscape_boost(image: Image.Image, amount: float, strength: float) -> Image.Image:
    boost = clamp(amount * strength, 0.0, 2.0)
    if boost <= 0:
        return image

    hsv = image.convert("HSV")
    hue, saturation, value = hsv.split()

    green_mask = range_mask(hue, [(45, 105)])
    blue_mask = range_mask(hue, [(132, 178)])
    gold_mask = range_mask(hue, [(18, 40)])
    landscape_mask = ImageChops.lighter(ImageChops.lighter(green_mask, blue_mask), gold_mask)

    saturation_lut = [int(clamp(value * (1.0 + 0.22 * boost), 0, 255)) for value in range(256)]
    value_lut = [int(clamp(value * (1.0 + 0.035 * boost), 0, 255)) for value in range(256)]

    boosted_saturation = saturation.point(saturation_lut)
    boosted_value = value.point(value_lut)
    saturation = Image.composite(boosted_saturation, saturation, landscape_mask)
    value = Image.composite(boosted_value, value, landscape_mask)
    return Image.merge("HSV", (hue, saturation, value)).convert("RGB")


def apply_skin_lift(image: Image.Image, amount: float, strength: float) -> Image.Image:
    lift = clamp(amount * strength, 0.0, 2.0)
    if lift <= 0:
        return image

    hsv = image.convert("HSV")
    hue, saturation, value = hsv.split()
    hue_mask = range_mask(hue, [(0, 27), (245, 255)], softness=8)
    saturation_mask = saturation.point(
        [
            int(255 if 28 <= item <= 185 else clamp(min(item, 255 - item) * 2.6, 0, 255))
            for item in range(256)
        ]
    )
    shadow_mask = value.point([int(clamp((210 - item) * 1.45, 0, 255)) for item in range(256)])
    skin_mask = ImageChops.multiply(ImageChops.multiply(hue_mask, saturation_mask), shadow_mask)

    lifted = ImageEnhance.Brightness(image).enhance(1.0 + 0.1 * lift)
    lifted = apply_warmth(lifted, 0.1, strength)
    return Image.composite(lifted, image, skin_mask)


def apply_dehaze(image: Image.Image, amount: float, strength: float) -> Image.Image:
    dehaze = clamp(amount * strength, 0.0, 2.0)
    if dehaze <= 0:
        return image

    contrasted = ImageEnhance.Contrast(image).enhance(1.0 + 0.07 * dehaze)
    sharpened = contrasted.filter(
        ImageFilter.UnsharpMask(radius=14.0, percent=int(12 * dehaze), threshold=10)
    )
    return Image.blend(image, sharpened, clamp(0.55 * dehaze, 0.0, 0.75))


def percentile_autocontrast(image: Image.Image, strength: float) -> Image.Image:
    rgb = image.convert("RGB")
    stretched = ImageOps.autocontrast(rgb, cutoff=1)
    amount = clamp(strength * 0.46, 0.0, 0.78)
    return Image.blend(rgb, stretched, amount)


def apply_tone_curve(image: Image.Image, strength: float) -> Image.Image:
    amount = clamp(0.18 * strength, 0.0, 0.36)

    lookup = []
    for value in range(256):
        tone = value / 255.0
        curved = tone + amount * (tone - 0.5) * 4.0 * tone * (1.0 - tone)
        lookup.append(int(clamp(curved * 255.0, 0, 255)))

    return image.point(lookup * len(image.getbands()))


def apply_vibrance(image: Image.Image, strength: float) -> Image.Image:
    hsv = image.convert("HSV")
    hue, saturation, value = hsv.split()
    vibrance = clamp(0.42 * strength, 0.0, 0.85)

    saturation_lookup = []
    for item in range(256):
        normalized = item / 255.0
        selective_boost = 1.0 + vibrance * (1.0 - normalized * 0.72)
        lifted = item * selective_boost + 3.0 * strength
        saturation_lookup.append(int(clamp(lifted, 0, 255)))

    value_lookup = []
    for item in range(256):
        normalized = item / 255.0
        midtone_lift = 0.035 * strength * 4.0 * normalized * (1.0 - normalized)
        value_lookup.append(int(clamp((normalized + midtone_lift) * 255.0, 0, 255)))

    hsv = Image.merge("HSV", (hue, saturation.point(saturation_lookup), value.point(value_lookup)))
    return hsv.convert("RGB")


def apply_clarity(image: Image.Image, strength: float) -> Image.Image:
    if strength <= 0:
        return image

    radius = 10.0
    percent = int(clamp(22 * strength, 0, 42))
    return image.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=8))


def enhance(image: Image.Image, strength: float, preset_name: str = DEFAULT_PRESET) -> Image.Image:
    strength = clamp(strength, 0.0, 2.0)
    preset = get_preset(preset_name)
    image = image.convert("RGB")

    if preset.monochrome:
        image = ImageOps.grayscale(image).convert("RGB")

    if preset.white_balance > 0:
        image = gray_world_white_balance(image, strength * preset.white_balance)
    image = apply_warmth(image, preset.warmth, strength)
    image = percentile_autocontrast(image, strength * preset.autocontrast)
    image = apply_shadow_highlight_recovery(image, preset.shadows, preset.highlights, strength)
    image = apply_tone_curve(image, strength * preset.tone_curve)
    image = apply_fade(image, preset.fade, strength)
    image = apply_dehaze(image, preset.dehaze, strength)

    if not preset.monochrome:
        image = apply_vibrance(image, strength * preset.vibrance)
        image = apply_selective_landscape_boost(image, preset.landscape_boost, strength)
        image = apply_skin_lift(image, preset.skin_lift, strength)
    image = apply_clarity(image, strength * preset.clarity)

    saturation = 1.0 + 0.08 * strength * preset.saturation
    contrast = 1.0 + 0.13 * strength * preset.contrast
    brightness = 1.0 + 0.025 * strength * preset.brightness
    sharpness = 1.0 + 0.34 * strength * preset.sharpness

    image = ImageEnhance.Color(image).enhance(saturation)
    image = ImageEnhance.Contrast(image).enhance(contrast)
    image = ImageEnhance.Brightness(image).enhance(brightness)
    image = ImageEnhance.Sharpness(image).enhance(sharpness)

    if strength > 0:
        radius = 1.15
        percent = int(92 * strength * preset.sharpness)
        threshold = 3
        image = image.filter(
            ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold),
        )

    return image


def output_path_for(source: Path, input_folder: Path, output_folder: Path) -> Path:
    relative_path = source.relative_to(input_folder)
    return output_folder / relative_path


def save_image(image: Image.Image, destination: Path, original: Image.Image, quality: int) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)

    save_kwargs: dict[str, object] = {}
    exif = original.info.get("exif")
    if exif:
        save_kwargs["exif"] = exif

    suffix = destination.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        save_kwargs.update({"quality": quality, "optimize": True, "progressive": True})
        image.save(destination, format="JPEG", **save_kwargs)
    elif suffix == ".webp":
        save_kwargs.update({"quality": quality, "method": 6})
        image.save(destination, format="WEBP", **save_kwargs)
    elif suffix in {".tif", ".tiff"}:
        image.save(destination, format="TIFF", **save_kwargs)
    elif suffix == ".png":
        image.save(destination, format="PNG", optimize=True)
    else:
        image.save(destination)


def process_image(
    source: Path,
    input_folder: Path,
    output_folder: Path,
    strength: float,
    preset_name: str,
    quality: int,
    overwrite: bool,
    dry_run: bool,
) -> tuple[Literal["processed", "skipped", "failed"], str]:
    destination = output_path_for(source, input_folder, output_folder)

    if destination.exists() and not overwrite:
        return "skipped", f"skip, esiste gia': {destination}"

    if dry_run:
        return "processed", f"dry-run: {source} -> {destination}"

    try:
        with Image.open(source) as original:
            oriented = ImageOps.exif_transpose(original)
            corrected = enhance(oriented, strength, preset_name)
            save_image(corrected, destination, original, quality)
    except Exception as exc:  # noqa: BLE001 - a batch tool should keep going.
        return "failed", f"errore su {source}: {exc}"

    return "processed", f"ok: {source} -> {destination}"


def main() -> int:
    args = parse_args()

    input_folder = args.input_folder.expanduser().resolve()
    if not input_folder.exists() or not input_folder.is_dir():
        print(f"Errore: la cartella non esiste: {input_folder}", file=sys.stderr)
        return 2

    output_folder = (
        args.output_folder.expanduser().resolve()
        if args.output_folder
        else input_folder / "corrected"
    )
    strength = clamp(args.strength, 0.0, 2.0)
    preset_name = args.preset
    quality = int(clamp(args.quality, 1, 100))

    images = discover_images(input_folder, args.recursive)
    if output_folder.is_relative_to(input_folder):
        images = [
            image
            for image in images
            if not image.resolve().is_relative_to(output_folder.resolve())
        ]

    if not images:
        print("Nessuna immagine supportata trovata.")
        return 0

    print(f"Trovate {len(images)} immagini.")
    print(f"Output: {output_folder}")
    print(f"Preset: {get_preset(preset_name).label}")
    print(f"Intensita': {strength:.2f}")

    processed = 0
    skipped = 0
    failed = 0
    for source in images:
        status, message = process_image(
            source=source,
            input_folder=input_folder,
            output_folder=output_folder,
            strength=strength,
            preset_name=preset_name,
            quality=quality,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )
        print(message)
        if status == "processed":
            processed += 1
        elif status == "skipped":
            skipped += 1
        else:
            failed += 1

    print(f"Finite. Elaborate: {processed}. Saltate: {skipped}. Fallite: {failed}.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
