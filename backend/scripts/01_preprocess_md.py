from __future__ import annotations

import argparse
from pathlib import Path

from math_graphrag.config import load_config
from math_graphrag.preprocess import preprocess_directory, preprocess_file


def main():
    parser = argparse.ArgumentParser(description="Làm sạch markdown sau OCR và giữ số trang")
    parser.add_argument("--input", help="File .md hoặc thư mục md_raw")
    parser.add_argument("--output", help="File output hoặc thư mục md_clean")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    input_path = Path(args.input or config["paths"]["raw_md_dir"])
    output_path = Path(args.output or config["paths"]["clean_md_dir"])

    if input_path.is_dir():
        outs = preprocess_directory(input_path, output_path, config)
        print(f"Done. Preprocessed {len(outs)} files -> {output_path}")
    else:
        out = output_path
        if output_path.suffix.lower() != ".md":
            out = output_path / input_path.name
        preprocess_file(input_path, out, config)
        print(f"Done -> {out}")


if __name__ == "__main__":
    main()
