#And this is the starter program iof the system

import json
import sys

from data_source import (
    load_seed,
    build_indexes,
    get_project_branch
)

from anomaly_engine import scan_all


def show_connections(data):

    indexes = build_indexes(data)

    print()
    print("CONNECTED DATA BRANCHES")
    print("=" * 60)

    for project in data.get(
        "projects",
        []
    ):

        branch = get_project_branch(
            project,
            data,
            indexes
        )

        community = (
            branch["community"]
            or {}
        )

        supplier = (
            branch["supplier"]
            or {}
        )

        print()
        print(
            project["name"]
        )

        print(
            "Project ID:",
            project["id"]
        )

        print(
            "Community:",
            community.get(
                "name",
                "Unknown"
            )
        )

        print(
            "Supplier:",
            supplier.get(
                "name",
                "Unknown"
            )
        )

        print(
            "Expenses:",
            len(
                branch["expenses"]
            )
        )

        print(
            "Transfers:",
            len(
                branch["transfers"]
            )
        )

        print(
            "Community reports:",
            len(
                branch[
                    "community_reports"
                ]
            )
        )


def main():

    if len(sys.argv) < 2:

        print(
            "Please provide the "
            "path to demo.json."
        )

        print()
        print(
            "Example:"
        )

        print(
            'python main.py '
            '"../mali-ya-rona/data/demo.json"'
        )

        return

    seed_path = sys.argv[1]

    data = load_seed(
        seed_path
    )

    print()
    print(
        "MALI YA RONA"
    )

    print(
        "EXTERNAL MONITORING ENGINE"
    )

    print("=" * 60)

    print(
        "Data mode:",
        data.get(
            "source_mode"
        )
    )

    print(
        "Data date:",
        data.get(
            "as_of"
        )
    )

    show_connections(data)

    flags = scan_all(data)

    print()
    print()
    print(
        "UNUSUALITY REVIEW FLAGS"
    )

    print("=" * 60)

    if len(flags) == 0:

        print(
            "No unusualities detected."
        )

        return

    for number, flag in enumerate(
        flags,
        start=1
    ):

        print()
        print(
            f"[{number}]",
            flag["rule_id"]
        )

        print(
            "Severity:",
            flag["severity"].upper()
        )

        print(
            "Project:",
            flag["project_id"]
        )

        print(
            "Reason:",
            flag["reason"]
        )

        print(
            json.dumps(
                flag["details"],
                indent=4
            )
        )


if __name__ == "__main__":
    main()