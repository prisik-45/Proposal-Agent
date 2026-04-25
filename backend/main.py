import argparse

from src.graph import build_graph


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tarkshy Proposal Generator")
    parser.add_argument("--client-business-name", required=True)
    parser.add_argument("--client-requirements", required=True)
    parser.add_argument("--timeline-days", required=True, type=int)
    parser.add_argument("--price-min", required=True, help="Minimum price (e.g., 25,000)")
    parser.add_argument("--price-max", required=True, help="Maximum price (e.g., 40,000)")
    parser.add_argument("--includes-text", required=True, help="What's included in pricing (e.g., 'Full development • Domain setup • Basic SEO • 3 months maintenance')")
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
                "price_min": args.price_min,
                "price_max": args.price_max,
                "includes_text": args.includes_text,
            }
        }
    )

    print(result.get("drive_public_link", ""))


if __name__ == "__main__":
    main()
