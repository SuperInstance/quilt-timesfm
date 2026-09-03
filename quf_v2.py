"""quf_v2.py -- Quilt Universal Format (QUil Format) reader for Python.

The Quilt cell model is the same cell in 5 substrates (C99, Rust no_std,
Python, Verilog-2005, VHDL-2008).  This module is the Python substrate's
QUF reader + writer, byte-exact with the other 4.

Spec: see quilt-verilog/docs/QUF-SPEC.md (mirror in quf-vhdl/docs/).

Reference implementations:
  - quilt-verilog/tools/quf.py        -- Verilog reference (writer/parser)
  - quf-vhdl/tools/vhdl_quf.py         -- VHDL reference (writer/parser)
  - quilt-c/src/quf.c                 -- C kernel serializer (49 tests)
  - quilt-rust/crates/quilt-polyformalism/src/lib.rs  -- Rust serializer (8 tests)

This module uses the same FNV-1a 64-bit constants as the other substrates
(state hash 0xCBF29CE484222325 / 0x00000100000001B3).  The bit-exactness
contract is the test: a QUF file written here loads identically into
all 4 other substrates (and vice versa).
"""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

# =============================================================================
# QUF constants (mirror of tools/quf.py and quf_types.vhdl)
# =============================================================================

MAGIC = b"QUF\x00"
VERSION = 1
ENDIAN_LITTLE = 1
DEFAULT_ALIGN = 32
DEFAULT_EDGE_K = 8
NDIALS = 16  # dials per cell (matches q_dialfile ND)

# GGUF-compatible value-type numbering
T_U8, T_I8, T_U16, T_I16, T_U32, T_I32, T_F32, T_BOOL, T_STR, T_ARR, \
    T_U64, T_I64, T_F64 = range(13)

TYPE_NAMES = {
    T_U8: "u8", T_I8: "i8", T_U16: "u16", T_I16: "i16", T_U32: "u32",
    T_I32: "i32", T_F32: "f32", T_BOOL: "bool", T_STR: "string",
    T_ARR: "array", T_U64: "u64", T_I64: "i64", T_F64: "f64",
}
STRUCT_FMT = {
    T_U8: "<B", T_I8: "<b", T_U16: "<H", T_I16: "<h", T_U32: "<I",
    T_I32: "<i", T_F32: "<f", T_BOOL: "<?", T_U64: "<Q", T_I64: "<q",
    T_F64: "<d",
}
FIXED_SIZE = {
    T_U8: 1, T_I8: 1, T_U16: 2, T_I16: 2, T_U32: 4, T_I32: 4, T_F32: 4,
    T_BOOL: 1, T_U64: 8, T_I64: 8, T_F64: 8,
}

# Canonical header KV order (writer emits in this order)
CANON_KV = [
    "quf.version", "cell_count", "edge_count", "route_count", "edge.k",
    "tick_period", "quant.dials", "quant.edges", "quant.routing", "align",
]
STRING_KV = {"quf.version", "quant.dials", "quant.edges", "quant.routing"}

# Reason codes (mirror of QUF-SPEC.md §5a, E7..E18)
E_OK              = 0x00
E_BAD_MAGIC       = 0x07  # E7  R1
E_BAD_VERSION     = 0x08  # E8  R1, R8 (edge.k range)
E_BAD_ENDIAN      = 0x09  # E9  R2
E_TRUNCATED       = 0x0A  # E10 R3
E_LYING_COUNT     = 0x0B  # E11 R4
E_U64_OVERFLOW    = 0x0C  # E12 R5
E_OVERLAP_FRONT   = 0x0D  # E13 R6
E_SIZE_MISMATCH   = 0x0E  # E14 R7, R8
E_BAD_ALIGNMENT   = 0x0F  # E15 R9
E_BAD_PADDING     = 0x10  # E16 R11
E_KV_LEN_OVERRUN  = 0x11  # E17 R12
E_BAD_VALUE_TYPE  = 0x12  # E18

