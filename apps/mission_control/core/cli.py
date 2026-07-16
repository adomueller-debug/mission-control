import argparse


def parse_args():
    parser = argparse.ArgumentParser(prog="mission")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("status")

    agent_parser = subparsers.add_parser("agent")
    agent_parser.add_argument("name")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("agent")
    run_parser.add_argument("task")

    subparsers.add_parser("start")

    return parser.parse_args()
