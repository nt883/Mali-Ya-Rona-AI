import os

from decimal import Decimal

from fastapi import Header
from pydantic import BaseModel

from core.config import (
    AUTHORITY_REGISTRY_PATH,
    GOVBANK_PATH,
    PUBLIC_SEED_PATH
)

from integration.govbank_bridge import (
    build_govbank_graph
)

from registry.service import (
    RegistryService
)

from govbank.service import (
    GovBankService,
    rand_to_cents
)

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from data_source import (
    load_seed,
    build_indexes,
    get_project_branch
)

from anomaly_engine import scan_all


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parent

DEFAULT_SEED_PATH = (
    ROOT.parent
    / "mali-ya-rona"
    / "data"
    / "demo.json"
)

SEED_PATH = Path(
    os.getenv(
        "MALI_SEED_PATH",
        str(DEFAULT_SEED_PATH)
    )
).expanduser().resolve()

WEB_FOLDER = ROOT / "web"


# ---------------------------------------------------------
# APP
# ---------------------------------------------------------

app = FastAPI(
    title="Mali Ya Rona External Monitoring Engine",
    description=(
        "Independent monitoring API that reads "
        "Mali Ya Rona structured data and identifies "
        "review-worthy anomalies."
    ),
    version="1.0.0"
)


app.mount(
    "/static",
    StaticFiles(directory=WEB_FOLDER),
    name="static"
)


# ---------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------

