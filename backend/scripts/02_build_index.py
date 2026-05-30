from __future__ import annotations

import argparse

from math_graphrag.config import load_config
from math_graphrag.indexing import build_index
from math_graphrag.logger import setup_logger, log_stage


def main():
    parser = argparse.ArgumentParser(description="Build Math GraphRAG index vào Neo4j")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--reset", action="store_true", help="Xóa toàn bộ graph trước khi build")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.reset:
        config.setdefault("neo4j", {})["reset_before_index"] = True
    logger = setup_logger(config)
    with log_stage(logger, "build_index_cli"):
        stats = build_index(config, logger=logger)
    print("Done:", stats)


if __name__ == "__main__":
    main()
