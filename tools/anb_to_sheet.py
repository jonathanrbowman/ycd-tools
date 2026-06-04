import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ycdlib import wflz
from tools.read_palette import read_palette

try:
    from PIL import Image, ImageDraw
except ImportError:
    print("Pillow required: pip install Pillow")
    raise

INDEX_RECORD_SIZE = 32
INDEX_TAG_POS = 0x10
INDEX_TAG_VALUE = 0x20
INDEX_WIDTH_POS = 0x18
INDEX_HEIGHT_POS = 0x1C
MIN_RECORD_RUN = 8

# minas default color palette, pulled from her default pal file you get if you extract Mina.pal.yc and call read_palette on it
# if you dont pass a palette file when parsing a .anb file, then we toss this palettte at it just to have something to look at
DEFAULT_PALETTE: list[tuple[int, int, int, int]] = [
    (112, 112, 112, 0),
    (0, 0, 0, 255),
    (248, 8, 40, 255),
    (255, 233, 197, 255),
    (248, 176, 48, 255),
    (255, 255, 255, 255),
    (166, 117, 254, 255),
    (245, 183, 132, 255),
    (248, 176, 48, 255),
    (168, 168, 168, 255),
    (155, 160, 239, 255),
    (226, 201, 255, 255),
    (21, 125, 98, 255),
    (174, 108, 55, 255),
    (248, 248, 136, 255),
    (123, 123, 123, 255),
    (197, 151, 130, 255),
    (130, 60, 61, 255),
    (79, 21, 7, 255),
    (92, 60, 13, 255),
]

def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def find_index_table(data: bytes) -> int | None:
    best_start = None
    best_len = 0
    pos = 0
    limit = len(data) - INDEX_RECORD_SIZE
    while pos <= limit:
        if read_u32(data, pos + INDEX_TAG_POS) == INDEX_TAG_VALUE:
            run = 0
            p = pos
            while p <= limit and read_u32(data, p + INDEX_TAG_POS) == INDEX_TAG_VALUE:
                w = read_u32(data, p + INDEX_WIDTH_POS)
                h = read_u32(data, p + INDEX_HEIGHT_POS)
                if not (1 <= w <= 256 and 1 <= h <= 256):
                    break
                run += 1
                p += INDEX_RECORD_SIZE
            if run > best_len:
                best_len = run
                best_start = pos
            pos = p if run > 0 else pos + 1
        else:
            pos += 1
    if best_len >= MIN_RECORD_RUN:
        return best_start
    return None


def parse_index_records(data: bytes, start: int) -> list[tuple[int, int]]:
    records: list[tuple[int, int]] = []
    pos = start
    limit = len(data) - INDEX_RECORD_SIZE
    while pos <= limit and read_u32(data, pos + INDEX_TAG_POS) == INDEX_TAG_VALUE:
        w = read_u32(data, pos + INDEX_WIDTH_POS)
        h = read_u32(data, pos + INDEX_HEIGHT_POS)
        if not (1 <= w <= 256 and 1 <= h <= 256):
            break
        records.append((w, h))
        pos += INDEX_RECORD_SIZE
    return records


def best_alignment(blocks: list[dict], records: list[tuple[int, int]]) -> int:
    best_k = 0
    best_score = -1
    for k in range(-4, 9):
        score = 0
        for i, (w, h) in enumerate(records):
            bi = i + k
            if 0 <= bi < len(blocks) and blocks[bi]["decompressed_size"] == w * h:
                score += 1
        if score > best_score:
            best_score = score
            best_k = k
    return best_k


