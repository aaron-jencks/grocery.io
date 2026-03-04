import argparse
from pathlib import Path

from db_server.server import serve


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=50051)
    parser.add_argument("--db-path", default="data/grocery.db")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    server = serve(host=args.host, port=args.port, db_path=Path(args.db_path))
    server.wait_for_termination()
