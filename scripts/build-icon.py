"""Build VeriPatch .ico from Tabler-inspired shield-check artwork."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "gui" / "assets"


def draw_icon(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = size * 0.12
    shield = [
        (size * 0.5, pad),
        (size - pad, size * 0.22),
        (size - pad, size * 0.58),
        (size * 0.5, size - pad),
        (pad, size * 0.58),
        (pad, size * 0.22),
    ]
    draw.polygon(shield, fill=(37, 99, 235, 255))
    stroke = max(2, size // 32)
    check = [
        (size * 0.30, size * 0.52),
        (size * 0.44, size * 0.66),
        (size * 0.72, size * 0.36),
    ]
    draw.line(check, fill=(255, 255, 255, 255), width=stroke, joint="curve")
    return img


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    sizes = (256, 48, 32, 16)
    images = [draw_icon(size) for size in sizes]
    for size, image in zip(sizes, images, strict=True):
        image.save(ASSETS / f"veripatch-{size}.png")
    images[0].save(
        ASSETS / "veripatch.ico",
        format="ICO",
        sizes=[(image.width, image.height) for image in images],
        append_images=images[1:],
    )
    print(f"Wrote {ASSETS / 'veripatch.ico'}")


if __name__ == "__main__":
    main()
