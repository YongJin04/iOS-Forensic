
# Original code retained below
import sys
import struct
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Dict

# ────────────────────────────────────────────────
# 기준·범위
# ────────────────────────────────────────────────
WINDOWS_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)
APPLE_EPOCH   = datetime(2001, 1, 1, tzinfo=timezone.utc)

_MIN_DT = datetime(2020, 1, 1, tzinfo=timezone.utc)
_MAX_DT = datetime(2035, 12, 31, tzinfo=timezone.utc)
_NOW    = datetime.now(timezone.utc)

# 잘못 저장된 값 ↔ 실제 시각 간 오프셋
OFFSET_DELTA = timedelta(days=1597, hours=11, minutes=24,
                         seconds=56, microseconds=909_000)

# ────────────────────────────────────────────────
# 보정 유틸리티
# ────────────────────────────────────────────────
def _valid(dt: datetime) -> bool:
    return _MIN_DT <= dt <= _MAX_DT

def _normalize_decode(dt: datetime) -> Optional[datetime]:
    """저장값 dt → 실제 시각으로 보정"""
    while dt > _NOW and (dt - OFFSET_DELTA) >= _MIN_DT:
        dt -= OFFSET_DELTA
    return dt if _valid(dt) else None

def _normalize_encode(dt: datetime) -> datetime:
    """실제 시각 dt → 저장 포맷용(미래) 시각으로 보정"""
    while dt + OFFSET_DELTA <= _NOW:
        dt += OFFSET_DELTA
    return dt

# ────────────────────────────────────────────────
# 숫자 ↔ datetime 변환기 (decode 전용)
# ────────────────────────────────────────────────
def from_chrome_us(val: int) -> Optional[datetime]:
    if 8e15 <= val <= 1.5e16:
        return WINDOWS_EPOCH + timedelta(microseconds=val)
    return None

def from_unix_us(val: int) -> Optional[datetime]:
    if 6.3e14 <= val <= 2.0e15:
        return datetime.fromtimestamp(val / 1e6, tz=timezone.utc)
    return None

def from_unix_ms(val: int) -> Optional[datetime]:
    if 6.3e11 <= val <= 2.0e12:
        return datetime.fromtimestamp(val / 1e3, tz=timezone.utc)
    return None

def from_unix_s(val: int) -> Optional[datetime]:
    if 1_577_836_800 <= val <= 2_135_011_200:
        return datetime.fromtimestamp(val, tz=timezone.utc)
    return None

def from_apple_us(val: int) -> Optional[datetime]:
    if 6.3e14 <= val <= 1.1e15:
        return APPLE_EPOCH + timedelta(microseconds=val)
    return None

def from_apple_ms(val: int) -> Optional[datetime]:
    if 6.3e11 <= val <= 1.1e12:
        return APPLE_EPOCH + timedelta(milliseconds=val)
    return None

def from_apple_s(val: int) -> Optional[datetime]:
    if 630_720_000 <= val <= 1_105_977_600:
        return APPLE_EPOCH + timedelta(seconds=val)
    return None

# 인코딩용(실제 시각 → 저장 숫자)
def to_chrome_us(dt: datetime) -> int:
    return int((_normalize_encode(dt) - WINDOWS_EPOCH).total_seconds() * 1e6)

def to_unix_us(dt: datetime) -> int:
    return int(_normalize_encode(dt).timestamp() * 1e6)

def to_unix_ms(dt: datetime) -> int:
    return int(_normalize_encode(dt).timestamp() * 1e3)

def to_unix_s(dt: datetime) -> int:
    return int(_normalize_encode(dt).timestamp())

def to_apple_us(dt: datetime) -> int:
    return int((_normalize_encode(dt) - APPLE_EPOCH).total_seconds() * 1e6)

def to_apple_ms(dt: datetime) -> int:
    return int((_normalize_encode(dt) - APPLE_EPOCH).total_seconds() * 1e3)

def to_apple_s(dt: datetime) -> int:
    return int((_normalize_encode(dt) - APPLE_EPOCH).total_seconds())