def get_data():

    try:
        return load_seed(SEED_PATH)

    except FileNotFoundError:

        raise HTTPException(
            status_code=500,
            detail=(
                "External Mali Ya Rona data source "
                f"was not found at: {SEED_PATH}"
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


# ---------------------------------------------------------
# HELPERS
# ---------------------------------------------------------

def group_flags_by_project(flags):

    grouped = {}

    for flag in flags:

        project_id = flag["project_id"]

        if project_id not in grouped:
            grouped[project_id] = []

        grouped[project_id].append(flag)

    return grouped


def highest_severity(flags):

    severities = [
        flag.get("severity")
        for flag in flags
    ]

    if "high" in severities:
        return "high"

    if "medium" in severities:
        return "medium"

    if "low" in severities:
        return "low"

    return "none"


# ---------------------------------------------------------
# FRONTEND
# ---------------------------------------------------------

@app.get("/")
def home():

    return FileResponse(
        WEB_FOLDER / "index.html"
    )

@app.get("/about")
def about():

    return FileResponse(
        WEB_FOLDER / "about.html"
    )


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/api/health")
def health():

    return {
        "status": "running",
        "seed_path": str(SEED_PATH)
    }


# ---------------------------------------------------------
# MAIN DASHBOARD
# ---------------------------------------------------------

@app.get("/api/dashboard")
def dashboard():

    data = get_data()

    indexes = build_indexes(data)

    all_flags = scan_all(data)

    flags_by_project = (
        group_flags_by_project(
            all_flags
        )
    )

    projects = []

    for project in data.get(
        "projects",
        []
    ):

        project_flags = (
            flags_by_project.get(
                project["id"],
                []
            )
        )

        community = (
            indexes["communities"]
            .get(
                project.get(
                    "community_id"
                )
            )
        ) or {}

        tender = project.get(
            "tender",
            {}
        )

        supplier = (
            indexes["suppliers"]
            .get(
                tender.get(
                    "supplier_id"
                )
            )
        ) or {}

        delivery = project.get(
            "delivery",
            {}
        )

        projects.append({
            "id":
                project["id"],

            "name":
                project.get("name"),

            "sector":
                project.get("sector"),

            "community":
                community.get("name"),

            "supplier":
                supplier.get("name"),

            "implementing_institution":
                project.get(
                    "implementing_institution"
                ),

            "official_status":
                delivery.get(
                    "official_status"
                ),

            "due_at":
                tender.get(
                    "due_at"
                ),

            "flag_count":
                len(project_flags),

            "highest_severity":
                highest_severity(
                    project_flags
                ),

            "flags":
                project_flags
        })

    high_count = sum(
        1
        for flag in all_flags
        if flag.get("severity") == "high"
    )

    medium_count = sum(
        1
        for flag in all_flags
        if flag.get("severity") == "medium"
    )

    affected_projects = {
        flag["project_id"]
        for flag in all_flags
    }

    return {

        "metadata": {
            "source_mode":
                data.get("source_mode"),

            "as_of":
                data.get("as_of"),

            "currency":
                data.get("currency"),

            "schema_version":
                data.get("schema_version"),

            "source_path":
                str(SEED_PATH)
        },

        "summary": {
            "projects":
                len(projects),

            "communities":
                len(
                    data.get(
                        "communities",
                        []
                    )
                ),

            "review_flags":
                len(all_flags),

            "high_flags":
                high_count,

            "medium_flags":
                medium_count,

            "affected_projects":
                len(affected_projects),

            "clear_projects":
                (
                    len(projects)
                    - len(affected_projects)
                )
        },

        "projects":
            projects
    }


# ---------------------------------------------------------
# ALL FLAGS
# ---------------------------------------------------------

@app.get("/api/flags")
def flags():

    data = get_data()

    return {
        "flags": scan_all(data)
    }


# ---------------------------------------------------------
# FUNDING NETWORK
# ---------------------------------------------------------

@app.get(
    "/api/money-flow"
)
def money_flow():

    data = get_data()


    # -------------------------------------
    # Prefer real prototype GovBank events.
    # -------------------------------------

    govbank_graph = (
        build_govbank_graph(
            data
        )
    )


    if govbank_graph.get(
        "available"
    ):

        govbank_graph[
            "as_of"
        ] = data.get(
            "as_of"
        )

        govbank_graph[
            "route_note"
        ] = (
            "This graph is generated from "
            "public-safe transactions published "
            "by the GovBank prototype."
        )

        return govbank_graph


    # -------------------------------------
    # FALLBACK:
    # old seed graph if GovBank is empty.
    # -------------------------------------

    flows = data.get(
        "money_flows",
        []
    )


    if not flows:

        return {
            "available": False,
            "message":
                "No funding-flow data exists."
        }


    flow = flows[0]


    transfers = []


    for transfer in flow.get(
        "transfers",
        []
    ):

        sent = transfer.get(
            "amount_sent_cents",
            0
        )

        received = transfer.get(
            "amount_received_cents",
            0
        )

        difference = (
            sent - received
        )


        transfers.append({

            **transfer,

            "difference_cents":
                difference,

            "status":
                (
                    "review"
                    if difference != 0
                    else "matched"
                )
        })


    return {

        "available":
            True,

        "source":
            "seed_fallback",

        "id":
            flow.get("id"),

        "title":
            flow.get("title"),

        "currency":
            flow.get("currency"),

        "as_of":
            flow.get("as_of"),

        "route_note":
            flow.get(
                "route_note"
            ),

        "nodes":
            flow.get(
                "nodes",
                []
            ),

        "transfers":
            transfers
    }


# ---------------------------------------------------------
# INDIVIDUAL PROJECT
# ---------------------------------------------------------

@app.get("/api/projects/{project_id}")
def project_detail(
    project_id: str
):

    data = get_data()

    indexes = build_indexes(data)

    project = (
        indexes["projects"]
        .get(project_id)
    )

    if not project:

        raise HTTPException(
            status_code=404,
            detail="Project not found."
        )

    branch = get_project_branch(
        project,
        data,
        indexes
    )

    project_flags = [
        flag
        for flag in scan_all(data)
        if flag["project_id"]
        == project_id
    ]

    return {
        "branch":
            branch,

        "flags":
            project_flags,

        "highest_severity":
            highest_severity(
                project_flags
            )
    }

registry_service = RegistryService(
    AUTHORITY_REGISTRY_PATH
)

govbank_service = GovBankService(
    GOVBANK_PATH,
    PUBLIC_SEED_PATH
)

class FundingReceiptInput(
    BaseModel
):

    account_id: str
    amount_rand: Decimal
    source_name: str
    source_reference: str


class AllocationInput(
    BaseModel
):

    source_account_id: str
    title: str
    amount_rand: Decimal
    service_sector: str
    location_scope: str
    allowed_edges: list[str]
    project_id: str | None = None


class TransferInput(
    BaseModel
):

    allocation_id: str
    from_account_id: str
    to_account_id: str
    amount_rand: Decimal
    purpose: str
    service_sector: str
    project_id: str | None = None
    public_service: bool = True

class ReviewTransferInput(
    BaseModel
):

    action: str
    reason: str

def get_actor_from_header(
    x_actor_id: str
):

    try:

        return (
            registry_service
            .get_actor(
                x_actor_id
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=403,
            detail=str(error)
        )

@app.get(
    "/api/govbank"
)
def govbank_overview():

    return (
        govbank_service
        .overview()
    )


@app.get(
    "/api/registry/me"
)
def registry_me(
    x_actor_id: str = Header(
        ...,
        alias="X-Actor-ID"
    )
):

    return get_actor_from_header(
        x_actor_id
    )


@app.post(
    "/api/govbank/funding-receipts"
)
def govbank_receive_funds(

    payload:
        FundingReceiptInput,

    x_actor_id: str = Header(
        ...,
        alias="X-Actor-ID"
    )
):

    actor = get_actor_from_header(
        x_actor_id
    )

    try:

        return (
            govbank_service
            .receive_funds(

                actor=actor,

                account_id=
                    payload.account_id,

                amount_cents=
                    rand_to_cents(
                        payload.amount_rand
                    ),

                source_name=
                    payload.source_name,

                source_reference=
                    payload.source_reference
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.post(
    "/api/govbank/allocations"
)
def govbank_create_allocation(

    payload:
        AllocationInput,

    x_actor_id: str = Header(
        ...,
        alias="X-Actor-ID"
    )
):

    actor = get_actor_from_header(
        x_actor_id
    )

    try:

        return (
            govbank_service
            .create_allocation(

                actor=actor,

                source_account_id=
                    payload
                    .source_account_id,

                title=
                    payload.title,

                amount_cents=
                    rand_to_cents(
                        payload.amount_rand
                    ),

                service_sector=
                    payload.service_sector,

                location_scope=
                    payload.location_scope,

                allowed_edges=
                    payload.allowed_edges,

                project_id=
                    payload.project_id
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.post(
    "/api/govbank/transfers"
)
def govbank_initiate_transfer(

    payload:
        TransferInput,

    x_actor_id: str = Header(
        ...,
        alias="X-Actor-ID"
    )
):

    actor = get_actor_from_header(
        x_actor_id
    )

    try:

        return (
            govbank_service
            .initiate_transfer(

                actor=actor,

                allocation_id=
                    payload.allocation_id,

                from_account_id=
                    payload.from_account_id,

                to_account_id=
                    payload.to_account_id,

                amount_cents=
                    rand_to_cents(
                        payload.amount_rand
                    ),

                purpose=
                    payload.purpose,

                service_sector=
                    payload.service_sector,

                project_id=
                    payload.project_id,

                public_service=
                    payload.public_service
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )


@app.post(
    "/api/govbank/transfers/"
    "{transaction_id}/approve"
)
def govbank_approve_transfer(

    transaction_id: str,

    x_actor_id: str = Header(
        ...,
        alias="X-Actor-ID"
    )
):

    actor = get_actor_from_header(
        x_actor_id
    )

    try:

        return (
            govbank_service
            .approve_transfer(
                actor,
                transaction_id
            )
        )

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

@app.post(
    "/api/govbank/transfers/"
    "{transaction_id}/review"
)
def govbank_review_transfer(

    transaction_id: str,

    payload:
        ReviewTransferInput,

    x_actor_id: str = Header(
        ...,
        alias="X-Actor-ID"
    )
):

    actor = get_actor_from_header(
        x_actor_id
    )


    try:

        return (
            govbank_service
            .review_transfer(

                actor=actor,

                transaction_id=
                    transaction_id,

                action=
                    payload.action,

                reason=
                    payload.reason
            )
        )


    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

@app.get(
    "/api/registry/actors"
)
def registry_actors():

    return {
        "actors":
            registry_service
            .list_actors()
    }

@app.get(
    "/govbank"
)
def govbank_page():

    return FileResponse(
        WEB_FOLDER
        / "govbank.html"
    )

