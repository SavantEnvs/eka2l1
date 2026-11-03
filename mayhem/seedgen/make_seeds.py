#!/usr/bin/env python3
"""Regenerates the synthetic seeds under mayhem/<target>/testsuite/ (rsc legacy/calypso, spi, rom, fpsx, nvg-tlv).

The layouts follow the readers in src/emu/loader/src/{rsc,spi,rom,fpsx,nvg_tlv}.cpp field by field, so each seed is
accepted by the parser and reaches past the header checks. Run from the repo root: python3 mayhem/seedgen/make_seeds.py
"""
import os
import struct

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def put(target, name, data):
    d = os.path.join(ROOT, target, "testsuite")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, name), "wb") as f:
        f.write(bytes(data))


def u8(v):
    return struct.pack("<B", v)


def u16(v):
    return struct.pack("<H", v)


def u32(v):
    return struct.pack("<I", v)


def be16(v):
    return struct.pack(">H", v)


def be32(v):
    return struct.pack(">I", v)


# ---------------------------------------------------------------- rsc: rsc_file_legacy (first uint32 is not a modern UID)
def rsc_legacy_plain(unicode_index):
    res = [b"hello\x00", b"world!!\x00\x01\x02"]
    data = b"".join(res)
    index_off = 4 + len(data)
    offsets, pos = [4], 4
    for r in res:
        pos += len(r)
        offsets.append(pos)
    table = b"".join(u16(o) for o in offsets)
    sect_size = len(table) + (1 if unicode_index else 0)
    return u16(index_off) + u16(sect_size) + data + table


