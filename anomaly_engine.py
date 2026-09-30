from datetime import date
from statistics import median

#so this is the beginning of our actual intelligence.

PRICE_REVIEW_THRESHOLD_PERCENT = 15


def cents_to_rand(cents):
    return round((cents or 0) / 100, 2)


def create_flag(
    rule_id,
    severity,
    project_id,
    reason,
    details
):

    return {
        "rule_id": rule_id,
        "severity": severity,
        "project_id": project_id,
        "reason": reason,
        "details": details
    }


# -------------------------------------------------
# PRICE CHECK
# -------------------------------------------------

def detect_price_anomalies(project, data):

    flags = []

    for expense in project.get("expenses", []):

        comparable_prices = []

        for offer in data.get("catalogue_offers", []):

            if (
                offer.get("item_key")
                == expense.get("item_key")

                and offer.get("specification")
                == expense.get("specification")

                and offer.get("unit")
                == expense.get("unit")

                and offer.get("region")
                == expense.get("region")
            ):

                amount = offer.get("amount_cents")

                if amount and amount > 0:
                    comparable_prices.append(amount)

        # We want more than one comparison
        if len(comparable_prices) < 2:
            continue

        benchmark = median(comparable_prices)

        claimed_price = expense.get(
            "unit_price_cents",
            0
        )

        if benchmark <= 0:
            continue

        deviation = (
            (claimed_price - benchmark)
            / benchmark
        ) * 100

        if deviation > PRICE_REVIEW_THRESHOLD_PERCENT:

            quantity = expense.get(
                "quantity",
                0
            )

            difference = (
                claimed_price - benchmark
            ) * quantity

            flag = create_flag(
                rule_id="PRICE_ANOMALY",

                severity=(
                    "high"
                    if deviation >= 50
                    else "medium"
                ),

                project_id=project["id"],

                reason=(
                    f"Recorded price is "
                    f"{deviation:.1f}% above "
                    f"the median comparable price."
                ),

                details={
                    "expense_id":
                        expense.get("id"),

                    "invoice_id":
                        expense.get("invoice_id"),

                    "claimed_unit_price_rand":
                        cents_to_rand(
                            claimed_price
                        ),

                    "benchmark_unit_price_rand":
                        cents_to_rand(
                            benchmark
                        ),

                    "benchmark_difference_rand":
                        cents_to_rand(
                            difference
                        ),

                    "number_of_comparisons":
                        len(comparable_prices)
                }
            )

            flags.append(flag)

    return flags


# -------------------------------------------------
# TRANSFER CHECK
# -------------------------------------------------

def detect_transfer_mismatches(project):

    flags = []

    for transfer in project.get(
        "transfers",
        []
    ):

        sent = transfer.get(
            "sent_claim_cents"
        )

        received = transfer.get(
            "received_claim_cents"
        )

        if sent is None or received is None:
            continue

        difference = sent - received

        if difference > 0:

            flags.append(
                create_flag(

                    rule_id=
                        "TRANSFER_MISMATCH",

                    severity="high",

                    project_id=
                        project["id"],

                    reason=(
                        "The reported sent "
                        "and received amounts "
                        "do not reconcile."
                    ),

                    details={
                        "reference":
                            transfer.get(
                                "reference"
                            ),

                        "sent_rand":
                            cents_to_rand(sent),

                        "received_rand":
                            cents_to_rand(
                                received
                            ),

                        "unreconciled_rand":
                            cents_to_rand(
                                difference
                            ),

                        "evidence_status":
                            transfer.get(
                                "reconciliation"
                            ),

                        "warning":
                            (
                                "This is a review "
                                "flag, not proof "
                                "of theft or fraud."
                            )
                    }
                )
            )

    return flags


# -------------------------------------------------
# DELIVERY CHECK
# -------------------------------------------------

def detect_delivery_conflicts(project):

    flags = []

    delivery = project.get(
        "delivery",
        {}
    )

    reports = project.get(
        "community_reports",
        []
    )

    conflict_reports = []

    for report in reports:

        if report.get("type") in [
            "incomplete_delivery",
            "non_delivery",
            "delivery_problem"
        ]:

            conflict_reports.append(report)

    if (
        delivery.get("official_status")
        == "complete"

        and len(conflict_reports) > 0
    ):

        flags.append(
            create_flag(

                rule_id=
                    "OFFICIAL_COMMUNITY_CONFLICT",

                severity="high",

                project_id=
                    project["id"],

                reason=(
                    "Official records say "
                    "the project is complete, "
                    "but community evidence "
                    "reports incomplete delivery."
                ),

                details={
                    "official_status":
                        delivery.get(
                            "official_status"
                        ),

                    "proof_status":
                        delivery.get(
                            "proof_status"
                        ),

                    "report_ids": [
                        report.get("id")
                        for report
                        in conflict_reports
                    ]
                }
            )
        )

    return flags


