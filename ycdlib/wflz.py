import struct

HEADER_SIZE = 16
BLOCK_SIZE = 4
MIN_MATCH_LEN = 5
SIGNATURES = (b"WFLZ", b"ZLFW")


def decompress(data: bytes, offset: int = 0) -> tuple[bytes, int, int]:
    sig = data[offset:offset + 4]
    if sig not in SIGNATURES:
        raise ValueError(f"bad wfLZ signature {sig!r}")

    compressed_size = struct.unpack_from("<I", data, offset + 4)[0]
    decompressed_size = struct.unpack_from("<I", data, offset + 8)[0]

    if decompressed_size == 0 or decompressed_size > (1 << 22):
        raise ValueError(f"implausible decompressed size {decompressed_size}")
    if compressed_size == 0 or offset + HEADER_SIZE + compressed_size > len(data) + 64:
        raise ValueError(f"implausible compressed size {compressed_size}")

    out = bytearray(decompressed_size)
    dst = 0
    src = offset + HEADER_SIZE
    num_literals = data[offset + 15]

    while True:
        for _ in range(num_literals):
            out[dst] = data[src]
            dst += 1
            src += 1

        while True:
            dist = struct.unpack_from("<H", data, src)[0]
            length = data[src + 2]
            num_literals = data[src + 3]
            src += BLOCK_SIZE

            if length != 0:
                copy_len = length + MIN_MATCH_LEN - 1
                for _ in range(copy_len):
                    out[dst] = out[dst - dist]
                    dst += 1

            if num_literals == 0:
                if dist == 0 and length == 0:
                    return bytes(out[:dst]), compressed_size, decompressed_size
                continue
            break


def find_blocks(data: bytes) -> list[int]:
    """return offsets of every byte position whose 4 bytes are a wfLZ signature."""
    hits: list[int] = []
    for magic in SIGNATURES:
        pos = 0
        while True:
            pos = data.find(magic, pos)
            if pos == -1:
                break
            hits.append(pos)
            pos += 1
    hits.sort()
    return hits


def find_valid_blocks(data: bytes) -> list[dict]:
    blocks: list[dict] = []
    for offset in find_blocks(data):
        try:
            decompressed, csize, dsize = decompress(data, offset)
        except (ValueError, IndexError, struct.error):
            continue
        if len(decompressed) != dsize:
            continue
        blocks.append({
            "offset": offset,
            "compressed_size": csize,
            "decompressed_size": dsize,
            "data": decompressed,
        })
    return blocks
