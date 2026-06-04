import json
import os
import struct
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ycdlib.ycd import parse_header   # noqa: E402

TOC_BASE = 0xC0
ENTRY_STRIDE = 16
ALIGN_CONST = 0x10
ASSET_MARKERS = (b".anb.yc", b".pal.yc")
STRTAB_LIMIT = 0x2000


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def toc_entry(data: bytes, index: int) -> tuple[int, int, int, int]:
    base = TOC_BASE + index * ENTRY_STRIDE
    return (
        read_u32(data, base + 0),
        read_u32(data, base + 4),
        read_u32(data, base + 8),
        read_u32(data, base + 12),
    )


def collect_asset_names(data: bytes) -> list[str]:
    found: list[tuple[int, str]] = []
    seen: set[str] = set()
    for marker in ASSET_MARKERS:
        pos = 0
        while True:
            pos = data.find(marker, pos)
            if pos == -1:
                break
            start = pos
            while start > 0 and 0x20 <= data[start - 1] <= 0x7E:
                start -= 1
            path = data[start:pos + len(marker)].decode("utf-8", errors="replace")
            if start < STRTAB_LIMIT and path not in seen:
                seen.add(path)
                found.append((start, path))
            pos += 1
    found.sort(key=lambda pair: pair[0])
    return [path for _, path in found]


def sniff_type(blob: bytes) -> str:
    head = blob[: min(len(blob), 0x200)]
    if b"YCD\x00" in head:
        return "nested-ycd"
    if any(m in head for m in (b"WFLZ", b"ZLFW")):
        return "wflz-compressed"
    return "raw/unknown"


def extract(pak_path: str, output_dir: str) -> None:
    with open(pak_path, "rb") as handle:
        data = handle.read()

    parse_header(data)
    names = collect_asset_names(data)

    pak_name = os.path.splitext(os.path.basename(pak_path))[0]
    root = os.path.join(output_dir, pak_name)
    os.makedirs(root, exist_ok=True)

    manifest: list[dict] = []
    written = 0
    for i, name in enumerate(names):
        toc_index = 2 + i * 2
        size, flags, align, offset = toc_entry(data, toc_index)

        if align != ALIGN_CONST or not (0 < offset < len(data)):
            manifest.append({
                "name": name, "toc_index": toc_index,
                "offset": offset, "size": size, "type": "INVALID-toc-entry",
            })
            continue

        blob = data[offset:offset + size]
        rel = name.replace("\\", "/").replace("/", os.sep)
        out_path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as handle:
            handle.write(blob)
        written += 1

        manifest.append({
            "name": name, "toc_index": toc_index,
            "offset": offset, "size": size, "type": sniff_type(blob),
        })

    with open(os.path.join(root, "manifest.json"), "w", encoding="utf-8") as handle:
        json.dump({
            "source": os.path.basename(pak_path),
            "asset_count": len(names),
            "assets": manifest,
        }, handle, indent=2)

    print(f"Extracted {written} assets to {root}")
    print(f"Manifest: {os.path.join(root, 'manifest.json')}")


def main() -> None:
    if len(sys.argv) != 3:
        print(__doc__)
        return
    extract(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
