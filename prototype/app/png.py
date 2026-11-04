"""Minimal PNG decoder / encoder / compositor (standard library only).

Supports 8-bit, non-interlaced PNGs (gray, RGB, palette, gray+alpha, RGBA),
which is what browsers produce from canvas.toDataURL('image/png').
"""
import struct
import zlib

SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_SIDE = 2000
MAX_PIXELS = 2000000
CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


class PngError(ValueError):
    pass


def _chunk(kind, body):
    return (struct.pack(">I", len(body)) + kind + body
            + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF))


def _read_chunks(data):
    if data[:8] != SIGNATURE:
        raise PngError("not a PNG file")
    pos, size = 8, len(data)
    ihdr = plte = trns = None
    idat = []
    ended = False
    while pos + 12 <= size:
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        end = pos + 8 + length
        if end + 4 > size:
            raise PngError("truncated PNG")
        body = data[pos + 8:end]
        (crc,) = struct.unpack(">I", data[end:end + 4])
        if zlib.crc32(kind + body) & 0xFFFFFFFF != crc:
            raise PngError("bad chunk checksum")
        pos = end + 4
        if kind == b"IHDR":
            if ihdr is not None or length != 13:
                raise PngError("bad IHDR")
            ihdr = struct.unpack(">IIBBBBB", body)
        elif ihdr is None:
            raise PngError("IHDR must come first")
        elif kind == b"PLTE":
            plte = body
        elif kind == b"tRNS":
            trns = body
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            ended = True
            break
        elif not kind[0] & 0x20:
            raise PngError("unsupported critical chunk")
    if ihdr is None or not ended or not idat:
        raise PngError("incomplete PNG")
    return ihdr, plte, trns, b"".join(idat)


def decode(data):
    """Return (width, height, RGBA bytearray)."""
    (width, height, depth, ctype, comp, filt, interlace), plte, trns, idat = _read_chunks(data)
    if depth != 8 or ctype not in CHANNELS or comp != 0 or filt != 0 or interlace != 0:
        raise PngError("unsupported PNG format")
    if not (0 < width <= MAX_SIDE and 0 < height <= MAX_SIDE and width * height <= MAX_PIXELS):
        raise PngError("image dimensions out of range")
    if ctype == 3 and (plte is None or len(plte) % 3 or not plte):
        raise PngError("bad palette")

    bpp = CHANNELS[ctype]
    stride = width * bpp
    expected = height * (stride + 1)
    try:
        inflater = zlib.decompressobj()
        raw = inflater.decompress(idat, expected + 1)
    except zlib.error:
        raise PngError("corrupt image data")
    if len(raw) != expected or not inflater.eof:
        raise PngError("image data has the wrong size")

    palette = None
    if ctype == 3:
        palette = []
        for i in range(len(plte) // 3):
            alpha = trns[i] if trns and i < len(trns) else 255
            palette.append((plte[3 * i], plte[3 * i + 1], plte[3 * i + 2], alpha))

    out = bytearray(width * height * 4)
    prev = bytearray(stride)
    pos = 0
    for y in range(height):
        ftype = raw[pos]
        line = bytearray(raw[pos + 1:pos + 1 + stride])
        pos += stride + 1
        if ftype == 1:
            for i in range(bpp, stride):
                line[i] = (line[i] + line[i - bpp]) & 255
        elif ftype == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 255
        elif ftype == 3:
            for i in range(stride):
                left = line[i - bpp] if i >= bpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif ftype == 4:
            for i in range(min(bpp, stride)):
                line[i] = (line[i] + prev[i]) & 255
            for i in range(bpp, stride):
                a, b, c = line[i - bpp], prev[i], prev[i - bpp]
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                if pa <= pb and pa <= pc:
                    pred = a
                elif pb <= pc:
                    pred = b
                else:
                    pred = c
                line[i] = (line[i] + pred) & 255
        elif ftype != 0:
            raise PngError("bad filter type")
        prev = line

        row = out[y * width * 4:(y + 1) * width * 4]
        if ctype == 6:
            row[:] = line
        elif ctype == 2:
            row[0::4], row[1::4], row[2::4] = line[0::3], line[1::3], line[2::3]
            row[3::4] = b"\xff" * width
        elif ctype == 0:
            row[0::4] = row[1::4] = row[2::4] = line
            row[3::4] = b"\xff" * width
        elif ctype == 4:
            row[0::4] = row[1::4] = row[2::4] = line[0::2]
            row[3::4] = line[1::2]
        else:
            for x in range(width):
                idx = line[x]
                if idx >= len(palette):
                    raise PngError("bad palette index")
                row[x * 4:x * 4 + 4] = bytes(palette[idx])
        out[y * width * 4:(y + 1) * width * 4] = row
    return width, height, out


def encode(width, height, rgba):
    stride = width * 4
    raw = b"".join(b"\x00" + bytes(rgba[y * stride:(y + 1) * stride]) for y in range(height))
    return (SIGNATURE
            + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
            + _chunk(b"IDAT", zlib.compress(raw, 6))
            + _chunk(b"IEND", b""))


def composite(base, overlay):
    """Draw overlay (scaled to the base size) over base. Returns (w, h, RGBA)."""
    bw, bh, b = base
    ow, oh, o = overlay
    out = bytearray(b)
    # Flatten any transparency of the base onto white.
    for i in range(3, len(out), 4):
        a = out[i]
        if a != 255:
            ia = 255 - a
            out[i - 3] = (out[i - 3] * a + 255 * ia) // 255
            out[i - 2] = (out[i - 2] * a + 255 * ia) // 255
            out[i - 1] = (out[i - 1] * a + 255 * ia) // 255
            out[i] = 255
    xmap = [x * ow // bw * 4 for x in range(bw)]
    for y in range(bh):
        orow = (y * oh // bh) * ow * 4
        brow = y * bw * 4
        for x in range(bw):
            oi = orow + xmap[x]
            a = o[oi + 3]
            if a == 0:
                continue
            bi = brow + x * 4
            if a == 255:
                out[bi:bi + 3] = o[oi:oi + 3]
            else:
                ia = 255 - a
                out[bi] = (o[oi] * a + out[bi] * ia) // 255
                out[bi + 1] = (o[oi + 1] * a + out[bi + 1] * ia) // 255
                out[bi + 2] = (o[oi + 2] * a + out[bi + 2] * ia) // 255
    return bw, bh, out
