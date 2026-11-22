"""PCAP / PCAPNG file validation helpers."""

from __future__ import annotations

from pathlib import Path

# Classic pcap (endian variants) and pcapng section header block
PCAP_MAGICS = {
    b"\xd4\xc3\xb2\xa1",
    b"\xa1\xb2\xc3\xd4",
    b"\x4d\x3c\xb2\xa1",
    b"\xa1\xb2\x3c\x4d",
}
PCAPNG_MAGIC = b"\x0a\x0d\x0d\x0a"

ALLOWED_EXTENSIONS = {".pcap", ".pcapng", ".cap"}
MAX_PCAP_BYTES = 50 * 1024 * 1024  # 50 MB


class PcapValidationError(ValueError):
    pass


def validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise PcapValidationError(
            f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    return suffix


def validate_size(size: int) -> None:
    if size <= 0:
        raise PcapValidationError("Empty file is not a valid capture.")
    if size > MAX_PCAP_BYTES:
        raise PcapValidationError(
            f"File too large ({size} bytes). Maximum allowed is {MAX_PCAP_BYTES} bytes (50 MB)."
        )


def validate_magic(header: bytes) -> str:
    if len(header) < 4:
        raise PcapValidationError("File header too short to identify capture format.")
    if header[:4] in PCAP_MAGICS:
        return "pcap"
    if header[:4] == PCAPNG_MAGIC:
        return "pcapng"
    raise PcapValidationError(
        "File does not look like a PCAP/PCAPNG capture (invalid magic bytes)."
    )


def validate_pcap_bytes(data: bytes, filename: str) -> str:
    validate_extension(filename)
    validate_size(len(data))
    return validate_magic(data[:16])
