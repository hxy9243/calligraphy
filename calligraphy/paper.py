"""Traditional Xuan writing paper (朱絲欄宣紙) and weathered cinnabar QR seal stamp (朱砂印章二維碼)."""
from functools import lru_cache
import hashlib
import math
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

DEFAULT_STAMP_URL = "https://calligraphy-demo-production.up.railway.app"


def get_default_stamp_url() -> str:
    return os.environ.get("CALLIGRAPHY_STAMP_URL", DEFAULT_STAMP_URL).strip()


# ============================================================================
# Pure-Python ISO/IEC 18004 QR Code Matrix Generator (Byte mode, Versions 1-10)
# ============================================================================

_GF_EXP = [0] * 512
_GF_LOG = [0] * 256


def _init_gf() -> None:
    x = 1
    for i in range(255):
        _GF_EXP[i] = x
        _GF_LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        _GF_EXP[i] = _GF_EXP[i - 255]


_init_gf()


def _gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _GF_EXP[_GF_LOG[a] + _GF_LOG[b]]


def _rs_generator_poly(degree: int) -> List[int]:
    poly = [1]
    for i in range(degree):
        next_poly = [0] * (len(poly) + 1)
        root = _GF_EXP[i]
        for j, coeff in enumerate(poly):
            next_poly[j] ^= coeff
            next_poly[j + 1] ^= _gf_mul(coeff, root)
        poly = next_poly
    return poly


def _rs_encode(data: Sequence[int], ec_len: int) -> List[int]:
    gen = _rs_generator_poly(ec_len)
    reg = [0] * ec_len
    for byte in data:
        factor = byte ^ reg[0]
        reg = reg[1:] + [0]
        if factor != 0:
            for j in range(ec_len):
                reg[j] ^= _gf_mul(gen[j + 1], factor)
    return reg


# (total_codewords, ec_per_block, num_blocks_g1, data_per_block_g1, num_blocks_g2, data_per_block_g2)
_QR_VERSION_TABLE: Dict[Tuple[int, str], Tuple[int, int, int, int, int, int]] = {
    # Level L (~7% recovery - high capacity up to 134 bytes in V6)
    (1, "L"): (26, 7, 1, 19, 0, 0),
    (2, "L"): (44, 10, 1, 34, 0, 0),
    (3, "L"): (70, 15, 1, 55, 0, 0),
    (4, "L"): (100, 20, 1, 80, 0, 0),
    (5, "L"): (134, 26, 1, 108, 0, 0),
    (6, "L"): (172, 18, 2, 68, 0, 0),
    # Level M (~15% recovery)
    (1, "M"): (26, 10, 1, 16, 0, 0),
    (2, "M"): (44, 16, 1, 28, 0, 0),
    (3, "M"): (70, 26, 1, 44, 0, 0),
    (4, "M"): (100, 18, 2, 32, 0, 0),
    (5, "M"): (134, 24, 2, 43, 0, 0),
    (6, "M"): (172, 16, 4, 27, 0, 0),
    # Level Q (~25% recovery - great for weathered seal stamps)
    (1, "Q"): (26, 13, 1, 13, 0, 0),
    (2, "Q"): (44, 22, 1, 22, 0, 0),
    (3, "Q"): (70, 18, 2, 17, 0, 0),
    (4, "Q"): (100, 26, 2, 24, 0, 0),
    (5, "Q"): (134, 18, 2, 15, 2, 16),
    (6, "Q"): (172, 24, 4, 19, 0, 0),
    # Level H (~30% recovery)
    (1, "H"): (26, 17, 1, 9, 0, 0),
    (2, "H"): (44, 28, 1, 16, 0, 0),
    (3, "H"): (70, 22, 2, 13, 0, 0),
    (4, "H"): (100, 16, 4, 9, 0, 0),
    (5, "H"): (134, 22, 2, 11, 2, 12),
    (6, "H"): (172, 28, 4, 15, 0, 0),
}

_ALIGNMENT_POSITIONS: Dict[int, List[int]] = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
}

_ECC_FORMAT_BITS = {"L": 0b01, "M": 0b00, "Q": 0b11, "H": 0b10}


def _bch_format_bits(ecc: str, mask: int) -> int:
    data = (_ECC_FORMAT_BITS[ecc] << 3) | mask
    rem = data << 10
    for i in range(4, -1, -1):
        if rem & (1 << (i + 10)):
            rem ^= 0x537 << i
    return ((data << 10) | rem) ^ 0x5412


