from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

from .utils import load_yaml


def load_config(path: str | Path = "configs/config.yaml") -> dict:
    load_dotenv()
    cfg = load_yaml(path)

    llm_provider_env = cfg.get("llm", {}).get("provider_env")
    if llm_provider_env and os.getenv(llm_provider_env):
        cfg["llm"]["provider"] = os.getenv(llm_provider_env)

    return cfg
