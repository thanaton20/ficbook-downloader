"""Draw the app icon and write the Mac and Windows icon files."""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
SIZE = 1024
PURPLE = (109, 40, 217, 255)
PURPLE_DARK = (76, 29, 149, 255)
PAGE = (255, 255, 255, 255)
PAGE_SHADE = (237, 233, 254, 255)
LINE = (196, 181, 253, 255)
ARROW = (255, 255, 255, 255)


def main() -> None:
    image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((48, 48, 976, 976), radius=224, fill=PURPLE)
    draw.rounded_rectangle((48, 48, 976, 280), radius=224, fill=(139, 92, 246, 255))
    draw.rectangle((48, 180, 976, 320), fill=PURPLE)

    draw.rounded_rectangle((250, 300, 500, 760), radius=28, fill=PAGE_SHADE)
    draw.rounded_rectangle((524, 300, 774, 760), radius=28, fill=PAGE)
    draw.rounded_rectangle((488, 300, 536, 760), radius=12, fill=PURPLE_DARK)

    for top in (380, 440, 500, 560, 620):
        draw.rounded_rectangle((290, top, 460, top + 18), radius=9, fill=LINE)
        draw.rounded_rectangle((564, top, 734, top + 18), radius=9, fill=(221, 214, 254, 255))

    draw.ellipse((640, 620, 900, 880), fill=PURPLE_DARK)
    draw.rounded_rectangle((748, 690, 792, 800), radius=12, fill=ARROW)
    draw.polygon([(700, 790), (860, 790), (770, 860)], fill=ARROW)

    png = ROOT / "AppIcon.png"
    image.save(png)

    iconset = ROOT / "AppIcon.iconset"
    iconset.mkdir(exist_ok=True)
    sizes = {
        "icon_16x16.png": 16,
        "icon_16x16@2x.png": 32,
        "icon_32x32.png": 32,
        "icon_32x32@2x.png": 64,
        "icon_128x128.png": 128,
        "icon_128x128@2x.png": 256,
        "icon_256x256.png": 256,
        "icon_256x256@2x.png": 512,
        "icon_512x512.png": 512,
        "icon_512x512@2x.png": 1024,
    }
    for name, side in sizes.items():
        image.resize((side, side), Image.Resampling.LANCZOS).save(iconset / name)

    image.save(
        ROOT / "AppIcon.ico",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
