"""
YCD container header reading.

So far each .pak.yc filebegins with
this header.

    0x00  char[4]  magic "YCD\\0"
    0x04  u32      version
    0x08  u64      toc_offset
    0x38  u64      total_size

Only the header is parsed here. Toc is different per file type, so each tool in tools/ handles it their own way.
"""

import struct

MAGIC = b"YCD\x00"
TOC_OFFSET_POS = 0x08
TOTAL_SIZE_POS = 0x38


def read_u32(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_u64(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def is_ycd(data: bytes) -> bool:
    return len(data) >= 4 and data[0:4] == MAGIC


class YcdHeader:
    def __init__(self, version: int, toc_offset: int, total_size: int) -> None:
        self.version = version
        self.toc_offset = toc_offset
        self.total_size = total_size


def parse_header(data: bytes) -> YcdHeader:
    if not is_ycd(data):
        raise ValueError(f"not a YCD file (magic = {data[0:4]!r})")
    return YcdHeader(
        version=read_u32(data, 0x04),
        toc_offset=read_u64(data, TOC_OFFSET_POS),
        total_size=read_u64(data, TOTAL_SIZE_POS),
    )
