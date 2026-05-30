from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="OCR PDF scan sang Markdown bằng Marker")
    parser.add_argument("--input", required=True, help="Đường dẫn PDF")
    parser.add_argument("--output", default="data/md_raw", help="Thư mục output markdown thô")
    parser.add_argument("--force-ocr", action="store_true", help="Ép OCR cho PDF scan")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)

    cmd = ["marker_single", args.input, "--output_dir", str(out)]
    if args.force_ocr:
        cmd.append("--force_ocr")
    # Marker versions may differ. If workers flag fails, remove it.
    if args.workers:
        cmd += ["--workers", str(args.workers)]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)


if __name__ == "__main__":
    main()
