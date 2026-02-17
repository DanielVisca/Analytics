import json
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator

from app.config import settings


def _properties_depth(d: Any) -> int:
    """Return maximum nesting depth of dict. Empty dict has depth 1."""
    if not isinstance(d, dict):
        return 0
    if not d:
        return 1
    return 1 + max(_properties_depth(v) for v in d.values())


class CaptureEvent(BaseModel):
    event: str = Field(..., min_length=1, max_length=4096)
    distinct_id: str = Field(..., min_length=1, max_length=4096)
    timestamp: Optional[str] = None
    properties: Optional[dict[str, Any]] = None
    uuid: Optional[UUID] = None
    project_id: Optional[str] = Field(None, max_length=256)
    lib: Optional[str] = Field(None, alias="$lib", max_length=128)
    lib_version: Optional[str] = Field(None, alias="$lib_version", max_length=64)
    device_id: Optional[str] = Field(None, alias="$device_id", max_length=256)

    model_config = {"populate_by_name": True, "extra": "allow"}

    @field_validator("timestamp", mode="before")
    @classmethod
    def optional_iso(cls, v: Any) -> Optional[str]:
        if v is None or v == "":
            return None
        if isinstance(v, datetime):
            return v.isoformat()
        return str(v)

    @model_validator(mode="after")
    def validate_properties_limits(self) -> "CaptureEvent":
        if self.properties is None:
            return self
        p = self.properties
        if len(p) > settings.properties_max_keys:
            raise ValueError(
                f"properties has {len(p)} keys; maximum is {settings.properties_max_keys}"
            )
        depth = _properties_depth(p)
        if depth > settings.properties_max_depth:
            raise ValueError(
                f"properties depth {depth} exceeds maximum {settings.properties_max_depth}"
            )
        serialized = json.dumps(p)
        if len(serialized.encode("utf-8")) > settings.properties_max_size_bytes:
            raise ValueError(
                f"properties serialized size exceeds maximum {settings.properties_max_size_bytes} bytes"
            )
        return self

    def kafka_key(self) -> str:
        return self.distinct_id

    def serialized(self) -> bytes:
        return self.model_dump_json(by_alias=True, exclude_none=False).encode("utf-8")


class CaptureBatch(BaseModel):
    batch: list[CaptureEvent] = Field(..., min_length=1, max_length=100)
    project_id: Optional[str] = Field(None, max_length=256)


def normalize_body(body: dict[str, Any]) -> list[tuple[CaptureEvent, str]]:
    """Return list of (event, kafka_key). Single event or batch."""
    if "batch" in body:
        batch = CaptureBatch(**body)
        default_project = batch.project_id
        out = []
        for ev in batch.batch:
            if default_project and not ev.project_id:
                ev = ev.model_copy(update={"project_id": default_project})
            out.append((ev, ev.kafka_key()))
        return out
    ev = CaptureEvent(**body)
    return [(ev, ev.kafka_key())]
