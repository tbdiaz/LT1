import asyncio
import sys

from winrt.windows.media.ocr import OcrEngine
from winrt.windows.storage import StorageFile, FileAccessMode
from winrt.windows.graphics.imaging import BitmapDecoder


async def _run(path):
    engine = OcrEngine.try_create_from_user_profile_languages()
    print("lang:", engine.recognizer_language.language_tag, file=sys.stderr)

    file = await StorageFile.get_file_from_path_async(path)
    stream = await file.open_async(FileAccessMode.READ)
    dec = await BitmapDecoder.create_async(stream)
    from winrt.windows.graphics.imaging import BitmapPixelFormat, BitmapTransform
    bmp = await dec.get_software_bitmap_async()
    result = await engine.recognize_async(bmp)
    lines = []
    for ln in result.lines:
        words = [(w.text, w.bounding_rect.x, w.bounding_rect.y,
                  w.bounding_rect.width, w.bounding_rect.height) for w in ln.words]
        if not words:
            continue
        x = min(w[1] for w in words)
        y = min(w[2] for w in words)
        lines.append((ln.text, x, y,
                      max(w[1] + w[3] for w in words) - x,
                      max(w[2] + w[4] for w in words) - y, words))
    return lines


if __name__ == "__main__":
    path = sys.argv[1]
    from PIL import Image
    img = Image.open(path)
    maxside = 3500
    if max(img.size) > maxside:
        scale = maxside / max(img.size)
        img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
        import os
        tmp = path.replace(".png", "_rs.png")
        img.save(tmp)
        path = tmp
    lines = asyncio.run(_run(path))
    for t, x, y, w, h, words in sorted(lines, key=lambda r: (r[2], r[1])):
        print(f"({x:.0f},{y:.0f}) {t}")