# ────────────────────────────────────────────────
# URL 주변 숫자 스캔 → 시각 추정
# ────────────────────────────────────────────────
_CONV8 = (
    from_chrome_us,
    from_unix_us,
    from_unix_ms,
    from_apple_us,
    from_apple_ms,
)
_CONV4 = (
    from_unix_s,
    from_apple_s,
)

def guess_timestamp(blob: bytes, url_ofs: int) -> Optional[str]:
    cand: List[datetime] = []

    # 8-byte 스캔(±64B)
    for rel in range(-64, 33, 4):
        pos = url_ofs + rel
        if 0 <= pos <= len(blob) - 8:
            raw = struct.unpack_from('<Q', blob, pos)[0]
            for conv in _CONV8:
                dt_raw = conv(raw)
                if dt_raw and (dt := _normalize_decode(dt_raw)):
                    cand.append(dt)

    # 4-byte 스캔(±32B)
    for rel in range(-32, 17, 4):
        pos = url_ofs + rel
        if 0 <= pos <= len(blob) - 4:
            raw = struct.unpack_from('<I', blob, pos)[0]
            for conv in _CONV4:
                dt_raw = conv(raw)
                if dt_raw and (dt := _normalize_decode(dt_raw)):
                    cand.append(dt)

    return max(cand).isoformat() if cand else None

# ────────────────────────────────────────────────
# URL · 제목 추정
# ────────────────────────────────────────────────
URL_RE   = re.compile(rb'https?://[!-~]+')
UTF16_RE = re.compile(rb'(?:[\x20-\x7E]\x00){3,}')

def is_readable(txt: str) -> bool:
    return (sum(c.isprintable() for c in txt) / len(txt)) >= 0.7 if txt else False

def guess_title(blob: bytes, end_ofs: int) -> Optional[str]:
    # 패턴 ① [len(4B)] + UTF-16LE
    if end_ofs + 4 <= len(blob):
        length = struct.unpack_from('<I', blob, end_ofs)[0]
        if 0 < length <= 512:
            raw = blob[end_ofs + 4 : end_ofs + 4 + length * 2]
            if len(raw) == length * 2:
                try:
                    txt = raw.decode('utf-16le').strip('\x00')
                    if is_readable(txt):
                        return txt
                except UnicodeDecodeError:
                    pass
    # 패턴 ② URL 뒤 널 이후 UTF-16LE 시퀀스
    if end_ofs < len(blob) and blob[end_ofs] == 0x00:
        m = UTF16_RE.match(blob, end_ofs + 1)
        if m:
            try:
                txt = m.group(0).decode('utf-16le').strip('\x00')
                if is_readable(txt):
                    return txt
            except UnicodeDecodeError:
                pass
    return None

# ────────────────────────────────────────────────
# 메인 파서
# ────────────────────────────────────────────────
def parse_snss_session(path: str | Path) -> List[Dict[str, Optional[str]]]:
    blob = Path(path).read_bytes()
    out: List[Dict[str, Optional[str]]] = []

    for m in URL_RE.finditer(blob):
        url_b  = m.group(0)
        url    = url_b.decode('ascii', errors='replace').rstrip('"\')]\x00')
        ts     = guess_timestamp(blob, m.start())
        title  = guess_title(blob, m.end())
        out.append({'timestamp': ts, 'url': url, 'title': title})
    return out

# ────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────
def main(argv):
    if len(argv) != 2:
        print(f'Usage: {Path(argv[0]).name} <session_file.bin>', file=sys.stderr)
        sys.exit(1)

    try:
        records = parse_snss_session(argv[1])
    except Exception as e:
        print(f'[ERROR] {e}', file=sys.stderr)
        sys.exit(2)

    json.dump(records, sys.stdout, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    main(sys.argv)


# ────────────────────────────────────────────────
# Entry point function
# ────────────────────────────────────────────────
def snss_parser(backup_path, filename):
    # Injects the logic that was previously driven by command-line arguments
    import sys
    sys.argv = ['snss_parser.py', backup_path, filename]
    results = []
    def print_capture(*args, **kwargs):
        results.append(' '.join(str(arg) for arg in args))
    import builtins
    original_print = builtins.print
    builtins.print = print_capture
    try:
        if __name__ == "__main__":  # ensure main logic is triggered
            main()  # assuming there's a main function
    finally:
        builtins.print = original_print
    return results
