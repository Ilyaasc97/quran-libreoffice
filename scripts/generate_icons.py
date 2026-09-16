import zlib
import struct
import os

def write_png(width, height, rgba_data, filepath):
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    raw_lines = bytearray()
    for y in range(height):
        raw_lines.append(0)  # filter type 0 (None)
        raw_lines.extend(rgba_data[y * width * 4 : (y + 1) * width * 4])
    idat = chunk(b"IDAT", zlib.compress(bytes(raw_lines), 9))
    iend = chunk(b"IEND", b"")

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(header + ihdr + idat + iend)

def create_quran_icon(size, filepath):
    rgba = bytearray(size * size * 4)
    cx, cy = size / 2.0, size / 2.0
    pad = size * 0.08
    w, h = size - 2 * pad, size - 2 * pad

    green = (18, 120, 70, 255)       # Emerald Green
    gold = (235, 185, 52, 255)       # Gold
    dark_green = (10, 70, 40, 255)

    for y in range(size):
        for x in range(size):
            idx = (y * size + x) * 4
            # Check if inside book rectangle
            if pad <= x < size - pad and pad <= y < size - pad:
                # Border check (Gold border)
                border_thick = max(1, size * 0.08)
                is_border = (x < pad + border_thick or x >= size - pad - border_thick or
                             y < pad + border_thick or y >= size - pad - border_thick)

                # Spine on right side (Arabic book opens from left to right)
                is_spine = (x >= size - pad - border_thick * 1.5)

                # Center circle (Medallion)
                dist_sq = (x - cx) ** 2 + (y - cy) ** 2
                r_outer = size * 0.24
                r_inner = size * 0.12

                if is_border or is_spine:
                    col = gold
                elif dist_sq <= r_outer ** 2:
                    if dist_sq <= r_inner ** 2:
                        col = green
                    else:
                        col = gold
                else:
                    col = green
                rgba[idx:idx+4] = bytes(col)
            else:
                rgba[idx:idx+4] = bytes((0, 0, 0, 0))

    write_png(size, size, rgba, filepath)

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
out_dir = os.path.join(base_dir, "extension", "icons")
os.makedirs(out_dir, exist_ok=True)
create_quran_icon(16, os.path.join(out_dir, "quran_16.png"))
create_quran_icon(26, os.path.join(out_dir, "quran_26.png"))
print("Icons successfully created!")
