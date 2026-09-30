#note : ROLE_PERMISSIONS first session

PREFIX_BY_PROFILE = {

    "national_official":
        "N",

    "provincial_official":
        "P",

    "district_official":
        "D",

    "municipal_official":
        "M",

    "councillor":
        "C",

    "citizen":
        "R",

    "supplier":
        "S"
}


ROLE_PERMISSIONS = {

    #-------------------------------------
    #WILL NAME THIS ONE LATER COS EISH (THE )
    #-------------------------------------

    "public_finance_reviewer": {
        "govbank.review_transfer",
        "finance.view_national",
        "system.audit"
    },

    # -------------------------------------
    # NATIONAL
    # -------------------------------------

    "national_funding_officer": {
        "govbank.receive_funds",
        "govbank.create_allocation",
        "govbank.initiate_transfer",
        "finance.view_national"
    },

    "national_finance_approver": {
        "govbank.approve_transfer",
        "finance.view_national"
    },


    # -------------------------------------
    # PROVINCIAL
    # -------------------------------------

    "provincial_finance_officer": {
        "govbank.initiate_transfer",
        "finance.view_province"
    },

    "provincial_finance_approver": {
        "govbank.approve_transfer",
        "finance.view_province"
    },


    # -------------------------------------
    # DISTRICT
    # -------------------------------------

    "district_finance_officer": {
        "govbank.initiate_transfer",
        "finance.view_district"
    },

    "district_finance_approver": {
        "govbank.approve_transfer",
        "finance.view_district"
    },


    # -------------------------------------
    # MUNICIPALITY
    # -------------------------------------

    "municipal_finance_officer": {
        "govbank.initiate_transfer",
        "finance.view_municipality"
    },

    "municipal_manager": {
        "govbank.approve_transfer",
        "finance.view_municipality",
        "ticket.manage",
        "service.update"
    },

    "municipal_project_officer": {
        "service.update",
        "delivery.record",
        "ticket.respond"
    },

    "municipal_scm_officer": {
        "procurement.manage",
        "supplier.review"
    },


    # -------------------------------------
    # COUNCILLOR
    # -------------------------------------

    "ward_councillor": {
        "public.view",
        "ticket.view_ward",
        "ticket.escalate",
        "ticket.follow_up"
    },


    # -------------------------------------
    # CITIZEN
    # -------------------------------------

    "citizen": {
        "public.view",
        "feedback.submit",
        "ticket.submit",
        "ticket.view_own"
    },


    # -------------------------------------
    # SUPPLIER
    # -------------------------------------

    "supplier": {
        "supplier.view_own",
        "evidence.upload",
        "flag.respond"
    },


    # -------------------------------------
    # PLATFORM ADMIN
    # Does NOT automatically receive
    # public-finance payment powers.
    # -------------------------------------

    "platform_admin": {
        "registry.manage",
        "system.audit"
    }
}


def actor_permissions(
    actor
):

    role = actor.get(
        "role"
    )

    permissions = set(
        ROLE_PERMISSIONS.get(
            role,
            set()
        )
    )

    permissions.update(
        actor.get(
            "granted_permissions",
            []
        )
    )

    permissions.difference_update(
        actor.get(
            "revoked_permissions",
            []
        )
    )

    return permissions


def has_permission(
    actor,
    permission
):

    return (
        permission
        in actor_permissions(
            actor
        )
    )


def require_permission(
    actor,
    permission
):

    if not has_permission(
        actor,
        permission
    ):

        raise PermissionError(
            f"Actor {actor.get('actor_id')} "
            f"does not have permission: "
            f"{permission}"
        )


def prefix_matches_profile(
    actor
):

    profile_type = actor.get(
        "profile_type"
    )

    expected_prefix = (
        PREFIX_BY_PROFILE.get(
            profile_type
        )
    )

    if not expected_prefix:
        return False

    actor_id = actor.get(
        "actor_id",
        ""
    )

    return actor_id.startswith(
        expected_prefix + "-"
    )