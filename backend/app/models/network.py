"""Network monitoring, PCAP, and traffic models."""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class MonitoringMode(str, enum.Enum):
    offline = "offline"
    live = "live"
    replay = "replay"


class PcapStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    processed = "processed"
    failed = "failed"


class TrafficLabel(str, enum.Enum):
    normal = "normal"
    suspicious = "suspicious"
    attack = "attack"
    unknown = "unknown"


class PcapFile(Base, TimestampMixin):
    __tablename__ = "pcap_files"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    sha256: Mapped[str] = mapped_column(String(64), default="", index=True)
    status: Mapped[PcapStatus] = mapped_column(
        Enum(PcapStatus, name="pcap_status"),
        default=PcapStatus.uploaded,
        nullable=False,
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str] = mapped_column(Text, default="")
    uploaded_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)

    traffic_records: Mapped[list["TrafficRecord"]] = relationship(back_populates="pcap")
    network_events: Mapped[list["NetworkEvent"]] = relationship(back_populates="pcap")


class TrafficRecord(Base, TimestampMixin):
    """Flow-level features extracted from PCAP / Zeek / Scapy."""

    __tablename__ = "traffic_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    pcap_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pcap_files.id"), index=True)
    source_ip: Mapped[str] = mapped_column(String(64), index=True, default="")
    dest_ip: Mapped[str] = mapped_column(String(64), index=True, default="")
    source_port: Mapped[int] = mapped_column(Integer, default=0)
    dest_port: Mapped[int] = mapped_column(Integer, default=0)
    protocol: Mapped[str] = mapped_column(String(32), default="")
    duration: Mapped[float] = mapped_column(Float, default=0.0)
    packet_count: Mapped[int] = mapped_column(Integer, default=0)
    bytes_transferred: Mapped[int] = mapped_column(BigInteger, default=0)
    connection_state: Mapped[str] = mapped_column(String(64), default="")
    tcp_flags: Mapped[str] = mapped_column(String(64), default="")
    label: Mapped[TrafficLabel] = mapped_column(
        Enum(TrafficLabel, name="traffic_label"),
        default=TrafficLabel.unknown,
    )
    raw_features_json: Mapped[str] = mapped_column(Text, default="{}")

    pcap: Mapped[Optional[PcapFile]] = relationship(back_populates="traffic_records")


class NetworkEvent(Base, TimestampMixin):
    __tablename__ = "network_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    pcap_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pcap_files.id"), index=True)
    traffic_record_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("traffic_records.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(128), default="connection")
    source_ip: Mapped[str] = mapped_column(String(64), index=True, default="")
    dest_ip: Mapped[str] = mapped_column(String(64), index=True, default="")
    source_port: Mapped[int] = mapped_column(Integer, default=0)
    dest_port: Mapped[int] = mapped_column(Integer, default=0)
    protocol: Mapped[str] = mapped_column(String(32), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    is_suspicious: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    observed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    monitoring_mode: Mapped[MonitoringMode] = mapped_column(
        Enum(MonitoringMode, name="monitoring_mode"),
        default=MonitoringMode.offline,
    )

    pcap: Mapped[Optional[PcapFile]] = relationship(back_populates="network_events")
