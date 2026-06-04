import sys

YCD_MAGIC = b"YCD\x00"
COLOR_TABLE_REL = 0xE8 # color table offset, relative to the inner YCD header. so far been consistent, but havent tried it on everything
MAX_COLORS = 34 # havent seen any with more colors than 34, but not a guarantee


def find_color_table(blob: bytes) -> int:
    ycd_offset = blob.find(YCD_MAGIC)
    if ycd_offset == -1:
        raise ValueError("no inner YCD header found - not a .pal.yc blob?")
    return ycd_offset + COLOR_TABLE_REL


def read_palette(path: str) -> list[tuple[int, int, int, int]]:
    with open(path, "rb") as handle:
        blob = handle.read()

    try:
        table = find_color_table(blob)
    except ValueError:
        return []

    palette: list[tuple[int, int, int, int]] = []
    for i in range(MAX_COLORS):
        base = table + i * 4
        if base + 4 > len(blob):
            break
        palette.append((blob[base], blob[base + 1], blob[base + 2], blob[base + 3]))
    return palette


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    path = sys.argv[1]

    palette = read_palette(path)
    if not palette:
        print(f"no palette decoded from {path} (no YCD header found)")
        return

    print(f"{len(palette)} colors in {path}")
    print(f"  {'idx':>3}  {'R':>3} {'G':>3} {'B':>3} {'A':>3}   hex")
    for i, (r, g, b, a) in enumerate(palette):
        print(f"  {i:3d}  {r:3d} {g:3d} {b:3d} {a:3d}   #{r:02X}{g:02X}{b:02X}{a:02X}")


if __name__ == "__main__":
    main()