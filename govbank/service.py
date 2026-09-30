#The SHA-256 chain here makes alteration detectable, but it's not “tamper-proof”.
#Our research specifically warns against that type of claim.

import json
from datetime import (
    datetime,
    timezone
)
from hashlib import sha256
from uuid import uuid4

from core.store import JsonStore

from core.permissions import (
    require_permission
)


def now_iso():

    return (
        datetime.now(
            timezone.utc
        )
        .replace(
            microsecond=0
        )
        .isoformat()
    )


def rand_to_cents(
    amount
):

    return int(
        round(
            float(amount)
            * 100
        )
    )


class GovBankService:

    def __init__(
        self,
        ledger_path,
        public_seed_path
    ):

        self.store = JsonStore(
            ledger_path,
            {
                "schema_version": 1,
                "currency": "ZAR",
                "accounts": [],
                "allocations": [],
                "transactions": [],
                "audit_log": []
            }
        )

        self.public_seed_path = (
            public_seed_path
        )


    # =============================================
    # LOOKUPS
    # =============================================

    def _find_account(
        self,
        data,
        account_id
    ):

        for account in data.get(
            "accounts",
            []
        ):

            if (
                account.get(
                    "account_id"
                )
                == account_id
            ):

                return account

        raise LookupError(
            f"GovBank account not found: "
            f"{account_id}"
        )


    def _find_allocation(
        self,
        data,
        allocation_id
    ):

        for allocation in data.get(
            "allocations",
            []
        ):

            if (
                allocation.get(
                    "allocation_id"
                )
                == allocation_id
            ):

                return allocation

        raise LookupError(
            "Allocation not found."
        )


    def _actor_controls_account(
        self,
        actor,
        account
    ):

        return (
            actor.get(
                "institution_id"
            )
            ==
            account.get(
                "institution_id"
            )
        )


    # =============================================
    # AUDIT
    # =============================================

    def _audit(
        self,
        data,
        actor,
        action,
        reference,
        details=None
    ):

        data.setdefault(
            "audit_log",
            []
        ).append({

            "event_id":
                "AUD-"
                + uuid4().hex[:12].upper(),

            "actor_id":
                actor.get(
                    "actor_id"
                ),

            "action":
                action,

            "reference":
                reference,

            "timestamp":
                now_iso(),

            "details":
                details or {}
        })


    # =============================================
    # HASH CHAIN
    # =============================================

    def _previous_hash(
        self,
        data
    ):

        posted = [

            transaction

            for transaction
            in data.get(
                "transactions",
                []
            )

            if transaction.get(
                "status"
            )
            == "posted"
        ]

        if not posted:
            return None

        return posted[-1].get(
            "record_hash"
        )


    def _hash_record(
        self,
        transaction,
        previous_hash
    ):

        material = {
            "previous_hash":
                previous_hash,

            "transaction_id":
                transaction.get(
                    "transaction_id"
                ),

            "from_account_id":
                transaction.get(
                    "from_account_id"
                ),

            "to_account_id":
                transaction.get(
                    "to_account_id"
                ),

            "amount_cents":
                transaction.get(
                    "amount_cents"
                ),

            "allocation_id":
                transaction.get(
                    "allocation_id"
                ),

            "posted_at":
                transaction.get(
                    "posted_at"
                )
        }

        encoded = json.dumps(
            material,
            sort_keys=True
        ).encode(
            "utf-8"
        )

        return sha256(
            encoded
        ).hexdigest()


    # =============================================
    # PUBLIC OVERVIEW
    # =============================================

    def overview(
        self
    ):

        data = self.store.read()

        return {
            "currency":
                data.get(
                    "currency"
                ),

            "accounts":
                data.get(
                    "accounts",
                    []
                ),

            "allocations":
                data.get(
                    "allocations",
                    []
                ),

            "transactions":
                data.get(
                    "transactions",
                    []
                )
        }


    # =============================================
    # EXTERNAL FUNDING RECEIPT
    # =============================================

    def receive_funds(
        self,
        actor,
        account_id,
        amount_cents,
        source_name,
        source_reference
    ):

        require_permission(
            actor,
            "govbank.receive_funds"
        )

        if amount_cents <= 0:

            raise ValueError(
                "Funding amount must "
                "be greater than zero."
            )

        data = self.store.read()

        account = self._find_account(
            data,
            account_id
        )

        if not self._actor_controls_account(
            actor,
            account
        ):

            raise PermissionError(
                "Actor cannot receive funds "
                "into this institution's account."
            )

        account[
            "balance_cents"
        ] += amount_cents

        transaction_id = (
            "GBR-"
            + uuid4()
            .hex[:12]
            .upper()
        )

        receipt = {

            "transaction_id":
                transaction_id,

            "transaction_type":
                "funding_receipt",

            "from_account_id":
                None,

            "to_account_id":
                account_id,

            "amount_cents":
                amount_cents,

            "source_name":
                source_name,

            "source_reference":
                source_reference,

            "status":
                "posted",

            "initiated_by":
                actor[
                    "actor_id"
                ],

            "approved_by":
                actor[
                    "actor_id"
                ],

            "posted_at":
                now_iso(),

            "previous_hash":
                None,

            "record_hash":
                None
        }

        previous_hash = (
            self._previous_hash(
                data
            )
        )

        receipt[
            "previous_hash"
        ] = previous_hash

        receipt[
            "record_hash"
        ] = self._hash_record(
            receipt,
            previous_hash
        )

        data[
            "transactions"
        ].append(
            receipt
        )

        self._audit(
            data,
            actor,
            "FUNDING_RECEIVED",
            transaction_id,
            {
                "amount_cents":
                    amount_cents,

                "account_id":
                    account_id
            }
        )

        self.store.write(
            data
        )

        return receipt


    # =============================================
    # ALLOCATION
    # =============================================

    def create_allocation(
        self,
        actor,
        source_account_id,
        title,
        amount_cents,
        service_sector,
        location_scope,
        allowed_edges,
        project_id=None
    ):

        require_permission(
            actor,
            "govbank.create_allocation"
        )

        if amount_cents <= 0:

            raise ValueError(
                "Allocation amount must "
                "be greater than zero."
            )

        data = self.store.read()

        source_account = (
            self._find_account(
                data,
                source_account_id
            )
        )

        if not self._actor_controls_account(
            actor,
            source_account
        ):

            raise PermissionError(
                "Actor cannot create an "
                "allocation from this account."
            )

        allocation_id = (
            "ALLOC-"
            + uuid4()
            .hex[:10]
            .upper()
        )

        allocation = {

            "allocation_id":
                allocation_id,

            "title":
                title,

            "source_account_id":
                source_account_id,

            "authorised_amount_cents":
                amount_cents,

            "route_movement_cents":
                0,

            "service_disbursed_cents":
                0,

            "service_sector":
                service_sector,

            "location_scope":
                location_scope,

            "project_id":
                project_id,

            "allowed_edges":
                allowed_edges,

            "status":
                "active",

            "created_by":
                actor[
                    "actor_id"
                ],

            "created_at":
                now_iso()
        }

        data[
            "allocations"
        ].append(
            allocation
        )

        self._audit(
            data,
            actor,
            "ALLOCATION_CREATED",
            allocation_id,
            {
                "amount_cents":
                    amount_cents,

                "service_sector":
                    service_sector
            }
        )

        self.store.write(
            data
        )

        return allocation


    # =============================================
    # POLICY CHECKS
    # =============================================
    def _allocation_position(
        self,
        data,
        allocation,
        account_id
    ):
        """
        Calculates how much of this allocation
        is currently available at a particular
        government account.

        Important:

        National -> Province -> District -> Municipality

        is movement of the same money.

        We must not count the money as new spending
        every time it moves to the next institution.
        """

        allocation_id = allocation[
            "allocation_id"
        ]

        source_account_id = allocation[
            "source_account_id"
        ]


        # The original source begins with the
        # authorised allocation amount.

        starting_position = 0

        if (
            account_id
            == source_account_id
        ):

            starting_position = allocation[
                "authorised_amount_cents"
            ]


        incoming = 0
        outgoing = 0
        reserved = 0


        for transaction in data.get(
            "transactions",
            []
        ):

            if (
                transaction.get(
                    "allocation_id"
                )
                != allocation_id
            ):
                continue


            status = transaction.get(
                "status"
            )


            # Money that has actually arrived.

            if (
                status == "posted"
                and
                transaction.get(
                    "to_account_id"
                )
                == account_id
            ):

                incoming += transaction.get(
                    "amount_cents",
                    0
                )


            # Money that has already left.

            if (
                status == "posted"
                and
                transaction.get(
                    "from_account_id"
                )
                == account_id
            ):

                outgoing += transaction.get(
                    "amount_cents",
                    0
                )


            # Pending transactions reserve money
            # so two pending transactions cannot
            # spend the same balance twice.

            if (
                status
                in [
                    "pending_approval",
                    "pending_review"
                ]
                and
                transaction.get(
                    "from_account_id"
                )
                == account_id
            ):

                reserved += transaction.get(
                    "amount_cents",
                    0
                )


        available = (
            starting_position
            + incoming
            - outgoing
            - reserved
        )


        return {
            "starting_position_cents":
                starting_position,

            "incoming_cents":
                incoming,

            "outgoing_cents":
                outgoing,

            "reserved_cents":
                reserved,

            "available_cents":
                available
        }


    def evaluate_transfer(
        self,
        data,
        allocation,
        from_account,
        to_account,
        amount_cents,
        service_sector,
        project_id
    ):

        flags = []

        position = self._allocation_position(
            data,
            allocation,
            from_account[
                "account_id"
            ]
        )


        if (
            amount_cents
            >
            position[
                "available_cents"
            ]
        ):

            flags.append({

                "code":
                    "ALLOCATION_POSITION_EXCEEDED",

                "severity":
                    "high",

                "reason":
                    (
                        "The sending institution "
                        "does not currently hold enough "
                        "of this allocation for the "
                        "requested transfer."
                    ),

                "evidence": {

                    "requested_cents":
                        amount_cents,

                    "available_cents":
                        position[
                            "available_cents"
                        ],

                    "incoming_cents":
                        position[
                            "incoming_cents"
                        ],

                    "outgoing_cents":
                        position[
                            "outgoing_cents"
                        ],

                    "reserved_cents":
                        position[
                            "reserved_cents"
                        ]
                }
            })

        edge = (
            from_account[
                "level"
            ]
            + ">"
            + to_account[
                "level"
            ]
        )

        if (
            edge
            not in allocation.get(
                "allowed_edges",
                []
            )
        ):

            flags.append({

                "code":
                    "ROUTE_OUTSIDE_ALLOCATION",

                "severity":
                    "high",

                "reason":
                    (
                        "Transaction route "
                        "is outside the "
                        "authorised allocation path."
                    ),

                "evidence": {
                    "edge":
                        edge,

                    "allowed_edges":
                        allocation.get(
                            "allowed_edges",
                            []
                        )
                }
            })


        if (
            amount_cents
            >
            allocation[
                "authorised_amount_cents"
            ]
        ):

            flags.append({

                "code":
                    "TRANSFER_EXCEEDS_ALLOCATION",

                "severity":
                    "high",

                "reason":
                    (
                        "This individual transfer "
                        "is larger than the total "
                        "authorised allocation."
                    ),

                "evidence": {
                    "authorised_amount_cents":
                        allocation[
                            "authorised_amount_cents"
                        ],

                    "transfer_amount_cents":
                        amount_cents
                }
            })


        if (
            allocation.get(
                "service_sector"
            )
            and
            service_sector
            != allocation.get(
                "service_sector"
            )
        ):

            flags.append({

                "code":
                    "SERVICE_SCOPE_MISMATCH",

                "severity":
                    "medium",

                "reason":
                    (
                        "Transaction service "
                        "does not match the "
                        "allocation service sector."
                    ),

                "evidence": {
                    "allocation_sector":
                        allocation.get(
                            "service_sector"
                        ),

                    "transaction_sector":
                        service_sector
                }
            })


        allocated_project = (
            allocation.get(
                "project_id"
            )
        )

        if (
            allocated_project
            and
            project_id
            != allocated_project
        ):

            flags.append({

                "code":
                    "PROJECT_SCOPE_MISMATCH",

                "severity":
                    "high",

                "reason":
                    (
                        "Transaction references "
                        "a different project from "
                        "the allocation."
                    ),

                "evidence": {
                    "allocation_project":
                        allocated_project,

                    "transaction_project":
                        project_id
                }
            })


        return flags


    # =============================================
    # INITIATE TRANSFER
    # =============================================

    def initiate_transfer(
        self,
        actor,
        allocation_id,
        from_account_id,
        to_account_id,
        amount_cents,
        purpose,
        service_sector,
        project_id=None,
        public_service=True
    ):

        require_permission(
            actor,
            "govbank.initiate_transfer"
        )

        if amount_cents <= 0:

            raise ValueError(
                "Transfer amount must "
                "be greater than zero."
            )
        
        if (
            from_account_id
            == to_account_id
        ):

            raise ValueError(
                "Sender and recipient accounts "
                "cannot be the same."
            )

        data = self.store.read()

        from_account = (
            self._find_account(
                data,
                from_account_id
            )
        )

        to_account = (
            self._find_account(
                data,
                to_account_id
            )
        )

        allocation = (
            self._find_allocation(
                data,
                allocation_id
            )
        )

        if not self._actor_controls_account(
            actor,
            from_account
        ):

            raise PermissionError(
                "Actor cannot initiate "
                "transactions from this account."
            )

        policy_flags = (
            self.evaluate_transfer(
                data,
                allocation,
                from_account,
                to_account,
                amount_cents,
                service_sector,
                project_id
            )
        )

        transaction_id = (
            "GBT-"
            + uuid4()
            .hex[:12]
            .upper()
        )

        transaction = {

            "transaction_id":
                transaction_id,

            "transaction_type":
                "internal_transfer",

            "allocation_id":
                allocation_id,

            "from_account_id":
                from_account_id,

            "to_account_id":
                to_account_id,

            "amount_cents":
                amount_cents,

            "purpose":
                purpose,

            "service_sector":
                service_sector,

            "project_id":
                project_id,

            "public_service":
                public_service,

            "status":
                (
                    "pending_review"
                    if policy_flags
                    else "pending_approval"
                ),

            "policy_flags":
                policy_flags,

            "initiated_by":
                actor[
                    "actor_id"
                ],

            "approved_by":
                None,

            "created_at":
                now_iso(),

            "posted_at":
                None,

            "previous_hash":
                None,

            "record_hash":
                None
        }

        data[
            "transactions"
        ].append(
            transaction
        )

        self._audit(
            data,
            actor,
            "TRANSFER_INITIATED",
            transaction_id,
            {
                "amount_cents":
                    amount_cents,

                "policy_flag_count":
                    len(
                        policy_flags
                    )
            }
        )

        self.store.write(
            data
        )

        return transaction
    
    # ----------------------------------------------
    # REVIEW TRANSFERS
    # ----------------------------------------------

    def review_transfer(
        self,
        actor,
        transaction_id,
        action,
        reason
    ):

        require_permission(
            actor,
            "govbank.review_transfer"
        )


        allowed_actions = {
            "clear_for_approval",
            "reject",
            "request_correction",
            "request_evidence"
        }


        if action not in allowed_actions:

            raise ValueError(
                "Invalid review action."
            )


        if not reason.strip():

            raise ValueError(
                "A review reason is required."
            )


        data = self.store.read()


        transaction = None


        for item in data.get(
            "transactions",
            []
        ):

            if (
                item.get(
                    "transaction_id"
                )
                == transaction_id
            ):

                transaction = item
                break


        if transaction is None:

            raise LookupError(
                "Transaction not found."
            )


        if (
            transaction.get(
                "status"
            )
            != "pending_review"
        ):

            raise ValueError(
                "Transaction is not "
                "awaiting review."
            )


        # Reviewer should not review
        # their own initiated transaction.

        if (
            transaction.get(
                "initiated_by"
            )
            ==
            actor.get(
                "actor_id"
            )
        ):

            raise PermissionError(
                "The transaction initiator "
                "cannot review the same transaction."
            )


        review_record = {

            "review_id":
                "REV-"
                + uuid4()
                .hex[:10]
                .upper(),

            "reviewer_id":
                actor.get(
                    "actor_id"
                ),

            "action":
                action,

            "reason":
                reason,

            "reviewed_at":
                now_iso(),

            "flags_reviewed":
                transaction.get(
                    "policy_flags",
                    []
                )
        }


        transaction.setdefault(
            "review_history",
            []
        ).append(
            review_record
        )


        if (
            action
            == "clear_for_approval"
        ):

            transaction[
                "status"
            ] = "pending_approval"


        elif (
            action
            == "reject"
        ):

            transaction[
                "status"
            ] = "rejected"


        elif (
            action
            == "request_correction"
        ):

            transaction[
                "status"
            ] = "correction_required"


        elif (
            action
            == "request_evidence"
        ):

            transaction[
                "status"
            ] = "evidence_requested"


        transaction[
            "latest_review"
        ] = review_record


        self._audit(
            data,
            actor,
            "TRANSFER_REVIEWED",
            transaction_id,
            {
                "action":
                    action,

                "reason":
                    reason,

                "flag_count":
                    len(
                        transaction.get(
                            "policy_flags",
                            []
                        )
                    )
            }
        )


        self.store.write(
            data
        )


        return transaction


    # =============================================
    # APPROVE + POST
    # =============================================

    def approve_transfer(
        self,
        actor,
        transaction_id
    ):

        require_permission(
            actor,
            "govbank.approve_transfer"
        )

        data = self.store.read()

        transaction = None

        for item in data.get(
            "transactions",
            []
        ):

            if (
                item.get(
                    "transaction_id"
                )
                == transaction_id
            ):

                transaction = item
                break


        if transaction is None:

            raise LookupError(
                "Transaction not found."
            )


        if (
            transaction.get(
                "status"
            )
            != "pending_approval"
        ):

            raise ValueError(
                "Transaction cannot use normal approval. "
                f"Current status: "
                f"{transaction.get('status')}. "
                "Flagged transactions must go through "
                "the review workflow."
            )


        if (
            transaction.get(
                "initiated_by"
            )
            ==
            actor.get(
                "actor_id"
            )
        ):

            raise PermissionError(
                "Maker-checker control: "
                "the initiator may not "
                "approve the same transfer."
            )


        from_account = (
            self._find_account(
                data,
                transaction[
                    "from_account_id"
                ]
            )
        )

        to_account = (
            self._find_account(
                data,
                transaction[
                    "to_account_id"
                ]
            )
        )


        if not self._actor_controls_account(
            actor,
            from_account
        ):

            raise PermissionError(
                "Approver is not authorised "
                "for the sending institution."
            )


        amount = transaction[
            "amount_cents"
        ]


        if (
            from_account[
                "balance_cents"
            ]
            <
            amount
        ):

            raise ValueError(
                "Insufficient GovBank balance."
            )


        from_account[
            "balance_cents"
        ] -= amount

        to_account[
            "balance_cents"
        ] += amount


        allocation = (
            self._find_allocation(
                data,
                transaction[
                    "allocation_id"
                ]
            )
        )

        allocation[
            "route_movement_cents"
        ] = (
            allocation.get(
                "route_movement_cents",
                0
            )
            +
            amount
        )


        transaction[
            "status"
        ] = "posted"

        transaction[
            "approved_by"
        ] = actor[
            "actor_id"
        ]

        transaction[
            "posted_at"
        ] = now_iso()


        previous_hash = (
            self._previous_hash(
                data
            )
        )

        transaction[
            "previous_hash"
        ] = previous_hash

        transaction[
            "record_hash"
        ] = self._hash_record(
            transaction,
            previous_hash
        )


        self._audit(
            data,
            actor,
            "TRANSFER_POSTED",
            transaction_id,
            {
                "amount_cents":
                    amount
            }
        )


        self.store.write(
            data
        )


        if transaction.get(
            "public_service"
        ):

            self.publish_public_transaction(
                transaction,
                from_account,
                to_account,
                allocation
            )


        return transaction


    # =============================================
    # PUBLICATION TO MALI YA RONA SEED
    # =============================================

    def publish_public_transaction(
        self,
        transaction,
        from_account,
        to_account,
        allocation
    ):

        if not self.public_seed_path.exists():

            raise FileNotFoundError(
                "Mali Ya Rona public "
                "data source was not found."
            )


        with self.public_seed_path.open(
            "r",
            encoding="utf-8"
        ) as file:

            public_data = json.load(
                file
            )


        # It is not live government data.
        # Be transparent about that.
        if (
            public_data.get(
                "source_mode"
            )
            ==
            "synthetic_demo"
        ):

            public_data[
                "source_mode"
            ] = "prototype_simulation"


        public_data[
            "schema_version"
        ] = max(
            3,
            public_data.get(
                "schema_version",
                1
            )
        )


        transactions = (
            public_data.setdefault(
                "govbank_public_transactions",
                []
            )
        )


        public_record = {

            "transaction_id":
                transaction[
                    "transaction_id"
                ],

            "allocation_id":
                transaction[
                    "allocation_id"
                ],

            "project_id":
                transaction.get(
                    "project_id"
                ),

            "from_institution":
                from_account[
                    "name"
                ],

            "from_level":
                from_account[
                    "level"
                ],

            "to_institution":
                to_account[
                    "name"
                ],

            "to_level":
                to_account[
                    "level"
                ],

            "amount_cents":
                transaction[
                    "amount_cents"
                ],

            "service_sector":
                transaction.get(
                    "service_sector"
                ),

            "purpose":
                transaction.get(
                    "purpose"
                ),

            "location_scope":
                allocation.get(
                    "location_scope"
                ),

            "posted_at":
                transaction[
                    "posted_at"
                ],

            "policy_flags":
                transaction.get(
                    "policy_flags",
                    []
                ),

            "source": {
                "kind":
                    "govbank_simulation",

                "mode":
                    "prototype_simulation"
            }
        }


        existing_index = None

        for index, item in enumerate(
            transactions
        ):

            if (
                item.get(
                    "transaction_id"
                )
                ==
                public_record[
                    "transaction_id"
                ]
            ):

                existing_index = index
                break


        if existing_index is None:

            transactions.append(
                public_record
            )

        else:

            transactions[
                existing_index
            ] = public_record


        with self.public_seed_path.open(
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                public_data,
                file,
                indent=2,
                ensure_ascii=False
            )