class Bits:
    def __init__(self):
        self.bits = []

    def put(self, value, n):
        for i in range(n):
            self.bits.append((value >> i) & 1)

    def tell(self):
        return len(self.bits)

    def data(self):
        out = bytearray((len(self.bits) + 7) // 8)
        for i, b in enumerate(self.bits):
            out[i >> 3] |= b << (i & 7)
        return bytes(out)


def rsc_legacy_compressed():
    # lookup table: one entry = a literal byte; resources: lookup ref + literal, 16-bit literal, 3-bit and 8-bit repeats
    lk = Bits()
    lk.put(1, 1), lk.put(0, 1), lk.put(0x41, 8)
    lk_offsets = [0, lk.tell()]

    res = Bits()
    offs = [0]
    # resource 1: lookup[0] then a literal byte
    res.put(0, 1), res.put(0, 1)
    res.put(1, 1), res.put(0, 1), res.put(0x42, 8)
    offs.append(res.tell())
    # resource 2: 16-bit literal, then 3-bit repeat of 4 bytes
    res.put(1, 1), res.put(1, 1), res.put(0, 1), res.put(0xBEEF, 16)
    res.put(1, 1), res.put(1, 1), res.put(1, 1), res.put(0, 1), res.put(1, 3)
    for b in b"abcd":
        res.put(b, 8)
    offs.append(res.tell())
    # resource 3: 8-bit repeat of 2 bytes
    res.put(1, 1), res.put(1, 1), res.put(1, 1), res.put(1, 1), res.put(2, 8)
    res.put(0x10, 8), res.put(0x20, 8)
    offs.append(res.tell())

    count = 3
    lookup_off_table = b"".join(u16(o) for o in lk_offsets)
    lookup_data = lk.data()
    res_index_off = 11 + len(lookup_off_table) + len(lookup_data)
    head = u16(4) + u16(count) + u8(0) + u8(1) + u16(res_index_off) + u16(64) + u8(1)
    assert len(head) == 11
    return head + lookup_off_table + lookup_data + b"".join(u16(o) for o in offs) + res.data()


# ---------------------------------------------------------------- rsc: rsc_file_morden calypso variant (low 16 bits of uid0 == 4)
def rsc_calypso():
    bits = 3                      # dict token bits -> 8 dictionary entries with unk1 == 0
    dict_index_off = 4 + 7 + 2    # 13, hard-wired in the reader
    dict_entries = (1 << bits) - 0
    dict_off = dict_index_off + dict_entries * 2
    dict_bits = Bits()
    d_offsets = []
    for i in range(dict_entries):
        d_offsets.append(dict_bits.tell())
        dict_bits.put(0x30 + i, 8)
    d_offsets.append(dict_bits.tell())
    dict_bytes = dict_bits.data()
    res_bits = Bits()
    r_offsets = [0]
    for _ in range(4):
        res_bits.put(1, 3)
        res_bits.put(2, 3)
        r_offsets.append(res_bits.tell())
    res_index_off = dict_off + len(dict_bytes)
    out = bytearray(res_index_off)
    out[0:4] = u32(0x00000004)
    out[5] = 0
    out[6:8] = u16(res_index_off)
    out[8:10] = u16(32)
    out[10] = bits
    for i in range(dict_entries):
        out[dict_index_off + 2 * i: dict_index_off + 2 * i + 2] = u16(d_offsets[i])
    out[dict_off:dict_off + len(dict_bytes)] = dict_bytes
    return bytes(out) + b"".join(u16(o) for o in r_offsets[:4]) + res_bits.data()


# ---------------------------------------------------------------- spi
SPI_UID = 0x10205C2B


def checked_uid_checksum(uids):
    # Mirrors crypt::calculate_checked_uid_checksum (see src/emu/common/src/crypt.cpp); only used to build a seed.
    def crc_for(bs):
        crc = 0
        for b in bs:
            crc = ((crc << 8) ^ _CRC[((crc >> 8) ^ b) & 0xFF]) & 0xFFFF
        return crc
    raw = b"".join(u32(u) for u in uids)
    even = bytes(raw[i] for i in range(0, 12, 2))
    odd = bytes(raw[i] for i in range(1, 12, 2))
    return (crc_for(odd) << 16) | crc_for(even)


def _crc_table():
    t = []
    for i in range(256):
        c = i << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
        t.append(c)
    return t


_CRC = _crc_table()


def spi_file(entries, type_uid=0):
    uids = [SPI_UID, type_uid, 0]
    out = b"".join(u32(u) for u in uids) + u32(checked_uid_checksum(uids)) + b"\x00" * 16
    for name, payload in entries:
        out += u32(len(name)) + u32(len(payload)) + name + payload
        pad = 4 - ((len(name) + len(payload)) % 4)
        if pad < 4:
            out += b"\x00" * pad
    return out


# ---------------------------------------------------------------- rom
ROM_BASE = 0x80000000


def rom_header(root_list_off, **kw):
    h = bytearray(496)
    h[124:128] = u32(ROM_BASE)
    h[140:144] = u32(ROM_BASE)
    h[144:148] = u32(kw.get("rom_size", 0x1000))
    h[148:152] = u32(ROM_BASE + root_list_off)
    h[232:233] = u8(9)
    h[233:234] = u8(2)
    h[234:236] = u16(1234)
    h[236:240] = u32(kw.get("compress_type", 0))
    h[244:248] = u32(kw.get("uncompress_size", 0))
    h[328:332] = u32(kw.get("pageable_rom_start", 0))
    h[336:340] = u32(kw.get("rom_page_idx", 0))
    return bytes(h)


def rom_entry(name, size, addr, is_dir):
    raw = u32(size) + u32(addr) + u8(0x10 if is_dir else 0) + u8(len(name)) + name.encode("utf-16-le")
    return raw


def rom_dir(entries):
    body = b""
    for e in entries:
        body += e
        if (len(body) + 4) % 4:
            body += b"\x00\x00"
    return u32(len(body) + 4) + body


def rom_image():
    root_list = 0x200
    root_dir_off = 0x220
    sub_off = 0x300
    sub = rom_dir([rom_entry("z.dll", 16, ROM_BASE + 0x400, False), rom_entry("Bee", 8, ROM_BASE + 0x410, False)])
    top = rom_dir([
        rom_entry("sys", 0, ROM_BASE + sub_off, True),
        rom_entry("a.txt", 12, ROM_BASE + 0x420, False),
        rom_entry("Beta", 4, ROM_BASE + 0x430, False),
    ])
    img = bytearray(0x600)
    img[:496] = rom_header(root_list)
    img[root_list:root_list + 12] = u32(1) + u32(0) + u32(ROM_BASE + root_dir_off)
    img[root_dir_off:root_dir_off + len(top)] = top
    img[sub_off:sub_off + len(sub)] = sub
    return bytes(img)


def rom_paged_image():
    img = bytearray(rom_image())
    page_idx = 0x500
    pageable_start = 0x400
    hdr = rom_header(0x200, rom_page_idx=page_idx, pageable_rom_start=pageable_start,
                     uncompress_size=pageable_start + 0x3000)
    img[:496] = hdr
    pages = [
        (0x540, 4, 0, 1),   # stored
        (0x544, 0, 0, 1),   # empty page
        (0x548, 6, 1, 1),   # bytepair-compressed
    ]
    for i, (start, size, comp, attr) in enumerate(pages):
        img[page_idx + 8 * i: page_idx + 8 * i + 8] = u32(start) + u16(size) + u8(comp) + u8(attr)
    img[0x540:0x544] = b"ROMP"
    img[0x548:0x54E] = bytes([0x00, 0x04, 0x41, 0x42, 0x43, 0x44])
    return bytes(img)


# ---------------------------------------------------------------- fpsx
def tlv(t, content):
    return u8(t) + u8(len(content)) + content


def tlv_large(t, content):
    return u8(t) + be16(len(content)) + content


def fpsx_tlvs():
    erase = u8(1) + u8(0) + u8(0) + be32(0) + be32(0x1000) + be32(0x2000) + be32(0x3000)
    entries = [
        tlv(18, erase),
        tlv(194, b"RM-1\x00"),
        tlv(244, b"ROFS image\x00second\x00"),
        tlv(230, be32(1700000000)),
        tlv_large(228, b"\x01\x02\x03\x04"),
        tlv(205, b"\x07"),
    ]
    inner = [tlv(230, be32(1)), tlv(195, b"sha1\x00")]
    array_content = u8(len(inner)) + b"".join(inner)
    entries.append(u8(238) + be16(len(array_content)) + array_content)
    return entries


def block_binary(ctype, data_size, data_off):
    hdr = u8(1) + be16(0x1C08) + be16(0xABCD) + u8(1) + be32(data_size) + be32(data_off)
    return u8(ctype) + u8(0) + u8(0x17) + u8(len(hdr)) + hdr + u8(0x5A)


def block_rofs(ctype, btype, desc, data_size, data_off, core=False):
    hdr = b"\x11" * 20 + desc.ljust(12, b"\x00") + u8(1) + be16(0x1C08) + be16(0x1234) + be32(data_size) + be32(data_off)
    if core:
        hdr += b"\x22" * 20 + u16(0x5555)
    return u8(ctype) + u8(0) + u8(btype) + u8(len(hdr)) + hdr + u8(0x6B)


def block_h30(ctype, data_size, data_off):
    hdr = u8(1) + be16(0x1C08) + be16(0x4321) + b"\x33" * 8 + be32(data_size) + be32(data_off)
    return u8(ctype) + u8(0) + u8(0x30) + u8(len(hdr)) + hdr + u8(0x7C)


def block_h3a(ctype):
    hdr = u8(1) + u16(0x1C08) + be16(0x4321) + b"ROFX image\x00\x00"
    return u8(ctype) + u8(0) + u8(0x3A) + u8(len(hdr)) + hdr + u8(0x7C)


def block_h49(ctype, data_size, data_off):
    hdr = be32(data_size) + be16(0x1111) + b"\x44" * 18 + be32(data_off)
    return u8(ctype) + u8(0) + u8(0x49) + u8(len(hdr)) + hdr + u8(0x7D)


def fpsx_image(blocks, tlvs):
    tlv_bytes = b"".join(tlvs)
    header_size = 4 + len(tlv_bytes)
    head = u8(0xB0) + be32(header_size) + be32(len(tlvs)) + tlv_bytes
    out = bytearray(head)
    for b, data_size in blocks:
        out += b
        out += b"\x00" * (-(-data_size // 512) * 512)
    return bytes(out)


# ---------------------------------------------------------------- nvg: NVG-TLV (nvg_type & 3 == 1), nvg_tlv.cpp
# Same opcode layouts as the TLV builder in src/tests/epoc/loader/nvg.cpp: 52-byte header, then a recording of
# OpenVG calls (clear, set, load matrix, create paint/path, append path data, draw).
TLV_CLEAR, TLV_SETI, TLV_SETF, TLV_SET_COLOR, TLV_SET_PAINT, TLV_LOAD_MATRIX = 0, 1, 2, 7, 8, 9
TLV_APPEND_PATH_DATA, TLV_DRAW_PATH, TLV_CREATE_PAINT, TLV_CREATE_PATH = 15, 16, 22, 23
VG_PATH_DATATYPE_S_32, VG_PATH_DATATYPE_F = 2, 3
SEG_MOVE_TO, SEG_LINE_TO, SEG_SCCWARC_TO, SEG_CLOSE = 1 << 1, 2 << 1, 9 << 1, 0
SEG_REL = 1


def f32(v):
    return struct.pack("<f", v)


def i32(v):
    return struct.pack("<i", v)


def tlv_header():
    h = bytearray(52)
    h[0:3] = b"nvg"
    h[3] = 1
    h[4:6] = u16(52)
    h[6:8] = u16(1)
    return bytes(h)


def tlv_clear(w, h):
    return u8(TLV_CLEAR) + f32(0) + f32(0) + f32(w) + f32(h)


def tlv_create_path(datatype, scale, bias):
    return u8(TLV_CREATE_PATH) + i32(0) + u8(datatype) + f32(scale) + f32(bias) + i32(0) + i32(0) + i32(0) + i32(1)


def tlv_append(segments, coords):
    out = u8(TLV_APPEND_PATH_DATA) + i32(1) + u16(len(segments)) + bytes(segments) + u16(len(coords))
    for c in coords:
        out += c
    return out


def tlv_draw(modes):
    return u8(TLV_DRAW_PATH) + i32(1) + u16(modes)


def nvg_tlv_plain():
    return (tlv_header() + tlv_clear(100, 50) + tlv_create_path(VG_PATH_DATATYPE_F, 1.0, 0.0)
            + tlv_append([SEG_MOVE_TO, SEG_LINE_TO], [f32(1), f32(2), f32(3), f32(4)]) + tlv_draw(2))


def nvg_tlv_styled():
    d = tlv_header() + tlv_clear(240, 156)
    d += u8(TLV_SETI) + u16(0x1100) + u16(0x1400)
    d += u8(TLV_LOAD_MATRIX) + b"".join(f32(v) for v in (1, 0, 0, 0, -1, 0, 3, 5, 1))
    d += u8(TLV_CREATE_PAINT) + i32(7) + u8(TLV_SET_COLOR) + i32(7) + u32(0xFF800040)
    d += u8(TLV_SET_PAINT) + i32(7) + u8(2)
    d += u8(TLV_SETF) + u16(0x1110) + f32(2.5)
    d += tlv_create_path(VG_PATH_DATATYPE_S_32, 0.5, 1.0)
    d += tlv_append([SEG_MOVE_TO | SEG_REL, SEG_LINE_TO | SEG_REL, SEG_CLOSE], [i32(-4), i32(6), i32(8), i32(2)])
    d += tlv_draw(2) + u8(TLV_SETI) + u16(0x1101) + u16(0x1901)
    d += tlv_append([SEG_MOVE_TO, SEG_SCCWARC_TO], [f32(c) for c in (0, 0, 2, 3, 0, 4, 0)]) + tlv_draw(1)
    return d + b"\x00" * 8


def main():
    put("nvg", "tlv_plain.nvg", nvg_tlv_plain())
    put("nvg", "tlv_styled.nvg", nvg_tlv_styled())

    put("rsc", "legacy_plain.rsc", rsc_legacy_plain(False))
    put("rsc", "legacy_unicode_index.rsc", rsc_legacy_plain(True))
    put("rsc", "legacy_compressed.rsc", rsc_legacy_compressed())
    put("rsc", "calypso.rsc", rsc_calypso())

    put("spi", "multi_entry.spi", spi_file([
        (b"ecom_a.rsc", b"0123456789"),
        (b"b", b"q"),
        (b"cc", b"xyz"),
        (b"dddd", b"\x00" * 7),
    ]))
    put("spi", "typed.spi", spi_file([(b"x", b"y")], type_uid=0x10009D8D))

    put("rom", "tree.rom", rom_image())
    put("rom", "paged.rom", rom_paged_image())

    put("fpsx", "uda.fpsx", fpsx_image([(block_binary(84, 0x40, 0x0), 0x40)], fpsx_tlvs()))
    put("fpsx", "rofs.fpsx", fpsx_image([(block_binary(84, 0x40, 0x0), 0x40),
                                         (block_rofs(93, 0x27, b"ROFS", 0x20, 0x10), 0x20)], fpsx_tlvs()))
    put("fpsx", "rofx.fpsx", fpsx_image([(block_binary(84, 0x40, 0x0), 0x40),
                                         (block_rofs(93, 0x27, b"ROFX", 0x20, 0x10), 0x20),
                                         (block_h3a(86), 0)], fpsx_tlvs()))
    put("fpsx", "core.fpsx", fpsx_image([(block_binary(84, 0x40, 0x0), 0x40),
                                         (block_rofs(93, 0x28, b"CORE", 0x20, 0x10, core=True), 0x20),
                                         (block_h30(84, 0x10, 0x100), 0x10),
                                         (block_h49(86, 0x10, 0x200), 0x10)], fpsx_tlvs()))


if __name__ == "__main__":
    main()
