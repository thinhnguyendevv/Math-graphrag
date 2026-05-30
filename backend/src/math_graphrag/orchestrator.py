from __future__ import annotations

import subprocess
from pathlib import Path

from .config import load_config
from .indexing import build_index
from .logger import setup_logger, log_stage
from .preprocess import preprocess_directory, preprocess_file


class PipelineOrchestrator:
    def __init__(self, config_path: str | Path = "configs/config.yaml"):
        self.config_path = Path(config_path)
        self.config = load_config(self.config_path)
        self.logger = setup_logger(self.config)

    def run_ocr(self, input_pdf: str | Path | None = None):
        if input_pdf is None:
            raise ValueError("run_ocr cần input_pdf. Nếu đã có file md thì bỏ qua stage ocr.")
        out_dir = self.config.get("paths", {}).get("raw_md_dir", "data/md_raw")
        cmd = ["marker_single", str(input_pdf), "--output_dir", str(out_dir)]
        with log_stage(self.logger, "marker_ocr"):
            self.logger.info("Running: %s", " ".join(cmd))
            subprocess.run(cmd, check=True)

    def run_preprocess(self, input_md: str | Path | None = None, output_md: str | Path | None = None):
        raw_dir = self.config.get("paths", {}).get("raw_md_dir", "data/md_raw")
        clean_dir = self.config.get("paths", {}).get("clean_md_dir", "data/md_clean")
        with log_stage(self.logger, "preprocess_md"):
            if input_md:
                if output_md is None:
                    output_md = Path(clean_dir) / Path(input_md).name
                return preprocess_file(input_md, output_md, self.config)
            return preprocess_directory(raw_dir, clean_dir, self.config)

    def run_index(self):
        with log_stage(self.logger, "build_index"):
            return build_index(self.config, logger=self.logger)
