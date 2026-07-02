import argparse


def parse_args():
    parser = argparse.ArgumentParser(prog="mission")

    parser.add_argument(
        "command",
        choices=["start", "status"],
        help="Auszuführender Befehl"
    )

    return parser.parse_args()
