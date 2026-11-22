"""Unit/API-oriented tests that do not require a live server for pure functions."""

from __future__ import annotations

import pytest

from app.network.pcap_validation import PcapValidationError, validate_magic, validate_pcap_bytes
from app.response.actions import ActionError, validate_lab_ip


def test_lab_ip_allows_private():
    assert validate_lab_ip("10.0.0.5") == "10.0.0.5"
    assert validate_lab_ip("192.168.1.10") == "192.168.1.10"


def test_lab_ip_rejects_public():
    with pytest.raises(ActionError):
        validate_lab_ip("8.8.8.8")


def test_pcap_magic_classic():
    assert validate_magic(b"\xd4\xc3\xb2\xa1" + b"\x00" * 12) == "pcap"


def test_pcap_magic_rejects_text():
    with pytest.raises(PcapValidationError):
        validate_pcap_bytes(b"hello world not pcap", "x.pcap")


def test_pcap_extension_rejected():
    with pytest.raises(PcapValidationError):
        validate_pcap_bytes(b"\xd4\xc3\xb2\xa1" + b"\x00" * 20, "malware.exe")
