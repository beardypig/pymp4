from __future__ import annotations

from abc import ABC
from uuid import UUID

from construct import Adapter, int2byte


class ISO6392TLanguageCode(Adapter, ABC):
    def _decode(self, obj, context, path):
        return b"".join(map(int2byte, [c + 0x60 for c in bytearray(obj)])).decode("utf8")

    def _encode(self, obj, context, path):
        return [c - 0x60 for c in bytearray(obj.encode("utf8"))]


class MaskedInteger(Adapter, ABC):
    def _decode(self, obj, context, path):
        return obj & 0x1F

    def _encode(self, obj, context, path):
        return obj & 0x1F


class UUIDBytes(Adapter, ABC):
    def _decode(self, obj, context, path):
        return UUID(bytes=obj)

    def _encode(self, obj, context, path):
        return obj.bytes
