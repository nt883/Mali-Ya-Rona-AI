def build_govbank_graph(
    public_data
):
    """
    Converts published GovBank transactions
    into the format used by the Mali Ya Rona
    visual funding graph.
    """

    transactions = public_data.get(
        "govbank_public_transactions",
        []
    )


    if not transactions:

        return {
            "available": False,
            "source": "govbank",
            "nodes": [],
            "transfers": []
        }


    node_map = {}

    transfers = []


    for transaction in transactions:

        from_name = transaction.get(
            "from_institution"
        )

        to_name = transaction.get(
            "to_institution"
        )

        from_level = transaction.get(
            "from_level"
        )

        to_level = transaction.get(
            "to_level"
        )


        from_id = (
            f"{from_level}:"
            f"{from_name}"
        )

        to_id = (
            f"{to_level}:"
            f"{to_name}"
        )


        if from_id not in node_map:

            node_map[from_id] = {

                "id":
                    from_id,

                "name":
                    from_name,

                "level":
                    from_level,

                "funds_in_cents":
                    0,

                "funds_out_cents":
                    0
            }


        if to_id not in node_map:

            node_map[to_id] = {

                "id":
                    to_id,

                "name":
                    to_name,

                "level":
                    to_level,

                "funds_in_cents":
                    0,

                "funds_out_cents":
                    0
            }


        amount = transaction.get(
            "amount_cents",
            0
        )


        node_map[to_id][
            "funds_in_cents"
        ] += amount

        node_map[from_id][
            "funds_out_cents"
        ] += amount

        policy_flags = transaction.get(
            "policy_flags",
            []
        )


        transfers.append({

            "id":
                transaction.get(
                    "transaction_id"
                ),

            "from_id":
                from_id,

            "to_id":
                to_id,

            "amount_sent_cents":
                amount,

            "amount_received_cents":
                amount,

            "allocation_id":
                transaction.get(
                    "allocation_id"
                ),

            "project_id":
                transaction.get(
                    "project_id"
                ),

            "service_sector":
                transaction.get(
                    "service_sector"
                ),

            "purpose":
                transaction.get(
                    "purpose"
                ),

            "policy_flags":
                policy_flags,

            "status":
                (
                    "review"
                    if policy_flags
                    else "matched"
                )
        })


    return {

        "available":
            True,

        "source":
            "govbank",

        "title":
            "GovBank public finance route",

        "currency":
            "ZAR",

        "nodes":
            list(
                node_map.values()
            ),

        "transfers":
            transfers
    }