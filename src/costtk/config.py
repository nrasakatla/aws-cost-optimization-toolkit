"""Configuration and environment gating.

The toolkit is *synthetic by default*. Live AWS collection requires BOTH an
explicit environment flag and the opt-in CLI switch. There is no code path that
touches boto3 unless both are set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_COLLECTOR = "COSTTK_COLLECTOR"  # "sample" (default) | "live"
ENV_READ_ONLY = "COSTTK_READ_ONLY"  # must be "1" for live collection


@dataclass(frozen=True)
class Settings:
    collector: str = "sample"
    read_only: bool = False
    data_dir: str = "data"

    @property
    def live_collection_enabled(self) -> bool:
        return self.read_only and self.collector == "live"


def load_settings() -> Settings:
    return Settings(
        collector=os.environ.get(ENV_COLLECTOR, "sample"),
        read_only=os.environ.get(ENV_READ_ONLY, "0") == "1",
        data_dir=os.environ.get("COSTTK_DATA_DIR", "data"),
    )
