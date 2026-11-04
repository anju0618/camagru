import os
import struct
import sys
import unittest
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from app import png  # noqa: E402


def make_png(width, height, ctype, rows, filter_type=0):
    raw = b"".join(bytes([filter_type]) + r for r in rows)
    return (png.SIGNATURE
            + png._chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, ctype, 0, 0, 0))
            + png._chunk(b"IDAT", zlib.compress(raw))
            + png._chunk(b"IEND", b""))


class PngTest(unittest.TestCase):
    def test_roundtrip(self):
        rgba = bytearray(bytes(range(16)) * 2)  # 4x2 RGBA
        w, h, out = png.decode(png.encode(4, 2, rgba))
        self.assertEqual((w, h, bytes(out)), (4, 2, bytes(rgba)))

    def test_rgb_gets_opaque_alpha(self):
        data = make_png(2, 1, 2, [bytes([10, 20, 30, 40, 50, 60])])
        _, _, out = png.decode(data)
        self.assertEqual(bytes(out), bytes([10, 20, 30, 255, 40, 50, 60, 255]))

    def test_sub_filter(self):
        data = make_png(2, 1, 0, [bytes([5, 3])], filter_type=1)
        _, _, out = png.decode(data)
        self.assertEqual(bytes(out), bytes([5, 5, 5, 255, 8, 8, 8, 255]))

    def test_rejects_garbage(self):
        for bad in (b"", b"hello", png.SIGNATURE, png.SIGNATURE + b"\x00" * 40):
            with self.assertRaises(png.PngError):
                png.decode(bad)

    def test_rejects_bad_crc(self):
        data = bytearray(png.encode(2, 2, bytearray(16)))
        data[20] ^= 0xFF
        with self.assertRaises(png.PngError):
            png.decode(bytes(data))

    def test_rejects_decompression_bomb(self):
        raw = b"\x00" * 50000000
        data = (png.SIGNATURE
                + png._chunk(b"IHDR", struct.pack(">IIBBBBB", 2, 2, 8, 6, 0, 0, 0))
                + png._chunk(b"IDAT", zlib.compress(raw))
                + png._chunk(b"IEND", b""))
        with self.assertRaises(png.PngError):
            png.decode(data)

    def test_composite(self):
        base = (2, 1, bytearray([0, 0, 0, 255, 100, 100, 100, 255]))
        over = (2, 1, bytearray([255, 0, 0, 255, 0, 0, 0, 0]))
        _, _, out = png.composite(base, over)
        self.assertEqual(bytes(out), bytes([255, 0, 0, 255, 100, 100, 100, 255]))


if __name__ == "__main__":
    unittest.main()
