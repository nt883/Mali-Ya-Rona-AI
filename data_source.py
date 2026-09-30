import json
from pathlib import Path

#So guys, this is our connector; This is more like another syustem for the Data Seed...

#Our program asks: Give me Project A

#Then our connector determines:
#Who is the community?
#Who is the supplier?
#What tender belongs to it?
#What was purchased?
#What other suppliers charged for it?
#Were there transfers?
#Were there community complaints?

#So this is literally the foundation
#The functions below explain everything.
def load_seed(seed_path):
    """
    Opens an external Mali Ya Rona JSON data source.
    """

    path = Path(seed_path).expanduser().resolve()

    if not path.exists():
        raise FileNotFoundError(
            f"Seed file could not be found:\n{path}"
        )

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    required_sections = [
        "communities",
        "suppliers",
        "catalogue_offers",
        "projects"
    ]

    missing_sections = []

    for section in required_sections:
        if section not in data:
            missing_sections.append(section)

    if missing_sections:
        raise ValueError(
            "The data source is missing: "
            + ", ".join(missing_sections)
        )

    return data


def build_indexes(data):
    """
    Creates quick lookup tables.

    Instead of repeatedly searching through every item,
    we can find something directly using its ID.
    """

    communities = {
        community["id"]: community
        for community in data.get("communities", [])
    }

    suppliers = {
        supplier["id"]: supplier
        for supplier in data.get("suppliers", [])
    }

    projects = {
        project["id"]: project
        for project in data.get("projects", [])
    }

    return {
        "communities": communities,
        "suppliers": suppliers,
        "projects": projects
    }


def get_project_branch(project, data, indexes):
    """
    Connects a project to its related records.

    Project
       -> Community
       -> Supplier
       -> Expenses
       -> Catalogue comparisons
       -> Transfers
       -> Community reports
    """

    tender = project.get("tender", {})

    supplier_id = tender.get("supplier_id")
    community_id = project.get("community_id")

    supplier = indexes["suppliers"].get(supplier_id)
    community = indexes["communities"].get(community_id)

    expense_branches = []

    for expense in project.get("expenses", []):

        comparable_offers = []

        for offer in data.get("catalogue_offers", []):

            same_item = (
                offer.get("item_key")
                == expense.get("item_key")
            )

            same_specification = (
                offer.get("specification")
                == expense.get("specification")
            )

            same_unit = (
                offer.get("unit")
                == expense.get("unit")
            )

            same_region = (
                offer.get("region")
                == expense.get("region")
            )

            if (
                same_item
                and same_specification
                and same_unit
                and same_region
            ):
                comparable_offers.append(offer)

        expense_branches.append({
            "expense": expense,
            "catalogue_offers": comparable_offers
        })

    return {
        "project": project,
        "community": community,
        "supplier": supplier,
        "expenses": expense_branches,
        "transfers": project.get("transfers", []),
        "community_reports":
            project.get("community_reports", [])
    }