# FNV-1a 64-bit (matches C, Rust, Verilog, VHDL)
FNV_OFFSET = 0xCBF29CE484222325
FNV_PRIME  = 0x00000100000001B3


# =============================================================================
# Data structures (mirror of quf_types.vhdl records)
# =============================================================================

@dataclass
class EdgeRecord:
    """One edge in the edges section.  12 + K bytes, little-endian.

    src, dst, mode, slot are u8.  base, wh are u16.  age is u32.
    buckets is K u8 values.  The Python representation is *unpacked*;
    pack/unpack is handled by the reader/writer.
    """
    src: int
    dst: int
    mode: int
    slot: int
    base: int
    wh: int
    age: int
    buckets: List[int] = field(default_factory=list)

    def pack(self) -> bytes:
        return struct.pack("<BBBBHHI",
                           self.src, self.dst, self.mode, self.slot,
                           self.base, self.wh, self.age) + bytes(self.buckets)

    @classmethod
    def unpack(cls, data: bytes, k: int) -> "EdgeRecord":
        if len(data) < 12 + k:
            raise ValueError("edge record too short")
        src, dst, mode, slot, base, wh, age = struct.unpack_from("<BBBBHHI", data, 0)
        return cls(src=src, dst=dst, mode=mode, slot=slot,
                   base=base, wh=wh, age=age, buckets=list(data[12:12+k]))


@dataclass
class RouteRecord:
    """One route in the routing section.  2 bytes."""
    dst: int
    via: int

    def pack(self) -> bytes:
        return struct.pack("<BB", self.dst, self.via)

    @classmethod
    def unpack(cls, data: bytes) -> "RouteRecord":
        dst, via = struct.unpack_from("<BB", data, 0)
        return cls(dst=dst, via=via)