# -------------------------------------------------
# MISSING DELIVERY PROOF
# -------------------------------------------------

def detect_missing_delivery_proof(project):

    delivery = project.get(
        "delivery",
        {}
    )

    if (
        delivery.get("official_status")
        == "complete"

        and delivery.get("proof_status")
        in [
            None,
            "missing",
            "unavailable"
        ]
    ):

        return [
            create_flag(

                rule_id=
                    "MISSING_DELIVERY_PROOF",

                severity="medium",

                project_id=
                    project["id"],

                reason=(
                    "The project is marked "
                    "complete but delivery "
                    "proof is unavailable."
                ),

                details={
                    "official_status":
                        delivery.get(
                            "official_status"
                        ),

                    "proof_status":
                        delivery.get(
                            "proof_status"
                        )
                }
            )
        ]

    return []


# -------------------------------------------------
# DEADLINE CHECK
# -------------------------------------------------

def detect_late_project(
    project,
    as_of
):

    tender = project.get(
        "tender",
        {}
    )

    due_date = tender.get(
        "due_at"
    )

    official_status = (
        project
        .get("delivery", {})
        .get("official_status")
    )

    if not due_date:
        return []

    if official_status == "complete":
        return []

    due = date.fromisoformat(
        due_date
    )

    current_date = date.fromisoformat(
        as_of
    )

    if current_date <= due:
        return []

    days_late = (
        current_date - due
    ).days

    return [
        create_flag(

            rule_id="LATE_PROJECT",

            severity="medium",

            project_id=
                project["id"],

            reason=(
                f"Project is "
                f"{days_late} days "
                f"past its due date."
            ),

            details={
                "due_at":
                    due_date,

                "as_of":
                    as_of,

                "days_late":
                    days_late,

                "status":
                    official_status
            }
        )
    ]


# -------------------------------------------------
# SCAN EVERYTHING
# -------------------------------------------------

def detect_govbank_transaction_flags(
    data
):

    flags = []


    transactions = data.get(
        "govbank_public_transactions",
        []
    )


    for transaction in transactions:

        project_id = (
            transaction.get(
                "project_id"
            )
            or
            "PUBLIC-FINANCE"
        )


        for policy_flag in transaction.get(
            "policy_flags",
            []
        ):

            flags.append(

                create_flag(

                    rule_id=(
                        "GOVBANK_"
                        + policy_flag.get(
                            "code",
                            "REVIEW"
                        )
                    ),

                    severity=
                        policy_flag.get(
                            "severity",
                            "medium"
                        ),

                    project_id=
                        project_id,

                    reason=
                        policy_flag.get(
                            "reason",
                            "GovBank transaction "
                            "requires review."
                        ),

                    details={

                        "transaction_id":
                            transaction.get(
                                "transaction_id"
                            ),

                        "allocation_id":
                            transaction.get(
                                "allocation_id"
                            ),

                        "from":
                            transaction.get(
                                "from_institution"
                            ),

                        "to":
                            transaction.get(
                                "to_institution"
                            ),

                        "amount_rand":
                            cents_to_rand(
                                transaction.get(
                                    "amount_cents",
                                    0
                                )
                            ),

                        "service_sector":
                            transaction.get(
                                "service_sector"
                            ),

                        "evidence":
                            policy_flag.get(
                                "evidence",
                                {}
                            )
                    }
                )
            )


    return flags

def scan_all(data):

    all_flags = []

    as_of = data.get("as_of")

    for project in data.get(
        "projects",
        []
    ):

        all_flags.extend(
            detect_price_anomalies(
                project,
                data
            )
        )

        all_flags.extend(
            detect_transfer_mismatches(
                project
            )
        )

        all_flags.extend(
            detect_delivery_conflicts(
                project
            )
        )

        all_flags.extend(
            detect_missing_delivery_proof(
                project
            )
        )

        if as_of:

            all_flags.extend(
                detect_late_project(
                    project,
                    as_of
                )
            )
    
    all_flags.extend(
        detect_govbank_transaction_flags(
            data
        )
    )

    return all_flags