from __future__ import annotations

import argparse

from math_graphrag.orchestrator import PipelineOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Orchestrator cho Math GraphRAG pipeline")
    parser.add_argument("--stage", choices=["ocr", "preprocess", "index", "all"], required=True)
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--input-pdf", help="PDF input nếu chạy stage ocr/all")
    parser.add_argument("--input-md", help="File md thô nếu chỉ preprocess một file")
    parser.add_argument("--output-md", help="File md sạch nếu chỉ preprocess một file")
    args = parser.parse_args()

    orch = PipelineOrchestrator(args.config)

    if args.stage == "ocr":
        orch.run_ocr(args.input_pdf)
    elif args.stage == "preprocess":
        orch.run_preprocess(args.input_md, args.output_md)
    elif args.stage == "index":
        print(orch.run_index())
    elif args.stage == "all":
        if args.input_pdf:
            orch.run_ocr(args.input_pdf)
        orch.run_preprocess(args.input_md, args.output_md)
        print(orch.run_index())


if __name__ == "__main__":
    main()
