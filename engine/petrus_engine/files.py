"""Filesystem availability policy; cloud-only files must never be opened implicitly."""

import stat
import sys
from typing import Protocol


class FileAvailabilityProvider(Protocol):
    def is_available(self, info) -> bool: ...


class GenericFileAvailabilityProvider:
    def is_available(self, info) -> bool:
        return stat.S_ISREG(info.st_mode)


class MacOSFileAvailabilityProvider(GenericFileAvailabilityProvider):
    def is_available(self, info) -> bool:
        return super().is_available(info) and not bool(getattr(info, "st_flags", 0) & 0x40000000)


def availability_provider() -> FileAvailabilityProvider:
    return MacOSFileAvailabilityProvider() if sys.platform == "darwin" else GenericFileAvailabilityProvider()
