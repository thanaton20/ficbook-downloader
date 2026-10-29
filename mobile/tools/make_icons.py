"""Draw the phone app icons: the desktop book-and-arrow mark in the sage palette.

Run from the repository root:  python3 mobile/tools/make_icons.py
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ACCENT = (63, 107, 96, 255)
ACCENT_DARK = (44, 75, 67, 255)
PAGE = (251, 252, 251, 255)
PAGE_SHADE = (225, 236, 228, 255)
LINE = (185, 206, 199, 255)
LINE_LIGHT = (215, 228, 222, 255)
MARK_BOX = (250, 300, 900, 880)

ANDROID_DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def mark() -> Image.Image:
    """The open book with a download badge, cropped to its own bounds."""
    image = Image.new("RGBA", (1024, 1024), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((250, 300, 500, 760), radius=28, fill=PAGE_SHADE)
    draw.rounded_rectangle((524, 300, 774, 760), radius=28, fill=PAGE)
    draw.rounded_rectangle((488, 300, 536, 760), radius=12, fill=ACCENT_DARK)
    for top in (380, 440, 500, 560, 620):
        draw.rounded_rectangle((290, top, 460, top + 18), radius=9, fill=LINE)
        draw.rounded_rectangle((564, top, 734, top + 18), radius=9, fill=LINE_LIGHT)
    draw.ellipse((640, 620, 900, 880), fill=ACCENT_DARK, outline=ACCENT, width=14)
    draw.rounded_rectangle((748, 690, 792, 800), radius=12, fill=PAGE)
    draw.polygon([(700, 790), (860, 790), (770, 860)], fill=PAGE)
    return image.crop(MARK_BOX)


def place(canvas: Image.Image, figure: Image.Image, width: float) -> None:
    scale = width / figure.width
    sized = figure.resize((round(figure.width * scale), round(figure.height * scale)), Image.Resampling.LANCZOS)
    left = (canvas.width - sized.width) // 2
    top = (canvas.height - sized.height) // 2
    canvas.alpha_composite(sized, (left, top))


def main() -> None:
    figure = mark()

    ios = Image.new("RGBA", (1024, 1024), ACCENT)
    place(ios, figure, 620)
    ios_path = ROOT / "ios" / "Ficbook" / "Assets.xcassets" / "AppIcon.appiconset" / "icon-1024.png"
    ios.convert("RGB").save(ios_path)

    res = ROOT / "android" / "app" / "src" / "main" / "res"
    for density, factor in ANDROID_DENSITIES.items():
        folder = res / f"mipmap-{density}"
        folder.mkdir(parents=True, exist_ok=True)
        # Adaptive foreground: 108dp, with the mark inside the 66dp safe zone.
        side = round(108 * factor)
        foreground = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        place(foreground, figure, 60 * factor)
        foreground.save(folder / "ic_launcher_foreground.png")
        # Legacy square icon for launchers without adaptive icons.
        side = round(48 * factor)
        legacy = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        ImageDraw.Draw(legacy).rounded_rectangle((0, 0, side - 1, side - 1), radius=round(side * 0.18), fill=ACCENT)
        place(legacy, figure, side * 0.62)
        legacy.save(folder / "ic_launcher.png")
    print("Wrote iOS and Android icons")


if __name__ == "__main__":
    main()
