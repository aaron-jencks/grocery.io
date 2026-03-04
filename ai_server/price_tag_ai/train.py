from __future__ import annotations

import argparse
from pathlib import Path

from price_tag_ai.config import load_config


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        dest="configs",
        action="append",
        required=True,
        help="JSON config file. Pass multiple times to layer configs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(*args.configs)

    output_dir = Path(config.train.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Experiment: {config.experiment_name}")
    print(f"Device: {config.train.device}")
    print(f"Train manifest: {config.dataset.train_manifest}")
    print(f"Val manifest: {config.dataset.val_manifest}")
    print(f"Output dir: {output_dir}")
    print("Training entrypoint scaffold is ready.")


if __name__ == "__main__":
    main()