def _mask_fn(mask: int, r: int, c: int) -> bool:
    if mask == 0:
        return (r + c) % 2 == 0
    if mask == 1:
        return r % 2 == 0
    if mask == 2:
        return c % 3 == 0
    if mask == 3:
        return (r + c) % 3 == 0
    if mask == 4:
        return (r // 2 + c // 3) % 2 == 0
    if mask == 5:
        return (r * c) % 2 + (r * c) % 3 == 0
    if mask == 6:
        return ((r * c) % 2 + (r * c) % 3) % 2 == 0
    return ((r + c) % 2 + (r * c) % 3) % 2 == 0


def _penalty_score(grid: np.ndarray) -> int:
    n = grid.shape[0]
    score = 0
    # Rule 1: runs of 5+ same-color modules
    for line in list(grid) + list(grid.T):
        run_val = int(line[0])
        run_len = 1
        for val in line[1:]:
            v = int(val)
            if v == run_val:
                run_len += 1
            else:
                if run_len >= 5:
                    score += 3 + (run_len - 5)
                run_val = v
                run_len = 1
        if run_len >= 5:
            score += 3 + (run_len - 5)
    # Rule 2: 2x2 blocks
    same_2x2 = (
        (grid[:-1, :-1] == grid[1:, :-1])
        & (grid[:-1, :-1] == grid[:-1, 1:])
        & (grid[:-1, :-1] == grid[1:, 1:])
    )
    score += 3 * int(np.sum(same_2x2))
    # Rule 3: finder-like patterns
    pat1 = np.array([1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0], dtype=np.uint8)
    pat2 = np.array([0, 0, 0, 0, 1, 0, 1, 1, 1, 0, 1], dtype=np.uint8)
    for line in list(grid) + list(grid.T):
        for i in range(n - 10):
            window = line[i : i + 11]
            if np.array_equal(window, pat1) or np.array_equal(window, pat2):
                score += 40
    # Rule 4: balance of dark modules
    dark_pct = (np.sum(grid) * 100.0) / (n * n)
    steps = int(abs(dark_pct - 50.0) // 5)
    score += steps * 10
    return score


@lru_cache(maxsize=32)
def encode_qr_matrix(text: str, ecc: str = "Q") -> np.ndarray:
    """Encode text into a boolean 2D numpy QR matrix (True = dark module)."""
    payload = text.encode("utf-8")
    ecc = ecc.upper()
    chosen_version = None
    for fallback_ecc in (ecc, "M", "L"):
        for ver in range(1, 7):
            spec = _QR_VERSION_TABLE.get((ver, fallback_ecc))
            if not spec:
                continue
            _, _, nb1, dp1, nb2, dp2 = spec
            data_cap = nb1 * dp1 + nb2 * dp2
            # Byte mode: 4 bits mode + 8 bits len (for V1-9) = 12 bits -> 2 bytes overhead
            if len(payload) + 2 <= data_cap:
                chosen_version = ver
                ecc = fallback_ecc
                break
        if chosen_version is not None:
            break
    if chosen_version is None:
        raise ValueError("QR payload too long for versions 1-6")

    _, ec_len, nb1, dp1, nb2, dp2 = _QR_VERSION_TABLE[(chosen_version, ecc)]
    total_data = nb1 * dp1 + nb2 * dp2

    bits: List[int] = []

    def _append_bits(val: int, length: int) -> None:
        for i in range(length - 1, -1, -1):
            bits.append((val >> i) & 1)

    # Byte mode indicator (0100) + character count (8 bits for V1-9)
    _append_bits(0b0100, 4)
    _append_bits(len(payload), 8)
    for b in payload:
        _append_bits(b, 8)

    # Terminator (up to 4 zeros)
    rem_bits = total_data * 8 - len(bits)
    for _ in range(min(4, rem_bits)):
        bits.append(0)
    while len(bits) % 8 != 0:
        bits.append(0)

    data_bytes = [
        sum(bits[i + j] << (7 - j) for j in range(8))
        for i in range(0, len(bits), 8)
    ]
    pad_Socket = [0xEC, 0x11]
    idx = 0
    while len(data_bytes) < total_data:
        data_bytes.append(pad_Socket[idx % 2])
        idx += 1

    # Split into blocks and compute Reed-Solomon EC codewords
    blocks_data: List[List[int]] = []
    blocks_ec: List[List[int]] = []
    pos = 0
    for _ in range(nb1):
        blk = data_bytes[pos : pos + dp1]
        pos += dp1
        blocks_data.append(blk)
        blocks_ec.append(_rs_encode(blk, ec_len))
    for _ in range(nb2):
        blk = data_bytes[pos : pos + dp2]
        pos += dp2
        blocks_data.append(blk)
        blocks_ec.append(_rs_encode(blk, ec_len))

    # Interleave data and EC codewords
    interleaved: List[int] = []
    max_dp = max(dp1, dp2)
    for i in range(max_dp):
        for blk in blocks_data:
            if i < len(blk):
                interleaved.append(blk[i])
    for i in range(ec_len):
        for ec_blk in blocks_ec:
            interleaved.append(ec_blk[i])

    stream_bits: List[int] = []
    for byte in interleaved:
        for i in range(7, -1, -1):
            stream_bits.append((byte >> i) & 1)
    # Remainder bits (7 for V2-6)
    if 2 <= chosen_version <= 6:
        stream_bits.extend([0] * 7)

    size = 17 + 4 * chosen_version
    base = np.zeros((size, size), dtype=np.uint8)
    reserved = np.zeros((size, size), dtype=bool)

    def _place_finder(top: int, left: int) -> None:
        for r in range(-1, 8):
            for c in range(-1, 8):
                rr, cc = top + r, left + c
                if 0 <= rr < size and 0 <= cc < size:
                    reserved[rr, cc] = True
                    if (
                        0 <= r <= 6
                        and 0 <= c <= 6
                        and (
                            r in (0, 6)
                            or c in (0, 6)
                            or (2 <= r <= 4 and 2 <= c <= 4)
                        )
                    ):
                        base[rr, cc] = 1

    _place_finder(0, 0)
    _place_finder(0, size - 7)
    _place_finder(size - 7, 0)

    # Alignment patterns
    align = _ALIGNMENT_POSITIONS[chosen_version]
    for ar in align:
        for ac in align:
            if reserved[ar, ac]:
                continue
            for r in range(-2, 3):
                for c in range(-2, 3):
                    reserved[ar + r, ac + c] = True
                    if max(abs(r), abs(c)) in (0, 2):
                        base[ar + r, ac + c] = 1

    # Timing patterns
    for i in range(8, size - 8):
        if not reserved[6, i]:
            reserved[6, i] = True
            base[6, i] = 1 if i % 2 == 0 else 0
        if not reserved[i, 6]:
            reserved[i, 6] = True
            base[i, 6] = 1 if i % 2 == 0 else 0

    # Dark module & format areas
    reserved[4 * chosen_version + 9, 8] = True
    base[4 * chosen_version + 9, 8] = 1
    for i in range(9):
        reserved[8, i] = True
        reserved[i, 8] = True
    for i in range(8):
        reserved[8, size - 1 - i] = True
        reserved[size - 1 - i, 8] = True

    # Place data bits in upward/downward 2-column zig-zags
    bit_idx = 0
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for r in rows:
            for dc in (0, -1):
                c = col + dc
                if not reserved[r, c]:
                    if bit_idx < len(stream_bits):
                        base[r, c] = stream_bits[bit_idx]
                        bit_idx += 1
        upward = not upward
        col -= 2

    def _apply_format(grid: np.ndarray, mask: int) -> None:
        fbits = _bch_format_bits(ecc, mask)
        # Around top-left
        coords_tl = [
            (8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8),
            (7, 8), (5, 8), (4, 8), (3, 8), (2, 8), (1, 8), (0, 8),
        ]
        for i, (r, c) in enumerate(coords_tl):
            grid[r, c] = (fbits >> (14 - i)) & 1
        # Split across bottom-left and top-right
        for i in range(7):
            grid[size - 1 - i, 8] = (fbits >> (14 - i)) & 1
        for i in range(7, 15):
            grid[8, size - 15 + i] = (fbits >> (14 - i)) & 1

    best_grid = None
    best_score = 10**9
    for mask in range(8):
        candidate = base.copy()
        for r in range(size):
            for c in range(size):
                if not reserved[r, c] and _mask_fn(mask, r, c):
                    candidate[r, c] ^= 1
        _apply_format(candidate, mask)
        sc = _penalty_score(candidate)
        if sc < best_score:
            best_score = sc
            best_grid = candidate

    return best_grid.astype(bool)


# ============================================================================
# Weathered Cinnabar Seal QR Stamp (朱砂印章二維碼 · 外框殘破與印泥肌理)
# ============================================================================

@lru_cache(maxsize=32)
def render_qr_seal_stamp(
    url: str = DEFAULT_STAMP_URL,
    size_px: int = 112,
    paper_rgb: Tuple[int, int, int] = (246, 239, 226),
) -> Image.Image:
    """Render a scannable red-ink cinnabar seal stamp with outer-frame breaking.

    Returns an RGBA PIL Image of shape (size_px, size_px).
    """
    size_px = max(64, int(size_px))
    matrix = encode_qr_matrix(url, ecc="L")
    n_mod = matrix.shape[0]

    # Supersample at 10px per module for authentic stone-carving & cinnabar texture
    scale = 10
    quiet_mods = 1.0 if n_mod >= 33 else 1.2      # Tight seal quiet zone like traditional 朱文印 while 100% scannable
    border_mods = 0.8 if n_mod >= 33 else 1.0     # Carved stone seal outer rim thickness
    pad_mods = 0.8                                # Clean paper margin outside rim so scanners see full quiet zone
    total_mods = n_mod + 2 * (quiet_mods + border_mods + pad_mods)
    canvas_sz = int(round(total_mods * scale))

    rng_seed = int(hashlib.sha256(url.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(rng_seed)

    outer_lo = int(round(pad_mods * scale))
    outer_hi = canvas_sz - outer_lo
    inner_lo = int(round((pad_mods + border_mods) * scale))
    inner_hi = canvas_sz - inner_lo
    qr_origin = int(round((pad_mods + border_mods + quiet_mods) * scale))

    # 1. Draw thick outer stone border with slightly rounded chiselled seal corners
    border_img = Image.new("L", (canvas_sz, canvas_sz), 0)
    bdraw = ImageDraw.Draw(border_img)
    bdraw.rounded_rectangle(
        [outer_lo, outer_lo, outer_hi - 1, outer_hi - 1],
        radius=int(scale * 1.1),
        fill=255,
    )
    bdraw.rounded_rectangle(
        [inner_lo, inner_lo, inner_hi - 1, inner_hi - 1],
        radius=int(scale * 0.45),
        fill=0,
    )
    border_mask = np.asarray(border_img, dtype=np.float32) / 255.0

    # Apply natural stone-carving breaks (外框殘破 / 擊邊崩缺) to the outer frame
    break_img = Image.new("L", (canvas_sz, canvas_sz), 255)
    kdraw = ImageDraw.Draw(break_img)
    border_w = inner_lo - outer_lo

    # Jagged stone-fracture breaks along the 4 edges (both full-through gaps and outer chips)
    rim_breaks = [
        # (side, fractional_pos, length_in_scales, depth_fraction)
        ("top", 0.18, 2.6, 1.15),
        ("top", 0.52, 1.8, 0.72),
        ("top", 0.79, 2.9, 1.15),
        ("right", 0.24, 2.8, 1.15),
        ("right", 0.61, 1.7, 0.68),
        ("right", 0.85, 2.5, 1.15),
        ("bottom", 0.16, 2.3, 0.78),
        ("bottom", 0.44, 1.9, 1.15),
        ("bottom", 0.72, 3.1, 1.15),
        ("left", 0.22, 2.1, 0.75),
        ("left", 0.54, 2.7, 1.15),
        ("left", 0.83, 1.9, 0.72),
    ]
    span = outer_hi - outer_lo
    for side, frac, len_sc, depth_frac in rim_breaks:
        half_len = int(len_sc * scale * 0.5)
        depth = int(border_w * depth_frac)
        center = outer_lo + int(span * frac)
        j = rng.integers(-4, 5, size=8)
        if side == "top":
            poly = [
                (center - half_len + j[0], outer_lo - 4),
                (center + half_len + j[1], outer_lo - 4),
                (center + int(half_len * 0.8) + j[2], outer_lo + int(depth * 0.6)),
                (center + int(half_len * 0.3) + j[3], outer_lo + depth),
                (center - int(half_len * 0.4) + j[4], outer_lo + int(depth * 0.9)),
                (center - int(half_len * 0.85) + j[5], outer_lo + int(depth * 0.5)),
            ]
        elif side == "bottom":
            poly = [
                (center - half_len + j[0], outer_hi + 4),
                (center + half_len + j[1], outer_hi + 4),
                (center + int(half_len * 0.8) + j[2], outer_hi - int(depth * 0.55)),
                (center + int(half_len * 0.25) + j[3], outer_hi - depth),
                (center - int(half_len * 0.45) + j[4], outer_hi - int(depth * 0.88)),
                (center - int(half_len * 0.85) + j[5], outer_hi - int(depth * 0.45)),
            ]
        elif side == "left":
            poly = [
                (outer_lo - 4, center - half_len + j[0]),
                (outer_lo - 4, center + half_len + j[1]),
                (outer_lo + int(depth * 0.55), center + int(half_len * 0.8) + j[2]),
                (outer_lo + depth, center + int(half_len * 0.3) + j[3]),
                (outer_lo + int(depth * 0.88), center - int(half_len * 0.4) + j[4]),
                (outer_lo + int(depth * 0.5), center - int(half_len * 0.85) + j[5]),
            ]
        else:
            poly = [
                (outer_hi + 4, center - half_len + j[0]),
                (outer_hi + 4, center + half_len + j[1]),
                (outer_hi - int(depth * 0.55), center + int(half_len * 0.8) + j[2]),
                (outer_hi - depth, center + int(half_len * 0.3) + j[3]),
                (outer_hi - int(depth * 0.88), center - int(half_len * 0.4) + j[4]),
                (outer_hi - int(depth * 0.5), center - int(half_len * 0.85) + j[5]),
            ]
        kdraw.polygon(poly, fill=0)

    # Angular stone corner fractures (印角殘破)
    for cx, cy, sx_dir, sy_dir in [
        (outer_lo, outer_lo, 1, 1),
        (outer_hi, outer_lo, -1, 1),
        (outer_lo, outer_hi, 1, -1),
        (outer_hi, outer_hi, -1, -1),
    ]:
        c_len1 = int(border_w * rng.uniform(0.9, 1.55))
        c_len2 = int(border_w * rng.uniform(0.85, 1.45))
        c_mid = int(border_w * rng.uniform(0.45, 0.85))
        poly = [
            (cx - sx_dir * 4, cy - sy_dir * 4),
            (cx + sx_dir * c_len1, cy - sy_dir * 2),
            (cx + sx_dir * c_mid, cy + sy_dir * c_mid),
            (cx - sx_dir * 2, cy + sy_dir * c_len2),
        ]
        kdraw.polygon(poly, fill=0)

    # Small angular chisel nicks along both outer and inner edges of the border frame
    for _ in range(44):
        side = rng.choice(["top", "bottom", "left", "right"])
        inner_edge = bool(rng.random() < 0.38)
        pos_c = int(rng.uniform(outer_lo + border_w, outer_hi - border_w))
        w_nick = int(rng.uniform(3, border_w * 0.75))
        d_nick = int(rng.uniform(3, border_w * 0.62))
        if side == "top":
            base_y = inner_lo if inner_edge else outer_lo
            d_y = -d_nick if inner_edge else d_nick
            poly = [(pos_c - w_nick, base_y), (pos_c + w_nick, base_y), (pos_c + int(rng.uniform(-3, 4)), base_y + d_y)]
        elif side == "bottom":
            base_y = inner_hi if inner_edge else outer_hi
            d_y = d_nick if inner_edge else -d_nick
            poly = [(pos_c - w_nick, base_y), (pos_c + w_nick, base_y), (pos_c + int(rng.uniform(-3, 4)), base_y + d_y)]
        elif side == "left":
            base_x = inner_lo if inner_edge else outer_lo
            d_x = -d_nick if inner_edge else d_nick
            poly = [(base_x, pos_c - w_nick), (base_x, pos_c + w_nick), (base_x + d_x, pos_c + int(rng.uniform(-3, 4)))]
        else:
            base_x = inner_hi if inner_edge else outer_hi
            d_x = d_nick if inner_edge else -d_nick
            poly = [(base_x, pos_c - w_nick), (base_x, pos_c + w_nick), (base_x + d_x, pos_c + int(rng.uniform(-3, 4)))]
        kdraw.polygon(poly, fill=0)

    break_mask = np.asarray(break_img, dtype=np.float32) / 255.0
    edge_noise = rng.normal(0.0, 1.0, (canvas_sz // 3, canvas_sz // 3)).astype(np.float32)
    edge_noise = cv2.GaussianBlur(edge_noise, (3, 3), 0.9)
    edge_noise = cv2.resize(edge_noise, (canvas_sz, canvas_sz), interpolation=cv2.INTER_CUBIC)
    border_mask = np.clip(border_mask * break_mask + 0.18 * edge_noise * (border_mask > 0.05), 0.0, 1.0)
    border_mask = (border_mask > 0.46).astype(np.float32)
    border_mask = cv2.GaussianBlur(border_mask, (3, 3), 0.55)

    # 2. Render QR modules aligned symmetrically on the scale grid
    qr_mask = np.zeros((canvas_sz, canvas_sz), dtype=np.float32)
    core_keep = np.zeros((canvas_sz, canvas_sz), dtype=bool)
    core_clear = np.zeros((canvas_sz, canvas_sz), dtype=bool)

    def _is_finder(r: int, c: int) -> bool:
        return (
            (r < 7 and c < 7)
            or (r < 7 and c >= n_mod - 7)
            or (r >= n_mod - 7 and c < 7)
        )

    for r in range(n_mod):
        for c in range(n_mod):
            x0 = qr_origin + c * scale
            x1 = qr_origin + (c + 1) * scale
            y0 = qr_origin + r * scale
            y1 = qr_origin + (r + 1) * scale
            if matrix[r, c]:
                qr_mask[y0:y1, x0:x1] = 1.0
                if n_mod >= 37:
                    m_base = 0
                elif _is_finder(r, c):
                    m_base = 1
                else:
                    m_base = 2
                # Connect core seamlessly across adjacent dark modules so strokes have no internal grid lines
                ml = 0 if (c > 0 and matrix[r, c - 1]) else m_base
                mr = 0 if (c + 1 < n_mod and matrix[r, c + 1]) else m_base
                mt = 0 if (r > 0 and matrix[r - 1, c]) else m_base
                mb = 0 if (r + 1 < n_mod and matrix[r + 1, c]) else m_base
                core_keep[y0 + mt : y1 - mb, x0 + ml : x1 - mr] = True
            else:
                if n_mod >= 37:
                    m_base = 0
                elif _is_finder(r, c):
                    m_base = 1
                else:
                    m_base = 2
                ml = 0 if (c > 0 and not matrix[r, c - 1]) else m_base
                mr = 0 if (c + 1 < n_mod and not matrix[r, c + 1]) else m_base
                mt = 0 if (r > 0 and not matrix[r - 1, c]) else m_base
                mb = 0 if (r + 1 < n_mod and not matrix[r + 1, c]) else m_base
                core_clear[y0 + mt : y1 - mb, x0 + ml : x1 - mr] = True

    # Apply subtle stone-carving organic edge texture to outer module boundaries
    qr_smooth = cv2.GaussianBlur(qr_mask, (5, 5), 0.85)
    mod_wobble = rng.normal(0.0, 1.0, (canvas_sz // 3, canvas_sz // 3)).astype(np.float32)
    mod_wobble = cv2.GaussianBlur(mod_wobble, (3, 3), 0.8)
    mod_wobble = cv2.resize(mod_wobble, (canvas_sz, canvas_sz), interpolation=cv2.INTER_CUBIC)
    qr_mask = np.clip(qr_smooth + 0.16 * mod_wobble * (qr_smooth > 0.05) * (qr_smooth < 0.95), 0.0, 1.0)
    qr_mask = (qr_mask > 0.48).astype(np.float32)
    qr_mask[core_keep] = 1.0
    qr_mask[core_clear] = 0.0

    ink_coverage = np.maximum(border_mask, qr_mask)

    # 3. Cinnabar Ink Paste Texture (朱砂印泥斑駁與飛白)
    speckle_hi = rng.random((canvas_sz // 2, canvas_sz // 2), dtype=np.float32)
    speckle_hi = cv2.resize(speckle_hi, (canvas_sz, canvas_sz), interpolation=cv2.INTER_LINEAR)
    mottle_lo = rng.normal(0.0, 1.0, (canvas_sz // 7, canvas_sz // 7)).astype(np.float32)
    mottle_lo = cv2.GaussianBlur(mottle_lo, (5, 5), 1.2)
    mottle_lo = cv2.resize(mottle_lo, (canvas_sz, canvas_sz), interpolation=cv2.INTER_CUBIC)

    void_field = speckle_hi + 0.28 * mottle_lo
    border_voids = (void_field > 0.78) & (border_mask > 0.2)
    qr_edge_voids = (void_field > 0.82) & (qr_mask > 0.2) & (~core_keep)
    ink_density = ink_coverage.copy()
    ink_density[border_voids] *= 0.10
    ink_density[qr_edge_voids] *= 0.20
    # Inside core_keep, add realistic cinnabar pigment mottling & tiny stone pores (0.72 - 1.0)
    core_variation = np.clip(0.92 + 0.08 * mottle_lo - 0.18 * (speckle_hi > 0.91), 0.72, 1.0)
    ink_density = np.where(core_keep, ink_density * core_variation, ink_density)

    # Colorize cinnabar ink: rich antique vermilion with subtle darker pooling at true stroke edges
    edge_ring = np.clip(cv2.GaussianBlur(ink_coverage, (5, 5), 1.1) - ink_coverage * 0.78, 0.0, 1.0)
    cinnabar_r = np.clip(182.0 + 16.0 * mottle_lo - 20.0 * edge_ring, 148.0, 208.0)
    cinnabar_g = np.clip(36.0 + 8.0 * mottle_lo - 10.0 * edge_ring, 18.0, 52.0)
    cinnabar_b = np.clip(26.0 + 6.0 * mottle_lo - 8.0 * edge_ring, 12.0, 38.0)

    pr, pg, pb = paper_rgb
    paper_grain = rng.normal(0.0, 1.6, (canvas_sz // 2, canvas_sz // 2)).astype(np.float32)
    paper_grain = cv2.resize(paper_grain, (canvas_sz, canvas_sz), interpolation=cv2.INTER_LINEAR)
    bg_r = np.clip(pr + paper_grain, 0, 255)
    bg_g = np.clip(pg + paper_grain * 0.9, 0, 255)
    bg_b = np.clip(pb + paper_grain * 0.8, 0, 255)

    out_r = bg_r * (1.0 - ink_density) + cinnabar_r * ink_density
    out_g = bg_g * (1.0 - ink_density) + cinnabar_g * ink_density
    out_b = bg_b * (1.0 - ink_density) + cinnabar_b * ink_density
    # Alpha is the cinnabar ink density itself so when stamped onto Xuan paper, only red ink is deposited!
    out_a = np.clip(ink_density * 255.0, 0.0, 255.0)

    rgba = np.stack([out_r, out_g, out_b, out_a], axis=-1).astype(np.uint8)
    stamp = Image.fromarray(rgba, mode="RGBA")
    if size_px != canvas_sz:
        stamp = stamp.resize((size_px, size_px), Image.Resampling.BOX)
    return stamp


# ============================================================================
# Evenly Distributed Ruling Grid & Line-Aligned Stamp Placement
# ============================================================================

def compute_paper_grid(
    width: int,
    height: int,
    direction: str = "vertical-rl",
    col_centers: Sequence[float] = (),
    row_centers: Sequence[float] = (),
    cell_size: float = 0.0,
    gap: float = 0.18,
) -> Dict[str, Any]:
    """Compute outer/inner frames and evenly distributed ruling lines across the full page.

    Every lane between inner_box edges has the exact same width (lane_width),
    and text columns/rows stay centered in their ruled lanes.
    """
    short_side = min(width, height)
    base_margin = max(10, int(round(short_side * 0.048)))
    inset = max(3, int(round(short_side * 0.0065)))

    inner_left = float(base_margin + inset)
    inner_top = float(base_margin + inset)
    inner_right = float(width - 1 - base_margin - inset)
    inner_bottom = float(height - 1 - base_margin - inset)

    min_margin = float(max(8, int(round(short_side * 0.022))))
    max_margin = float(max(base_margin + inset + 4, int(round(short_side * 0.155))))

    if direction == "vertical-rl":
        default_span = max(32.0, inner_right - inner_left)
        n_text = len(col_centers)
        text_pitch = 0.0
        if n_text >= 2:
            text_pitch = (col_centers[-1] - col_centers[0]) / float(n_text - 1)
        elif cell_size > 0:
            text_pitch = cell_size * (1.0 + gap)

        center_x = 0.5 * (col_centers[0] + col_centers[-1]) if n_text >= 1 else (width - 1) * 0.5
        chosen_n: Optional[int] = None
        chosen_pitch: Optional[float] = None

        if text_pitch > 12.0 and text_pitch <= default_span * 0.48:
            max_span = width - 2.0 * min_margin
            min_span = width - 2.0 * max_margin
            parity = n_text % 2 if n_text >= 1 else 0
            best_diff = 1e9
            for cand_n in range(max(3, n_text), 48):
                if n_text >= 1 and (cand_n % 2) != parity:
                    continue
                cand_span = cand_n * text_pitch
                if min_span <= cand_span <= max_span:
                    diff = abs(cand_span - default_span)
                    if diff < best_diff:
                        best_diff = diff
                        chosen_n = cand_n
                        chosen_pitch = text_pitch

        if chosen_n is not None and chosen_pitch is not None:
            grid_span = chosen_n * chosen_pitch
            inner_left = center_x - 0.5 * grid_span
            inner_right = center_x + 0.5 * grid_span
            n_lanes = chosen_n
            lane_width = chosen_pitch
        else:
            # Fallback for single huge character or empty canvas: divide inner_box into equal lanes
            if n_text == 1:
                n_lanes = 5 if width <= height else 7
            elif n_text >= 2:
                n_lanes = max(4, n_text * 2 if n_text * 2 <= 10 else n_text)
            else:
                n_lanes = 6 if width <= height else 8
            lane_width = default_span / float(n_lanes)

        dividers = [inner_left + k * lane_width for k in range(1, n_lanes)]
        lane_centers = [inner_left + (k + 0.5) * lane_width for k in range(n_lanes)]
    else:
        default_span = max(32.0, inner_bottom - inner_top)
        n_text = len(row_centers)
        text_pitch = 0.0
        if n_text >= 2:
            text_pitch = (row_centers[-1] - row_centers[0]) / float(n_text - 1)
        elif cell_size > 0:
            text_pitch = cell_size * (1.0 + gap)

        center_y = 0.5 * (row_centers[0] + row_centers[-1]) if n_text >= 1 else (height - 1) * 0.5
        chosen_n = None
        chosen_pitch = None

        if text_pitch > 12.0 and text_pitch <= default_span * 0.48:
            max_span = height - 2.0 * min_margin
            min_span = height - 2.0 * max_margin
            parity = n_text % 2 if n_text >= 1 else 0
            best_diff = 1e9
            for cand_n in range(max(3, n_text), 48):
                if n_text >= 1 and (cand_n % 2) != parity:
                    continue
                cand_span = cand_n * text_pitch
                if min_span <= cand_span <= max_span:
                    diff = abs(cand_span - default_span)
                    if diff < best_diff:
                        best_diff = diff
                        chosen_n = cand_n
                        chosen_pitch = text_pitch

        if chosen_n is not None and chosen_pitch is not None:
            grid_span = chosen_n * chosen_pitch
            inner_top = center_y - 0.5 * grid_span
            inner_bottom = center_y + 0.5 * grid_span
            n_lanes = chosen_n
            lane_width = chosen_pitch
        else:
            if n_text == 1:
                n_lanes = 5 if height <= width else 7
            elif n_text >= 2:
                n_lanes = max(4, n_text * 2 if n_text * 2 <= 10 else n_text)
            else:
                n_lanes = 6 if height <= width else 8
            lane_width = default_span / float(n_lanes)

        dividers = [inner_top + k * lane_width for k in range(1, n_lanes)]
        lane_centers = [inner_top + (k + 0.5) * lane_width for k in range(n_lanes)]

    i_box = [
        int(round(inner_left)),
        int(round(inner_top)),
        int(round(inner_right)),
        int(round(inner_bottom)),
    ]
    o_box = [
        max(2, i_box[0] - inset),
        max(2, i_box[1] - inset),
        min(width - 3, i_box[2] + inset),
        min(height - 3, i_box[3] + inset),
    ]
    return {
        "outer_box": o_box,
        "inner_box": i_box,
        "dividers": tuple(round(d, 2) for d in dividers),
        "lane_centers": tuple(round(c, 2) for c in lane_centers),
        "lane_width": round(float(lane_width), 2),
        "n_lanes": len(lane_centers),
    }


def _nearest_lane_index(coord: float, lane_centers: Sequence[float]) -> int:
    if not lane_centers:
        return 0
    return int(min(range(len(lane_centers)), key=lambda i: abs(lane_centers[i] - coord)))


def compute_stamp_placement(
    width: int,
    height: int,
    direction: str,
    grid: Dict[str, Any],
    schedule: Sequence[Dict[str, Any]],
    stamp_position: str = "after-text",
    stamp_col: Optional[int] = None,
    stamp_row: Optional[float] = None,
    stamp_url: Optional[str] = None,
) -> Tuple[int, int, int]:
    """Compute (sx, sy, stamp_sz) aligned to the paper's ruled lines.

    The seal stamp is sized to be smaller, delicate, and fit comfortably in between
    the ruled lines with clearance on both sides so it never crosses the grid boundaries.
    """
    short_side = min(width, height)
    lane_centers = grid["lane_centers"]
    lane_width = grid["lane_width"]
    inner_left, inner_top, inner_right, inner_bottom = grid["inner_box"]
    n_lanes = max(1, len(lane_centers))

    # Dense share URLs (41x41 matrix) require ~92px; default URLs (29x29 matrix) scan at 80-84px
    is_dense_url = bool(stamp_url and len(stamp_url) > 80)
    ideal_sz = 92 if is_dense_url else 84

    if lane_width > 0:
        # Keep inside lane width with breathing room so it never touches or crosses the lines
        max_fit = int(round(lane_width * 0.78))
        target_sz = min(ideal_sz, max_fit)
        stamp_sz = max(72, min(ideal_sz, target_sz)) if max_fit >= 72 else max(64, max_fit)
    else:
        stamp_sz = max(72, min(ideal_sz, int(round(short_side * 0.09))))

    half = stamp_sz * 0.5
    pad_along = max(8.0, stamp_sz * 0.10)

    def _clamp_box(cx: float, cy: float) -> Tuple[int, int]:
        sx = int(round(max(4.0, min(width - stamp_sz - 4.0, cx - half))))
        sy = int(round(max(4.0, min(height - stamp_sz - 4.0, cy - half))))
        return sx, sy

    if direction == "vertical-rl":
        min_cy = inner_top + pad_along + half
        max_cy = inner_bottom - pad_along - half
        if max_cy < min_cy:
            min_cy = max_cy = height * 0.5

        if stamp_position == "custom" and (stamp_col is not None or stamp_row is not None):
            idx = max(0, min(n_lanes - 1, int(stamp_col) if stamp_col is not None else 0))
            frac = max(0.0, min(1.0, float(stamp_row) if stamp_row is not None else 0.85))
            cx = lane_centers[idx]
            cy = min_cy + frac * (max_cy - min_cy)
            sx, sy = _clamp_box(cx, cy)
            return sx, sy, stamp_sz

        if not schedule or stamp_position == "corner":
            cx = lane_centers[0]
            cy = max_cy
            sx, sy = _clamp_box(cx, cy)
            return sx, sy, stamp_sz

        first_e = schedule[0]
        last_e = schedule[-1]
        first_cx = float(first_e["x"]) + float(first_e["size"]) * 0.5
        first_top = float(first_e["y"])
        last_cx = float(last_e["x"]) + float(last_e["size"]) * 0.5
        last_bot = float(last_e["y"]) + float(last_e["size"])
        char_gap = max(10.0, float(last_e["size"]) * 0.16)

        first_lane = _nearest_lane_index(first_cx, lane_centers)
        last_lane = _nearest_lane_index(last_cx, lane_centers)

        if stamp_position == "before-text":
            # Above first character on first line if room; else top of preceding right-hand lane
            if first_top - char_gap - stamp_sz >= inner_top + 4:
                cx = lane_centers[first_lane]
                cy = first_top - char_gap - half
            elif first_lane + 1 < n_lanes:
                cx = lane_centers[first_lane + 1]
                cy = max(min_cy, first_top + half)
            else:
                cx = lane_centers[first_lane]
                cy = min_cy
        elif stamp_position == "next-line":
            next_lane = max(0, last_lane - 1)
            cx = lane_centers[next_lane]
            cy = min(max_cy, max(min_cy, last_bot))
        else:
            # "after-text" (default): right after the last character on the last line,
            # or on the next ruled line if the last line reaches the bottom of the frame.
            if last_bot + char_gap + stamp_sz <= inner_bottom - 2:
                cx = lane_centers[last_lane]
                cy = last_bot + char_gap + half
            elif last_lane > 0:
                cx = lane_centers[last_lane - 1]
                cy = max_cy
            else:
                cx = lane_centers[0]
                cy = max_cy

        sx, sy = _clamp_box(cx, cy)
        return sx, sy, stamp_sz

    else:
        # horizontal-lr: lines are horizontal rows from top to bottom
        min_cx = inner_left + pad_along + half
        max_cx = inner_right - pad_along - half
        if max_cx < min_cx:
            min_cx = max_cx = width * 0.5

        if stamp_position == "custom" and (stamp_col is not None or stamp_row is not None):
            idx = max(0, min(n_lanes - 1, int(stamp_col) if stamp_col is not None else n_lanes - 1))
            frac = max(0.0, min(1.0, float(stamp_row) if stamp_row is not None else 0.85))
            cy = lane_centers[idx]
            cx = min_cx + frac * (max_cx - min_cx)
            sx, sy = _clamp_box(cx, cy)
            return sx, sy, stamp_sz

        if not schedule or stamp_position == "corner":
            cy = lane_centers[-1]
            cx = max_cx
            sx, sy = _clamp_box(cx, cy)
            return sx, sy, stamp_sz

        first_e = schedule[0]
        last_e = schedule[-1]
        first_cy = float(first_e["y"]) + float(first_e["size"]) * 0.5
        first_left = float(first_e["x"])
        last_cy = float(last_e["y"]) + float(last_e["size"]) * 0.5
        last_right = float(last_e["x"]) + float(last_e["size"])
        char_gap = max(10.0, float(last_e["size"]) * 0.16)

        first_lane = _nearest_lane_index(first_cy, lane_centers)
        last_lane = _nearest_lane_index(last_cy, lane_centers)

        if stamp_position == "before-text":
            if first_left - char_gap - stamp_sz >= inner_left + 4:
                cy = lane_centers[first_lane]
                cx = first_left - char_gap - half
            elif first_lane > 0:
                cy = lane_centers[first_lane - 1]
                cx = max(min_cx, first_left + half)
            else:
                cy = lane_centers[first_lane]
                cx = min_cx
        elif stamp_position == "next-line":
            next_lane = min(n_lanes - 1, last_lane + 1)
            cy = lane_centers[next_lane]
            cx = min(max_cx, max(min_cx, last_right))
        else:
            # "after-text" (default): right after the last character on the last row,
            # or on the next ruled row if the last row reaches the right margin.
            if last_right + char_gap + stamp_sz <= inner_right - 2:
                cy = lane_centers[last_lane]
                cx = last_right + char_gap + half
            elif last_lane + 1 < n_lanes:
                cy = lane_centers[last_lane + 1]
                cx = max_cx
            else:
                cy = lane_centers[-1]
                cx = max_cx

        sx, sy = _clamp_box(cx, cy)
        return sx, sy, stamp_sz


def get_stamp_preview_meta(params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Compute stamp placement and grid metrics for editor handle alignment."""
    enabled = bool(params.get("stamp_enabled", True))
    width = int(params.get("width", 720))
    height = int(params.get("height", 960))
    direction = str(params.get("direction", "vertical-rl"))
    stamp_position = str(params.get("stamp_position", "after-text"))
    stamp_col = params.get("stamp_col")
    stamp_row = params.get("stamp_row")
    gap = float(params.get("spacing", 0.18))
    font_size = float(params.get("font_size", 68)) if params.get("font_size") is not None else None
    fit = bool(params.get("fit", True))
    zigzag = bool(params.get("zigzag", False))
    lines = params.get("lines")
    if not lines and params.get("text"):
        from .text.input import parse_text
        lines = parse_text(params["text"], punctuation=params.get("punctuation", "omit"))["lines"]
    if not lines:
        lines = [["永"]]

    from .text.layout import layout_text
    plan = layout_text(
        lines,
        width=width,
        height=height,
        direction=direction,
        font_size=font_size,
        gap=gap,
        fit=fit,
        zigzag=zigzag,
    )
    schedule = plan.get("placements", [])

    if schedule and "column" in schedule[0] and "row" in schedule[0]:
        cols_by_idx: Dict[int, List[float]] = {}
        rows_by_idx: Dict[int, List[float]] = {}
        for e in schedule:
            cols_by_idx.setdefault(int(e["column"]), []).append(float(e["x"]) + float(e["size"]) * 0.5)
            rows_by_idx.setdefault(int(e["row"]), []).append(float(e["y"]) + float(e["size"]) * 0.5)
        col_centers = tuple(sorted(round(sum(v) / len(v), 1) for v in cols_by_idx.values()))
        row_centers = tuple(sorted(round(sum(v) / len(v), 1) for v in rows_by_idx.values()))
    else:
        col_centers = tuple(sorted({round(float(e["x"]) + float(e["size"]) * 0.5, 1) for e in schedule}))
        row_centers = tuple(sorted({round(float(e["y"]) + float(e["size"]) * 0.5, 1) for e in schedule}))
    cell_size = round(float(schedule[0]["size"]), 2) if schedule else 0.0

    grid = compute_paper_grid(
        width=width,
        height=height,
        direction=direction,
        col_centers=col_centers,
        row_centers=row_centers,
        cell_size=cell_size,
        gap=gap,
    )

    stamp_url = params.get("stamp_url") or get_default_stamp_url()
    sx, sy, sz = compute_stamp_placement(
        width=width,
        height=height,
        direction=direction,
        grid=grid,
        schedule=schedule,
        stamp_position=stamp_position,
        stamp_col=int(stamp_col) if stamp_col is not None else None,
        stamp_row=float(stamp_row) if stamp_row is not None else None,
        stamp_url=stamp_url,
    )

    return {
        "sx": sx,
        "sy": sy,
        "sz": sz,
        "cw": width,
        "ch": height,
        "inner_box": [int(x) for x in grid["inner_box"]],
        "lane_width": float(grid["lane_width"]),
        "lane_centers": [float(c) for c in grid["lane_centers"]],
        "enabled": enabled,
        "direction": direction,
    }


# ============================================================================
# Traditional Xuan Stationery Paper (仿古宣紙信箋 · 多款背景與印章對齊)
# ============================================================================

@lru_cache(maxsize=128)
def _cached_xuan_base(
    width: int,
    height: int,
    paper_color: Tuple[int, int, int],
    paper_style: str,
    direction: str,
    col_centers_tuple: Tuple[float, ...],
    row_centers_tuple: Tuple[float, ...],
    cell_size: float,
    gap: float,
    stamp_enabled: bool,
    stamp_position: str,
    stamp_col: Optional[int],
    stamp_row: Optional[float],
    stamp_url: str,
    first_box: Optional[Tuple[float, float, float]],
    last_box: Optional[Tuple[float, float, float]],
) -> Image.Image:
    """Render and cache the stationery background (paper texture + evenly distributed rules + QR seal stamp)."""
    r0, g0, b0 = paper_color
    is_dark = (r0 + g0 + b0) / 3.0 < 85.0
    short_side = min(width, height)

    if paper_style == "plain" and (not stamp_enabled or not stamp_url or is_dark or short_side < 320):
        return Image.new("RGB", (width, height), paper_color)

    rng = np.random.default_rng(width * 10007 + height * 31 + r0 * 7 + len(paper_style) * 13)

    if paper_style == "plain":
        canvas_arr = np.full((height, width, 3), paper_color, dtype=np.uint8)
    else:
        # 1. Paper base with Xuan paper cloud mottling, laid lines, and warm antique edge vignette
        yy = np.linspace(-1.0, 1.0, height, dtype=np.float32)[:, None]
        xx = np.linspace(-1.0, 1.0, width, dtype=np.float32)[None, :]
        r2 = np.clip(xx * xx + yy * yy, 0.0, 2.0)
        vignette = np.clip((r2 - 0.35) / 1.35, 0.0, 1.0) ** 1.5

        low_h = max(8, height // 20)
        low_w = max(8, width // 20)
        cloud = rng.normal(0.0, 1.0, (low_h, low_w)).astype(np.float32)
        cloud = cv2.GaussianBlur(cloud, (5, 5), 1.2)
        cloud = cv2.resize(cloud, (width, height), interpolation=cv2.INTER_CUBIC)

        mid_h = max(16, height // 4)
        mid_w = max(16, width // 4)
        grain = rng.normal(0.0, 1.0, (mid_h, mid_w)).astype(np.float32)
        grain = cv2.GaussianBlur(grain, (5, 5), 0.9)
        grain = cv2.resize(grain, (width, height), interpolation=cv2.INTER_LINEAR)

        # Subtle horizontal bamboo-screen laid lines (簾紋) characteristic of handmade Xuan paper
        laid = np.sin(np.arange(height, dtype=np.float32)[:, None] * (2.0 * math.pi / 8.0)) * 0.25

        if is_dark:
            delta = 0.85 * cloud + 0.35 * grain
            base_r = np.clip(r0 + delta, 0, 255)
            base_g = np.clip(g0 + delta, 0, 255)
            base_b = np.clip(b0 + delta, 0, 255)
        else:
            # Warm antique Xuan paper: unified luminance delta preserves 4:2:0 yuv420p chroma fidelity
            vig_scale = 5.0 if short_side >= 240 else 1.5
            cloud_scale = 1.6 if short_side >= 240 else 0.7
            grain_scale = 0.55 if short_side >= 240 else 0.2
            delta = np.round(cloud_scale * cloud + grain_scale * grain + laid - vig_scale * vignette)
            delta = np.where(delta == -3.0, -2.0, delta)
            base_r = np.clip(r0 + delta, 145, 255)
            base_g = np.clip(g0 + delta, 140, 255)
            base_b = np.clip(b0 + delta, 130, 255)

        canvas_arr = np.stack([base_r, base_g, base_b], axis=-1).astype(np.uint8)
        canvas_arr[0, 0] = paper_color

    page = Image.fromarray(canvas_arr, mode="RGB").convert("RGBA")
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay)

    # 2. Delicate Xuan paper plant fibers (宣紙檀皮纖維) and gold flecks (灑金) on light paper
    if not is_dark and short_side >= 240 and paper_style != "plain":
        n_fibers = max(16, min(110, (width * height) // 14000))
        for _ in range(n_fibers):
            fx = float(rng.uniform(short_side * 0.04, width - short_side * 0.04))
            fy = float(rng.uniform(short_side * 0.04, height - short_side * 0.04))
            angle = float(rng.uniform(0, math.pi * 2))
            flen = float(rng.uniform(7.0, 20.0))
            mx = fx + math.cos(angle) * flen * 0.5 + float(rng.uniform(-2.5, 2.5))
            my = fy + math.sin(angle) * flen * 0.5 + float(rng.uniform(-2.5, 2.5))
            ex = fx + math.cos(angle) * flen
            ey = fy + math.sin(angle) * flen
            odraw.line(
                [(fx, fy), (mx, my), (ex, ey)],
                fill=(204, 184, 158, int(rng.integers(22, 44))),
                width=1,
            )

        if paper_style == "gold":
            # Shimmering gold leaf flecks (泥金灑金箋) — keep R >= 210 so it never triggers ink masks
            n_flecks = max(28, min(180, (width * height) // 8500))
            for _ in range(n_flecks):
                gx = float(rng.uniform(short_side * 0.03, width - short_side * 0.03))
                gy = float(rng.uniform(short_side * 0.03, height - short_side * 0.03))
                rad = float(rng.uniform(1.5, 4.8))
                n_pts = int(rng.integers(4, 7))
                pts = []
                base_ang = float(rng.uniform(0, math.pi * 2))
                for k in range(n_pts):
                    ang = base_ang + (2.0 * math.pi * k) / n_pts + float(rng.uniform(-0.3, 0.3))
                    rr = rad * float(rng.uniform(0.55, 1.25))
                    pts.append((gx + math.cos(ang) * rr, gy + math.sin(ang) * rr))
                alpha = int(rng.integers(75, 155))
                odraw.polygon(pts, fill=(226, 184, 92, alpha))

    # 3. Evenly Distributed Border Frame & Column/Row Dividers (朱絲欄 / 烏絲欄)
    grid = compute_paper_grid(
        width,
        height,
        direction=direction,
        col_centers=col_centers_tuple,
        row_centers=row_centers_tuple,
        cell_size=cell_size,
        gap=gap,
    )
    outer_box = grid["outer_box"]
    inner_box = grid["inner_box"]
    dividers = grid["dividers"]
    outer_w = max(2, int(round(short_side / 380.0))) if short_side >= 320 else 1

    if paper_style not in ("unruled", "plain"):
        if is_dark:
            outer_stroke = (165, 58, 46, 95 if short_side >= 240 else 48)
            inner_stroke = (165, 58, 46, 60 if short_side >= 240 else 30)
            rule_stroke = (165, 58, 46, 38 if short_side >= 240 else 20)
        elif paper_style == "wusi":
            # Scholar grey-ink ruling (烏絲欄): R >= 150 so blended R stays >= 195 (well above 138 ink threshold)
            outer_stroke = (152, 148, 142, 165 if short_side >= 240 else 58)
            inner_stroke = (156, 152, 146, 125 if short_side >= 240 else 40)
            rule_stroke = (162, 158, 152, 85 if short_side >= 240 else 28)
        else:
            # Cinnabar red ruling (朱絲欄): R >= 188
            outer_stroke = (188, 96, 78, 195 if short_side >= 240 else 68)
            inner_stroke = (196, 114, 96, 145 if short_side >= 240 else 44)
            rule_stroke = (198, 128, 112, 88 if short_side >= 240 else 32)

        if inner_box[2] - inner_box[0] > 24 and inner_box[3] - inner_box[1] > 24:
            odraw.rectangle(outer_box, outline=outer_stroke, width=outer_w)
            odraw.rectangle(inner_box, outline=inner_stroke, width=1)

            if direction == "vertical-rl":
                for dx in dividers:
                    ix = int(round(dx))
                    if inner_box[0] + 4 < ix < inner_box[2] - 4:
                        odraw.line(
                            [(ix, inner_box[1] + 1), (ix, inner_box[3] - 1)],
                            fill=rule_stroke,
                            width=1,
                        )
            else:
                for dy in dividers:
                    iy = int(round(dy))
                    if inner_box[1] + 4 < iy < inner_box[3] - 4:
                        odraw.line(
                            [(inner_box[0] + 1, iy), (inner_box[2] - 1, iy)],
                            fill=rule_stroke,
                            width=1,
                        )

    # 4. Line-Aligned Cinnabar QR Seal Stamp (朱砂印章二維碼)
    has_stamp = bool(stamp_enabled and stamp_url and not is_dark and short_side >= 320)
    if has_stamp:
        synthetic_schedule: List[Dict[str, Any]] = []
        if first_box is not None:
            synthetic_schedule.append({"x": first_box[0], "y": first_box[1], "size": first_box[2]})
        if last_box is not None and last_box != first_box:
            synthetic_schedule.append({"x": last_box[0], "y": last_box[1], "size": last_box[2]})

        sx, sy, stamp_sz = compute_stamp_placement(
            width,
            height,
            direction=direction,
            grid=grid,
            schedule=synthetic_schedule,
            stamp_position=stamp_position,
            stamp_col=stamp_col,
            stamp_row=stamp_row,
            stamp_url=stamp_url,
        )

        # Clear the ruling lines underneath the seal body so the border lines stop at the stamp edge
        clear_pad = max(2, int(round(stamp_sz * 0.03)))
        odraw.rectangle(
            [sx + clear_pad, sy + clear_pad, sx + stamp_sz - clear_pad, sy + stamp_sz - clear_pad],
            fill=(0, 0, 0, 0),
        )

    page = Image.alpha_composite(page, overlay)

    if has_stamp:
        stamp_paper = (
            max(226, min(246, int(round(r0 - 8)))),
            max(216, min(238, int(round(g0 - 11)))),
            max(200, min(226, int(round(b0 - 16)))),
        )
        stamp = render_qr_seal_stamp(stamp_url, size_px=stamp_sz, paper_rgb=stamp_paper)
        page.paste(stamp, (sx, sy), stamp)

    result = page.convert("RGB")
    result.putpixel((0, 0), paper_color)
    return result


def render_writing_paper(
    width: int,
    height: int,
    appearance: Any,
    plan: Optional[Any] = None,
    include_stamp: Optional[bool] = None,
) -> Image.Image:
    """Create the writing paper background for a scene or preview frame."""
    paper_style = getattr(appearance, "paper_style", "xuan")
    stamp_enabled = bool(getattr(appearance, "stamp_enabled", True))
    if include_stamp is not None:
        stamp_enabled = stamp_enabled and bool(include_stamp)
    stamp_position = str(getattr(appearance, "stamp_position", "after-text"))
    stamp_col = getattr(appearance, "stamp_col", None)
    stamp_row = getattr(appearance, "stamp_row", None)

    schedule: List[Dict[str, Any]] = []
    direction = "vertical-rl"
    if isinstance(plan, dict):
        schedule = plan.get("schedule", [])
        direction = plan.get("direction", "vertical-rl")
    elif plan is not None:
        schedule = getattr(plan, "schedule", [])
        direction = getattr(plan, "direction", "vertical-rl")

    # Group by logical column/row index if present, otherwise by rounded coordinate
    if schedule and "column" in schedule[0] and "row" in schedule[0]:
        cols_by_idx: Dict[int, List[float]] = {}
        rows_by_idx: Dict[int, List[float]] = {}
        for e in schedule:
            cols_by_idx.setdefault(int(e["column"]), []).append(float(e["x"]) + float(e["size"]) * 0.5)
            rows_by_idx.setdefault(int(e["row"]), []).append(float(e["y"]) + float(e["size"]) * 0.5)
        col_centers = tuple(sorted(round(sum(v) / len(v), 1) for v in cols_by_idx.values()))
        row_centers = tuple(sorted(round(sum(v) / len(v), 1) for v in rows_by_idx.values()))
    else:
        col_centers = tuple(
            sorted({round(float(e["x"]) + float(e["size"]) * 0.5, 1) for e in schedule})
        )
        row_centers = tuple(
            sorted({round(float(e["y"]) + float(e["size"]) * 0.5, 1) for e in schedule})
        )
    cell_size = round(float(schedule[0]["size"]), 2) if schedule else 0.0

    gap = 0.18
    if len(col_centers) > 1 and cell_size > 0:
        gap = round((col_centers[1] - col_centers[0]) / cell_size - 1.0, 3)
    elif len(row_centers) > 1 and cell_size > 0:
        gap = round((row_centers[1] - row_centers[0]) / cell_size - 1.0, 3)

    stamp_url = getattr(appearance, "stamp_url", None)
    if stamp_url is None:
        stamp_url = get_default_stamp_url()

    first_box: Optional[Tuple[float, float, float]] = None
    last_box: Optional[Tuple[float, float, float]] = None
    if schedule:
        f_e = schedule[0]
        l_e = schedule[-1]
        first_box = (round(float(f_e["x"]), 1), round(float(f_e["y"]), 1), round(float(f_e["size"]), 1))
        last_box = (round(float(l_e["x"]), 1), round(float(l_e["y"]), 1), round(float(l_e["size"]), 1))

    base = _cached_xuan_base(
        int(width),
        int(height),
        tuple(appearance.paper_color),
        paper_style,
        direction,
        col_centers,
        row_centers,
        cell_size,
        gap,
        stamp_enabled,
        stamp_position,
        int(stamp_col) if stamp_col is not None else None,
        round(float(stamp_row), 4) if stamp_row is not None else None,
        stamp_url,
        first_box,
        last_box,
    )
    return base.copy()