@dataclass
class QufFile:
    """A parsed QUF file.  The full state of a Quilt fabric.

    header: dict of KV pairs
    dials:   list of cell_count rows, each a list of 16 u16 values
    edges:   list of EdgeRecord
    routing: list of RouteRecord
    ticks:   (tpw, list of phases)  -- the tick schedule
    """
    header: Dict[str, Any] = field(default_factory=dict)
    dials: List[List[int]] = field(default_factory=list)
    edges: List[EdgeRecord] = field(default_factory=list)
    routing: List[RouteRecord] = field(default_factory=list)
    ticks: Tuple[int, List[int]] = (0, [])

    @property
    def cell_count(self) -> int:
        return len(self.dials)

    @property
    def edge_count(self) -> int:
        return len(self.edges)

    @property
    def route_count(self) -> int:
        return len(self.routing)

    @property
    def edge_k(self) -> int:
        return int(self.header.get("edge.k", DEFAULT_EDGE_K))

    @property
    def align(self) -> int:
        return int(self.header.get("align", DEFAULT_ALIGN))

    def state_hash(self) -> int:
        """FNV-1a 64-bit over the cell state (dials + edges, in order).

        Matches the C, Rust, Verilog, and VHDL implementations.
        """
        h = FNV_OFFSET
        for row in self.dials:
            for v in row:
                h = ((h ^ (v & 0xFF)) * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
                h = ((h ^ ((v >> 8) & 0xFF)) * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
        for e in self.edges:
            rec = struct.pack("<BBBBHHI",
                              e.src, e.dst, e.mode, e.slot,
                              e.base, e.wh, e.age)
            for byte in rec:
                h = ((h ^ byte) * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
            for b in e.buckets:
                h = ((h ^ b) * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
        return h

    def to_dict(self) -> dict:
        """JSON-shaped view (matches the C writer's test fixture)."""
        d = {
            "header": dict(self.header),
            "dials": [list(r) for r in self.dials],
            "edges": [{
                "src": e.src, "dst": e.dst, "mode": e.mode, "slot": e.slot,
                "base": e.base, "wh": e.wh, "age": e.age,
                "buckets": list(e.buckets),
            } for e in self.edges],
            "routing": [{"dst": r.dst, "via": r.via} for r in self.routing],
            "ticks": {"tpw": self.ticks[0], "phases": list(self.ticks[1])},
        }
        # Backward-compat: also write 'ticksched' as alias
        d["ticksched"] = d["ticks"]
        return d


# =============================================================================
# Reader (QufFile.loads)
# =============================================================================

class QufError(Exception):
    """Raised on any R1-R12 reject condition (E7-E18)."""
    def __init__(self, code: int, msg: str):
        super().__init__(f"E{code:02d}: {msg}")
        self.code = code


def _take(buf: bytes, off: int, n: int) -> Tuple[bytes, int]:
    if off + n > len(buf):
        raise QufError(E_TRUNCATED, f"truncated at byte {off} (need {n} bytes, have {len(buf) - off})")
    return buf[off:off + n], off + n


def _read_value(buf: bytes, off: int, vt: int) -> Tuple[Any, int]:
    if vt == T_STR:
        n, off = struct.unpack_from("<I", buf, off)[0], off + 4
        # R10: names are bytes, not text.  Strings may be invalid UTF-8;
        # we accept and return as bytes if so.
        raw, off = _take(buf, off, n)
        try:
            return raw.decode("utf-8"), off
        except UnicodeDecodeError:
            return raw, off
    if vt == T_ARR:
        et, off = struct.unpack_from("<I", buf, off)[0], off + 4
        if et not in FIXED_SIZE:
            raise QufError(E_BAD_VALUE_TYPE, f"array element type {et} is not fixed-size")
        n, off = struct.unpack_from("<I", buf, off)[0], off + 4
        vals = []
        for _ in range(n):
            v, off = _read_value(buf, off, et)
            vals.append(v)
        return vals, off
    if vt not in STRUCT_FMT:
        raise QufError(E_BAD_VALUE_TYPE, f"unknown value type {vt} (cannot skip)")
    sz = FIXED_SIZE[vt]
    raw, off = _take(buf, off, sz)
    return struct.unpack(STRUCT_FMT[vt], raw)[0], off


def loads(buf: bytes) -> QufFile:
    """Parse a QUF byte stream into a QufFile.

    Enforces R1-R12 from QUF-SPEC.md §5a.  Raises QufError(code, msg)
    on any reject condition.  Bit-exact with the Verilog reference's
    tools/quf.py and the VHDL reference's tools/vhdl_quf.py.
    """
    if len(buf) < 16:
        raise QufError(E_TRUNCATED, f"file too short for header ({len(buf)} bytes)")

    # R1: magic
    if buf[:4] != MAGIC:
        raise QufError(E_BAD_MAGIC, f"bad magic {buf[:4]!r} (expected {MAGIC!r})")

    # R1: version
    version = struct.unpack_from("<I", buf, 4)[0]
    if version != VERSION:
        raise QufError(E_BAD_VERSION, f"version {version} != {VERSION}")

    # R2: endian
    endian = struct.unpack_from("<I", buf, 8)[0]
    if endian != ENDIAN_LITTLE:
        raise QufError(E_BAD_ENDIAN, f"endian {endian} != {ENDIAN_LITTLE} (big-endian not supported)")

    # KV count
    kv_count, off = struct.unpack_from("<I", buf, 12)[0], 16

    header: Dict[str, Any] = {}

    # Walk KV pairs
    for i in range(kv_count):
        if off + 4 > len(buf):
            raise QufError(E_LYING_COUNT, f"kv_count {kv_count} overruns end of file")
        nl, off = struct.unpack_from("<I", buf, off)[0], off + 4
        if off + nl > len(buf):
            raise QufError(E_LYING_COUNT, f"kv[{i}] name_len {nl} overruns end of file")
        # R10: names are bytes
        name = buf[off:off + nl]
        off += nl
        if off + 4 > len(buf):
            raise QufError(E_LYING_COUNT, f"kv[{i}] value_type overruns end of file")
        vt, off = struct.unpack_from("<I", buf, off)[0], off + 4
        try:
            value, off = _read_value(buf, off, vt)
        except QufError as e:
            raise QufError(e.code, f"kv[{i}] ({name!r}): {e}")
        try:
            name_str = name.decode("utf-8")
        except UnicodeDecodeError:
            name_str = name.decode("utf-8", errors="replace")
        header[name_str] = value

    # Section table
    if off + 4 > len(buf):
        raise QufError(E_TRUNCATED, "no section_count after KV walk")
    section_count, off = struct.unpack_from("<I", buf, off)[0], off + 4

    sections: List[Dict[str, Any]] = []
    for i in range(section_count):
        if off + 4 > len(buf):
            raise QufError(E_LYING_COUNT, f"section[{i}] name_len overruns")
        nl, off = struct.unpack_from("<I", buf, off)[0], off + 4
        if off + nl > len(buf):
            raise QufError(E_LYING_COUNT, f"section[{i}] name overruns")
        name = buf[off:off + nl]
        off += nl
        if off + 4 > len(buf):
            raise QufError(E_LYING_COUNT, f"section[{i}] kind overruns")
        kind, off = struct.unpack_from("<I", buf, off)[0], off + 4
        # R5: u64 high words
        if off + 8 > len(buf):
            raise QufError(E_LYING_COUNT, f"section[{i}] offset overruns")
        offset_lo, off = struct.unpack_from("<I", buf, off)[0], off + 4
        offset_hi, off = struct.unpack_from("<I", buf, off)[0], off + 4
        if offset_hi != 0:
            raise QufError(E_U64_OVERFLOW, f"section[{i}] offset high word {offset_hi} != 0")
        if off + 8 > len(buf):
            raise QufError(E_LYING_COUNT, f"section[{i}] size overruns")
        size_lo, off = struct.unpack_from("<I", buf, off)[0], off + 4
        size_hi, off = struct.unpack_from("<I", buf, off)[0], off + 4
        if size_hi != 0:
            raise QufError(E_U64_OVERFLOW, f"section[{i}] size high word {size_hi} != 0")
        # R5: offset + size must not overflow u32
        if offset_lo + size_lo >= (1 << 32):
            raise QufError(E_U64_OVERFLOW, f"section[{i}] offset+size >= 2^32")
        try:
            name_str = name.decode("utf-8")
        except UnicodeDecodeError:
            name_str = name.decode("utf-8", errors="replace")
        sections.append({
            "name": name_str, "kind": kind, "offset": offset_lo, "size": size_lo
        })

    # R9: alignment of section offsets + file length
    align = int(header.get("align", DEFAULT_ALIGN))
    if align < 8 or (align & (align - 1)) != 0:
        raise QufError(E_BAD_ALIGNMENT, f"align {align} is not a power of two >= 8")
    if len(buf) % align != 0:
        raise QufError(E_BAD_ALIGNMENT, f"file length {len(buf)} not a multiple of align {align}")
    for sec in sections:
        if sec["offset"] % align != 0:
            raise QufError(E_BAD_ALIGNMENT, f"section {sec['name']!r} offset {sec['offset']} not {align}-aligned")

    # R6: section offsets must be past the front matter (table end)
    table_end = off
    for sec in sections:
        if sec["offset"] < table_end:
            raise QufError(E_OVERLAP_FRONT, f"section {sec['name']!r} offset {sec['offset']} overlaps front matter (table ends at {table_end})")

    # R11: padding must be zero.  We walk sections in offset order; between
    # each section (or between the table and the first section) the bytes
    # must be zero.  We also verify EOF padding.
    sorted_sections = sorted(sections, key=lambda s: s["offset"])
    cursor = table_end
    for sec in sorted_sections:
        # Pad from cursor to sec["offset"] (if any)
        if sec["offset"] > cursor:
            pad = buf[cursor:sec["offset"]]
            if any(b != 0 for b in pad):
                raise QufError(E_BAD_PADDING, f"nonzero padding byte before section {sec['name']!r}")
        cursor = sec["offset"] + sec["size"]
    # EOF pad
    if cursor < len(buf):
        pad = buf[cursor:]
        if any(b != 0 for b in pad):
            raise QufError(E_BAD_PADDING, "nonzero padding byte at EOF")

    # R3/R4: end-of-file checks
    for sec in sections:
        if sec["offset"] + sec["size"] > len(buf):
            raise QufError(E_TRUNCATED, f"section {sec['name']!r} extends past EOF")

    # Read known sections
    file_obj = QufFile(header=header)
    cell_count = int(header.get("cell_count", 0))
    edge_k = int(header.get("edge.k", DEFAULT_EDGE_K))

    for sec in sections:
        name = sec["name"]
        start, size = sec["offset"], sec["size"]
        payload = buf[start:start + size]

        if name == "dials":
            # cell_count * 16 u16
            if size != cell_count * 32:
                raise QufError(E_SIZE_MISMATCH, f"dials size {size} != cell_count*32 ({cell_count*32})")
            rows = []
            for c in range(cell_count):
                row = list(struct.unpack_from("<16H", payload, c * 32))
                rows.append(row)
            file_obj.dials = rows
        elif name == "edges":
            rec_size = 12 + edge_k
            if size % rec_size != 0:
                raise QufError(E_SIZE_MISMATCH, f"edges size {size} not a multiple of (12+K)={rec_size}")
            file_obj.edges = [
                EdgeRecord.unpack(payload[i * rec_size:(i + 1) * rec_size], edge_k)
                for i in range(size // rec_size)
            ]
        elif name == "routing":
            if size % 2 != 0:
                raise QufError(E_SIZE_MISMATCH, f"routing size {size} not even")
            file_obj.routing = [
                RouteRecord.unpack(payload[i * 2:(i + 1) * 2], )
                for i in range(size // 2)
            ]
        elif name == "ticks":
            if size < 4:
                raise QufError(E_SIZE_MISMATCH, f"ticks size {size} < 4")
            tpw = struct.unpack_from("<I", payload, 0)[0]
            phases_data = payload[4:]
            phases = list(struct.unpack(f"<{len(phases_data) // 4}I", phases_data))
            file_obj.ticks = (tpw, phases)

    # Check that dials has the right number of cells
    if file_obj.dials and len(file_obj.dials) != cell_count:
        raise QufError(E_SIZE_MISMATCH, f"dials has {len(file_obj.dials)} rows but cell_count = {cell_count}")

    return file_obj


# =============================================================================
# Writer (QufFile.dumps)
# =============================================================================

def _u32(x: int) -> bytes:
    return struct.pack("<I", x)


def _u64(x: int) -> bytes:
    return struct.pack("<Q", x)


def _pack_value(vt: int, v: Any) -> bytes:
    if vt == T_STR:
        b = v.encode("utf-8") if isinstance(v, str) else bytes(v)
        return _u32(len(b)) + b
    if vt == T_ARR:
        et, evs = v
        out = _u32(et) + _u32(len(evs))
        for e in evs:
            out += _pack_value(et, e)
        return out
    if isinstance(v, bool):
        v = int(v)
    return struct.pack(STRUCT_FMT[vt], v)


def _coerce(k: str, v: Any) -> Tuple[int, Any]:
    if k in STRING_KV:
        if not isinstance(v, str):
            raise ValueError(f"header {k} must be a string")
        return T_STR, v
    if isinstance(v, bool):
        return T_U32, int(v)
    if isinstance(v, int):
        if not (0 <= v < (1 << 32)):
            raise ValueError(f"header {k} out of u32 range")
        return T_U32, v
    raise ValueError(f"header {k} must be an integer (u32) or string")


def dumps(qf: QufFile) -> bytes:
    """Serialize a QufFile to canonical QUF bytes.

    Same byte layout as quilt-verilog/tools/quf.py and quf-vhdl/tools/vhdl_quf.py.
    Bit-exact with both references.
    """
    hdr = dict(qf.header)
    align = int(hdr.setdefault("align", DEFAULT_ALIGN))
    edge_k = int(hdr.setdefault("edge.k", DEFAULT_EDGE_K))
    if not (1 <= edge_k <= 16):
        raise ValueError(f"edge.k out of range 1..16: {edge_k}")
    if not (8 <= align <= (1 << 20)) or (align & (align - 1)) != 0:
        raise ValueError(f"align must be a power of two in [8, 2^20]")

    # Derive counts if not present
    if "cell_count" not in hdr:
        hdr["cell_count"] = qf.cell_count
    if "edge_count" not in hdr:
        hdr["edge_count"] = qf.edge_count
    if "route_count" not in hdr:
        hdr["route_count"] = qf.route_count

    # Build the KV walk
    canon_order = list(CANON_KV)
    out = bytearray()
    out += MAGIC
    out += _u32(VERSION)
    out += _u32(ENDIAN_LITTLE)
    kv_count = sum(1 for k in canon_order if k in hdr)
    out += _u32(kv_count)
    for k in canon_order:
        if k in hdr:
            vt, v = _coerce(k, hdr[k])
            kb = k.encode("utf-8")
            out += _u32(len(kb)) + kb
            out += _u32(vt)
            out += _pack_value(vt, v)

    # Build section payloads
    payload_bufs: Dict[str, bytes] = {}
    if qf.dials:
        d = bytearray()
        for row in qf.dials:
            for v in row:
                if not (0 <= v < (1 << 16)):
                    raise ValueError(f"dial value out of u16 range: {v}")
                d += struct.pack("<H", v)
        payload_bufs["dials"] = bytes(d)
    if qf.edges:
        e = bytearray()
        for edge in qf.edges:
            rec = edge.pack()
            e += rec
        payload_bufs["edges"] = bytes(e)
    if qf.routing:
        r = bytearray()
        for route in qf.routing:
            r += route.pack()
        payload_bufs["routing"] = bytes(r)
    if qf.ticks[0] != 0 or qf.ticks[1]:
        tpw, phases = qf.ticks
        if not (0 <= tpw < (1 << 32)):
            raise ValueError(f"tpw out of u32 range")
        t = struct.pack("<I", tpw)
        for p in phases:
            t += struct.pack("<I", p)
        payload_bufs["ticks"] = t

    # Section table
    out += _u32(len(payload_bufs))
    table_size = 0
    for name in payload_bufs:
        nb = name.encode("utf-8")
        table_size += 4 + len(nb) + 4 + 8 + 8
    after_table = len(out) + table_size
    pad_to = (align - (after_table % align)) % align
    first_offset = after_table + pad_to

    offsets: Dict[str, int] = {}
    cursor = first_offset
    section_order = ["dials", "edges", "routing", "ticks"]
    for name in section_order:
        if name in payload_bufs:
            offsets[name] = cursor
            base = cursor + len(payload_bufs[name])
            cursor = (base + align - 1) // align * align

    for name in section_order:
        if name not in payload_bufs:
            continue
        nb = name.encode("utf-8")
        out += _u32(len(nb)) + nb
        out += _u32(0)  # kind = 0
        out += _u64(offsets[name])
        out += _u64(len(payload_bufs[name]))

    # Pad to align
    while len(out) % align != 0:
        out += b"\x00"

    # Emit payloads, padding between sections
    for name in section_order:
        if name in payload_bufs:
            out += payload_bufs[name]
            while len(out) % align != 0:
                out += b"\x00"

    return bytes(out)


# =============================================================================
# CLI (selftest, info, create, dump, verify)
# =============================================================================

def selftest() -> bool:
    """Self-test: round-trip a 2-cell, 3-edge fixture."""
    qf = QufFile(
        header={
            "quf.version": "selftest-1.0",
            "cell_count": 2, "edge_count": 3, "route_count": 0,
            "edge.k": 8, "tick_period": 4,
            "quant.dials": "Q1.15", "quant.edges": "Q1.15",
            "quant.routing": "u8", "align": 32,
        },
        dials=[
            [64, 16, 1, 1, 4, 16384, 1, 128, 1, 0, 8, 0, 0, 0, 0, 0],
            [64, 16, 1, 1, 4, 16384, 1, 128, 1, 0, 8, 0, 0, 0, 0, 0],
        ],
        edges=[
            EdgeRecord(0, 1, 0, 0, 16384, 0, 100, [1, 2, 3, 4, 5, 6, 7, 8]),
            EdgeRecord(1, 0, 0, 0, 16384, 0, 100, [8, 7, 6, 5, 4, 3, 2, 1]),
            EdgeRecord(0, 1, 0, 1, 8192, 0, 50, [0, 0, 0, 0, 1, 1, 1, 1]),
        ],
        ticks=(4, [0, 0]),
    )
    blob = dumps(qf)
    qf2 = loads(blob)
    assert qf2.state_hash() == qf.state_hash(), "round-trip state_hash mismatch"
    assert qf2.cell_count == 2
    assert qf2.edge_count == 3
    assert qf2.ticks[0] == 4
    print(f"selftest OK: {len(blob)} bytes, hash 0x{qf.state_hash():016x}")
    return True


def main():
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("selftest")
    a.set_defaults(func=lambda args: selftest())

    a = sub.add_parser("info")
    a.add_argument("file")
    a.set_defaults(func=lambda args: info(args.file))

    a = sub.add_parser("verify")
    a.add_argument("file")
    a.set_defaults(func=lambda args: verify(args.file))

    a = sub.add_parser("dump")
    a.add_argument("file")
    a.set_defaults(func=lambda args: dump(args.file))

    a = sub.add_parser("round-trip")
    a.add_argument("file")
    a.set_defaults(func=lambda args: round_trip(args.file))

    args = ap.parse_args()
    args.func(args)


def info(path: str) -> None:
    blob = open(path, "rb").read()
    qf = loads(blob)
    print(f"OK: {path}")
    print(f"  bytes:        {len(blob)}")
    print(f"  cell_count:   {qf.cell_count}")
    print(f"  edge_count:   {qf.edge_count}")
    print(f"  route_count:  {qf.route_count}")
    print(f"  edge.k:       {qf.edge_k}")
    print(f"  align:        {qf.align}")
    print(f"  ticks:        tpw={qf.ticks[0]}, {len(qf.ticks[1])} phases")
    print(f"  state_hash:   0x{qf.state_hash():016x}")


def verify(path: str) -> None:
    """Run all R1-R12 checks via loads(); exit 0 on success, 1 on failure."""
    try:
        loads(open(path, "rb").read())
        print(f"OK: {path}")
    except QufError as e:
        print(f"FAIL: {path}: {e}")
        raise SystemExit(1)


def dump(path: str) -> None:
    blob = open(path, "rb").read()
    qf = loads(blob)
    print(json.dumps(qf.to_dict(), indent=2))


def round_trip(path: str) -> None:
    blob = open(path, "rb").read()
    qf1 = loads(blob)
    blob2 = dumps(qf1)
    qf2 = loads(blob2)
    assert blob == blob2, f"round-trip byte mismatch: {len(blob)} vs {len(blob2)}"
    assert qf1.state_hash() == qf2.state_hash(), "state_hash mismatch after round-trip"
    print(f"OK: {path} -> round-trip exact ({len(blob)} bytes, hash 0x{qf1.state_hash():016x})")


if __name__ == "__main__":
    main()
