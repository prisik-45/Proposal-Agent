import argparse

from src.graph import build_graph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tarkshy Proposal Generator")
    parser.add_argument("--client-business-name", required=True)
    parser.add_argument("--client-requirements", required=True)
    parser.add_argument("--timeline-days", required=True, type=int)
    return parser.parse_args()


def main():
    args = parse_args()
    graph = build_graph()
    result = graph.invoke(
        {
            "input": {
                "client_business_name": args.client_business_name,
                "client_requirements": args.client_requirements,
                "timeline_days": args.timeline_days,
            }
        }
    )

    print(result.get("drive_public_link", ""))


if __name__ == "__main__":
    main()