def render_cell(
    buf: bytes,
    width: int,
    height: int,
    palette: list[tuple[int, int, int, int]]
) -> "Image.Image":
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pixels = img.load()
    for i in range(min(len(buf), width * height)):
        idx = buf[i]
        pixels[i % width, i // width] = palette[idx] if idx < len(palette) else (255, 0, 255, 255)
    return img

def _plan_rows(
    box_sizes: list[tuple[int, int]],
    target_width: int,
    pad: int
) -> list[list[int]]:
    rows: list[list[int]] = []
    current: list[int] = []
    used = pad
    for index, (bw, _bh) in enumerate(box_sizes):
        needed = bw + pad
        if current and used + needed > target_width:
            rows.append(current)
            current = []
            used = pad
        current.append(index)
        used += needed
    if current:
        rows.append(current)
    return rows


def build_sheet(
    cells: list[tuple[bytes, int, int]],
    palette: list[tuple[int, int, int, int]],
    out_png: str, target_width: int = 1400, target_box: int = 48,
    inner_pad: int = 6
) -> None:
    pad = 6
    label_h = 8

    if not cells:
        Image.new("RGBA", (pad, pad), (24, 24, 28, 255)).save(out_png)
        return

    max_dim = max(max(w, h) for _, w, h in cells)
    scale = max(1, target_box // max_dim)

    scaled_sizes = [(w * scale, h * scale) for _, w, h in cells]
    box_sizes = [(sw + 2 * inner_pad, sh + 2 * inner_pad) for sw, sh in scaled_sizes]

    widest = max(bw for bw, _ in box_sizes)
    effective_width = max(target_width, widest + pad * 2)

    rows = _plan_rows(box_sizes, effective_width, pad)

    row_heights: list[int] = []
    for row in rows:
        tallest = max(box_sizes[i][1] for i in row)
        row_heights.append(tallest + label_h + pad)

    sheet_h = pad + sum(row_heights)
    sheet = Image.new("RGBA", (effective_width, sheet_h), (24, 24, 28, 255))
    draw = ImageDraw.Draw(sheet)

    y = pad
    for row, row_h in zip(rows, row_heights):
        x = pad
        box_h = row_h - label_h - pad
        for cell_index in row:
            buf, w, h = cells[cell_index]
            sw, sh = scaled_sizes[cell_index]
            bw, _bh = box_sizes[cell_index]

            draw.rectangle([x, y, x + bw - 1, y + box_h - 1], outline=(50, 50, 58, 255))

            cell = render_cell(buf, w, h, palette)
            scaled = cell.resize((sw, sh), Image.NEAREST)

            ox = x + inner_pad
            oy = y + box_h - inner_pad - sh
            sheet.alpha_composite(scaled, (ox, oy))
            draw.text((x, y + box_h), str(cell_index), fill=(150, 150, 160, 255))

            x += bw + pad
        y += row_h

    sheet.save(out_png)


def generate(
    anb_path: str,
    out_png: str,
    cells_dir: str | None = None,
    palette_path: str | None = None
) -> dict:
    with open(anb_path, "rb") as handle:
        data = handle.read()

    blocks = wflz.find_valid_blocks(data)
    if not blocks:
        raise ValueError("no valid wfLZ blocks found - is this an .anb sprite file?")

    table_start = find_index_table(data)
    if table_start is None:
        raise ValueError("could not locate the cell index table")
    records = parse_index_records(data, table_start)
    k = best_alignment(blocks, records)

    if palette_path:
        palette = read_palette(palette_path) or DEFAULT_PALETTE
    else:
        palette = DEFAULT_PALETTE

    cells: list[tuple[bytes, int, int]] = []
    exact = 0
    for i, (w, h) in enumerate(records):
        bi = i + k
        if not (0 <= bi < len(blocks)):
            continue
        block = blocks[bi]
        if block["decompressed_size"] == w * h:
            exact += 1
        cells.append((block["data"], w, h))

    used_indices: set[int] = set()
    for buf, _w, _h in cells:
        used_indices.update(buf)
    palette_source = palette_path if palette_path else "(default Mina palette)"
    used_colors = {
        idx: (palette[idx] if idx < len(palette) else None)
        for idx in sorted(used_indices)
    }

    build_sheet(cells, palette, out_png)

    if cells_dir:
        os.makedirs(cells_dir, exist_ok=True)
        for i, (buf, w, h) in enumerate(cells):
            img = render_cell(buf, w, h, palette)
            scale = max(1, 192 // max(w, h))
            img.resize((w * scale, h * scale), Image.NEAREST).save(
                os.path.join(cells_dir, f"cell_{i:04d}_{w}x{h}.png"))

    return {"blocks": len(blocks), "records": len(records), "alignment_k": k,
            "exact_fit": exact, "cells": len(cells),
            "index_table_offset": table_start, "sheet": out_png,
            "palette_source": palette_source, "used_colors": used_colors}


def main() -> None:
    if len(sys.argv) < 3:
        print(__doc__)
        return
    anb_path = sys.argv[1]
    out_png = sys.argv[2]
    cells_dir = sys.argv[sys.argv.index("--cells") + 1] if "--cells" in sys.argv else None
    palette_path = sys.argv[sys.argv.index("--palette") + 1] if "--palette" in sys.argv else None

    result = generate(anb_path, out_png, cells_dir, palette_path)
    print(f"  wfLZ blocks        : {result['blocks']}")
    print(f"  index records      : {result['records']}")
    print(f"  index table offset : 0x{result['index_table_offset']:X}")
    print(f"  alignment k        : {result['alignment_k']}")
    print(f"  cells rendered     : {result['cells']} ({result['exact_fit']} exact-fit)")
    print(f"  sheet              : {result['sheet']}")
    print(f"  palette source     : {result['palette_source']}")
    print("  colors used        :")
    for idx, rgba in result["used_colors"].items():
        if rgba is None:
            print(f"    index {idx}: <out of palette range>")
        else:
            r, g, b, a = rgba
            print(f"    index {idx}: RGBA({r:3d},{g:3d},{b:3d},{a:3d})  #{r:02X}{g:02X}{b:02X}{a:02X}")


if __name__ == "__main__":
    main()