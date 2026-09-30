let bankData = null;
let actors = [];
let currentActorId = "";


const money = new Intl.NumberFormat(
    "en-ZA",
    {
        style: "currency",
        currency: "ZAR"
    }
);


function centsToMoney(
    cents
) {

    return money.format(
        (cents || 0) / 100
    );
}


async function getJson(
    url,
    options = {}
) {

    const response =
        await fetch(
            url,
            options
        );


    const body =
        await response.json();


    if (!response.ok) {

        throw new Error(
            body.detail
            || "Request failed."
        );
    }


    return body;
}


function showMessage(
    text,
    isError = false
) {

    const box =
        document.getElementById(
            "messageBox"
        );


    box.textContent =
        text;


    box.classList.remove(
        "hidden",
        "error"
    );


    if (isError) {

        box.classList.add(
            "error"
        );
    }


    box.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });
}


async function loadActors() {

    const result =
        await getJson(
            "/api/registry/actors"
        );


    actors =
        result.actors || [];


    const select =
        document.getElementById(
            "actorSelect"
        );


    select.innerHTML = `
        <option value="">
            Select an official…
        </option>
    `;


    actors.forEach(
        actor => {

            /*
            Citizen and supplier profiles
            will get their own portals later.
            For this GovBank page we show
            official actors.
            */

            if (
                actor.profile_type
                === "citizen"
            ) {
                return;
            }


            const option =
                document.createElement(
                    "option"
                );


            option.value =
                actor.actor_id;


            option.textContent =
                `${actor.display_name}
                 — ${actor.role}`;


            select.appendChild(
                option
            );
        }
    );
}


function updateActorDetails() {

    currentActorId =
        document.getElementById(
            "actorSelect"
        ).value;


    const box =
        document.getElementById(
            "actorDetails"
        );


    const actor =
        actors.find(
            item =>
                item.actor_id
                === currentActorId
        );


    if (!actor) {

        box.textContent =
            "No official selected";

        return;
    }


    box.innerHTML = `

        <strong>
            ${actor.display_name}
        </strong>

        <br>

        Credential:
        ${actor.actor_id}

        <br>

        Role:
        ${actor.role}

        <br>

        Institution:
        ${actor.institution_id || "—"}

    `;
}


async function loadBank() {

    bankData =
        await getJson(
            "/api/govbank"
        );


    renderAccounts();

    populateAccountMenus();

    populateAllocations();

    renderPending();

    renderReviews();

    renderTransactions();
}


function renderAccounts() {

    const grid =
        document.getElementById(
            "accountGrid"
        );


    grid.innerHTML = "";


    bankData.accounts.forEach(
        account => {

            const card =
                document.createElement(
                    "article"
                );


            card.className =
                "account-card";


            card.innerHTML = `

                <span
                    class="account-level"
                >
                    ${account.level}
                </span>

                <h3>
                    ${account.name}
                </h3>

                <div
                    class="account-balance"
                >
                    ${
                        centsToMoney(
                            account.balance_cents
                        )
                    }
                </div>

                <div
                    class="account-id"
                >
                    ${account.account_id}
                </div>

            `;


            grid.appendChild(
                card
            );
        }
    );
}


function fillAccountSelect(
    id
) {

    const select =
        document.getElementById(
            id
        );


    select.innerHTML = "";


    bankData.accounts.forEach(
        account => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                account.account_id;


            option.textContent =
                `${account.name}
                (${centsToMoney(
                    account.balance_cents
                )})`;


            select.appendChild(
                option
            );
        }
    );
}


function populateAccountMenus() {

    [
        "receiptAccount",
        "allocationSource",
        "transferFrom",
        "transferTo"
    ].forEach(
        fillAccountSelect
    );
}


function populateAllocations() {

    const select =
        document.getElementById(
            "transferAllocation"
        );


    select.innerHTML = "";


    if (
        bankData.allocations.length
        === 0
    ) {

        const option =
            document.createElement(
                "option"
            );


        option.value = "";

        option.textContent =
            "Create an allocation first";


        select.appendChild(
            option
        );


        return;
    }


    bankData.allocations.forEach(
        allocation => {

            const option =
                document.createElement(
                    "option"
                );


            option.value =
                allocation.allocation_id;


            option.textContent =
                `${allocation.title}
                — ${
                    centsToMoney(
                        allocation
                        .authorised_amount_cents
                    )
                }`;


            select.appendChild(
                option
            );
        }
    );
}

function renderReviews() {

    const holder =
        document.getElementById(
            "reviewTransfers"
        );


    const badge =
        document.getElementById(
            "reviewCountBadge"
        );


    const reviews =
        bankData.transactions.filter(
            transaction =>
                transaction.status
                === "pending_review"
        );


    badge.textContent =
        `${reviews.length}
        awaiting review`;


    holder.innerHTML = "";


    if (
        reviews.length === 0
    ) {

        holder.innerHTML = `

            <div class="review-empty">

                No transactions currently
                require review.

            </div>
        `;

        return;
    }


    reviews.forEach(
        transaction => {

            const flags =
                transaction.policy_flags
                || [];


            const flagHtml =
                flags.map(
                    flag => `

                        <div
                            class="review-flag-box"
                        >

                            <span
                                class="review-flag-code"
                            >
                                ${
                                    flag.code
                                    || "REVIEW"
                                }
                            </span>

                            <div
                                class="review-flag-reason"
                            >
                                ${
                                    flag.reason
                                    || "Transaction requires review."
                                }
                            </div>

                        </div>

                    `
                )
                .join("");


            const card =
                document.createElement(
                    "article"
                );


            card.className =
                "review-card";


            card.innerHTML = `

                <div
                    class="review-header"
                >

                    <div>

                        <span
                            class="review-reference"
                        >
                            ${
                                transaction.transaction_id
                            }
                        </span>

                        <h3>
                            ${
                                transaction.purpose
                                ||
                                "Public finance transfer"
                            }
                        </h3>

                    </div>


                    <div
                        class="review-amount"
                    >
                        ${
                            centsToMoney(
                                transaction.amount_cents
                            )
                        }
                    </div>

                </div>


                <div
                    class="review-route"
                >

                    <span>
                        ${
                            accountName(
                                transaction
                                .from_account_id
                            )
                        }
                    </span>


                    <span
                        class="review-route-arrow"
                    >
                        →
                    </span>


                    <span>
                        ${
                            accountName(
                                transaction
                                .to_account_id
                            )
                        }
                    </span>

                </div>


                <div>

                    <strong>
                        Algorithm findings
                    </strong>

                </div>


                <div
                    class="review-flags"
                >
                    ${flagHtml}
                </div>


                <div
                    class="review-form"
                >

                    <textarea
                        class="review-reason"
                        placeholder="
Explain the review decision.
Example:
Wrong destination selected by user.
Transaction should be corrected before approval.
                        "
                    ></textarea>


                    <div
                        class="review-actions"
                    >

                        <button
                            class="
                                review-action
                                clear
                            "
                            data-action=
                                "clear_for_approval"
                        >
                            Clear for approval
                        </button>


                        <button
                            class="
                                review-action
                                reject
                            "
                            data-action=
                                "reject"
                        >
                            Reject
                        </button>


                        <button
                            class="
                                review-action
                                correction
                            "
                            data-action=
                                "request_correction"
                        >
                            Request correction
                        </button>


                        <button
                            class="
                                review-action
                                evidence
                            "
                            data-action=
                                "request_evidence"
                        >
                            Request evidence
                        </button>

                    </div>

                </div>

            `;


            card
            .querySelectorAll(
                ".review-action"
            )
            .forEach(
                button => {

                    button.addEventListener(
                        "click",
                        () => {

                            const reason =
                                card
                                .querySelector(
                                    ".review-reason"
                                )
                                .value;


                            reviewTransaction(
                                transaction
                                .transaction_id,

                                button
                                .dataset
                                .action,

                                reason
                            );
                        }
                    );
                }
            );


            holder.appendChild(
                card
            );
        }
    );
}

function renderPending() {

    const holder =
        document.getElementById(
            "pendingTransfers"
        );


    holder.innerHTML = "";


    const pending =
        bankData.transactions.filter(
            transaction =>
                transaction.status
                === "pending_approval"
        );


    if (
        pending.length === 0
    ) {

        holder.innerHTML = `
            <p>
                No transactions currently
                require approval.
            </p>
        `;

        return;
    }


    pending.forEach(
        transaction => {

            const card =
                document.createElement(
                    "div"
                );


            card.className =
                "pending-card";


            card.innerHTML = `

                <div>

                    <strong>
                        ${transaction.transaction_id}
                    </strong>

                    <p>
                        ${
                            transaction.from_account_id
                        }
                        →
                        ${
                            transaction.to_account_id
                        }
                    </p>

                    <p>
                        ${
                            centsToMoney(
                                transaction.amount_cents
                            )
                        }
                        •
                        ${transaction.purpose}
                    </p>

                    <p>
                        Initiated by:
                        ${
                            transaction.initiated_by
                        }
                    </p>

                </div>


                <button
                    class="approve-button"
                >
                    Approve transaction
                </button>

            `;


            card
            .querySelector(
                ".approve-button"
            )
            .addEventListener(
                "click",
                () =>
                    approveTransaction(
                        transaction.transaction_id
                    )
            );


            holder.appendChild(
                card
            );
        }
    );
}


function accountName(
    accountId
) {

    if (!accountId) {
        return "External source";
    }


    const account =
        bankData.accounts.find(
            item =>
                item.account_id
                === accountId
        );


    return (
        account
        ? account.name
        : accountId
    );
}


function renderTransactions() {

    const body =
        document.getElementById(
            "transactionTable"
        );


    body.innerHTML = "";


    const transactions =
        [...bankData.transactions]
        .reverse();


    transactions.forEach(
        transaction => {

            const row =
                document.createElement(
                    "tr"
                );


            const flags =
                transaction.policy_flags
                || [];


            row.innerHTML = `

                <td>
                    ${transaction.transaction_id}
                </td>

                <td>
                    ${transaction.transaction_type}
                </td>

                <td>
                    ${
                        accountName(
                            transaction.from_account_id
                        )
                    }
                </td>

                <td>
                    ${
                        accountName(
                            transaction.to_account_id
                        )
                    }
                </td>

                <td>
                    ${
                        centsToMoney(
                            transaction.amount_cents
                        )
                    }
                </td>

                <td>

                    <span
                        class="
                            status-pill
                            ${
                                transaction.status
                                === "posted"
                                ? "status-posted"
                                : "status-pending"
                            }
                        "
                    >
                        ${transaction.status}
                    </span>

                </td>

                <td>

                    ${
                        flags.length
                        ? `
                            <span
                                class="review-flag"
                            >
                                ${flags.length}
                                review flag(s)
                            </span>
                        `
                        : `
                            <span
                                class="no-review"
                            >
                                No flag
                            </span>
                        `
                    }

                </td>

            `;


            body.appendChild(
                row
            );
        }
    );
}


function requireActor() {

    if (!currentActorId) {

        showMessage(
            "Select an acting official first.",
            true
        );

        return false;
    }


    return true;
}


async function receiveFunds() {

    if (!requireActor()) {
        return;
    }


    try {

        await getJson(
            "/api/govbank/funding-receipts",
            {
                method:
                    "POST",

                headers: {
                    "Content-Type":
                        "application/json",

                    "X-Actor-ID":
                        currentActorId
                },

                body:
                    JSON.stringify({

                        account_id:
                            document
                            .getElementById(
                                "receiptAccount"
                            )
                            .value,

                        amount_rand:
                            document
                            .getElementById(
                                "receiptAmount"
                            )
                            .value,

                        source_name:
                            document
                            .getElementById(
                                "receiptSource"
                            )
                            .value,

                        source_reference:
                            document
                            .getElementById(
                                "receiptReference"
                            )
                            .value
                    })
            }
        );


        showMessage(
            "Funding receipt posted successfully."
        );


        await loadBank();

    }

    catch (error) {

        showMessage(
            error.message,
            true
        );
    }
}


async function createAllocation() {

    if (!requireActor()) {
        return;
    }


    try {

        const result =
            await getJson(
                "/api/govbank/allocations",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "X-Actor-ID":
                            currentActorId
                    },

                    body:
                        JSON.stringify({

                            source_account_id:
                                document
                                .getElementById(
                                    "allocationSource"
                                )
                                .value,

                            title:
                                document
                                .getElementById(
                                    "allocationTitle"
                                )
                                .value,

                            amount_rand:
                                document
                                .getElementById(
                                    "allocationAmount"
                                )
                                .value,

                            service_sector:
                                document
                                .getElementById(
                                    "allocationSector"
                                )
                                .value,

                            location_scope:
                                document
                                .getElementById(
                                    "allocationLocation"
                                )
                                .value,

                            allowed_edges: [
                                "national>province",
                                "province>district",
                                "district>municipality",
                                "national>municipality",
                                "municipality>supplier"
                            ],

                            project_id:
                                null
                        })
                }
            );


        showMessage(
            `Allocation created:
            ${result.allocation_id}`
        );


        await loadBank();

    }

    catch (error) {

        showMessage(
            error.message,
            true
        );
    }
}


async function sendTransfer() {

    if (!requireActor()) {
        return;
    }


    const allocationId =
        document
        .getElementById(
            "transferAllocation"
        )
        .value;


    if (!allocationId) {

        showMessage(
            "Create an allocation first.",
            true
        );

        return;
    }


    try {

        const result =
            await getJson(
                "/api/govbank/transfers",
                {
                    method:
                        "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "X-Actor-ID":
                            currentActorId
                    },

                    body:
                        JSON.stringify({

                            allocation_id:
                                allocationId,

                            from_account_id:
                                document
                                .getElementById(
                                    "transferFrom"
                                )
                                .value,

                            to_account_id:
                                document
                                .getElementById(
                                    "transferTo"
                                )
                                .value,

                            amount_rand:
                                document
                                .getElementById(
                                    "transferAmount"
                                )
                                .value,

                            purpose:
                                document
                                .getElementById(
                                    "transferPurpose"
                                )
                                .value,

                            service_sector:
                                document
                                .getElementById(
                                    "transferSector"
                                )
                                .value,

                            project_id:
                                null,

                            public_service:
                                true
                        })
                }
            );


        const flagCount =
            (
                result.policy_flags
                || []
            ).length;


        showMessage(
            flagCount
            ? `Transfer created with
               ${flagCount}
               review flag(s).`
            : "Transfer created and awaiting approval."
        );


        await loadBank();

    }

    catch (error) {

        showMessage(
            error.message,
            true
        );
    }
}

async function reviewTransaction(
    transactionId,
    action,
    reason
) {

    if (!requireActor()) {
        return;
    }


    if (
        !reason
        || !reason.trim()
    ) {

        showMessage(
            "Write a review explanation first.",
            true
        );

        return;
    }


    try {

        const result =
            await getJson(

                `/api/govbank/transfers/${transactionId}/review`,

                {
                    method:
                        "POST",

                    headers: {

                        "Content-Type":
                            "application/json",

                        "X-Actor-ID":
                            currentActorId
                    },

                    body:
                        JSON.stringify({

                            action:
                                action,

                            reason:
                                reason
                        })
                }
            );


        showMessage(
            `Review completed.
             New status:
             ${result.status}`
        );


        await loadBank();

    }

    catch (error) {

        showMessage(
            error.message,
            true
        );
    }
}


async function approveTransaction(
    transactionId
) {

    if (!requireActor()) {
        return;
    }


    try {

        await getJson(

            `/api/govbank/transfers/${transactionId}/approve`,

            {
                method:
                    "POST",

                headers: {
                    "X-Actor-ID":
                        currentActorId
                }
            }
        );


        showMessage(
            "Transaction approved and posted."
        );


        await loadBank();

    }

    catch (error) {

        showMessage(
            error.message,
            true
        );
    }
}


document
.getElementById(
    "actorSelect"
)
.addEventListener(
    "change",
    updateActorDetails
);


document
.getElementById(
    "receiveFundsButton"
)
.addEventListener(
    "click",
    receiveFunds
);


document
.getElementById(
    "createAllocationButton"
)
.addEventListener(
    "click",
    createAllocation
);


document
.getElementById(
    "sendTransferButton"
)
.addEventListener(
    "click",
    sendTransfer
);


document
.getElementById(
    "refreshBank"
)
.addEventListener(
    "click",
    loadBank
);


async function start() {

    try {

        await loadActors();

        await loadBank();

    }

    catch (error) {

        showMessage(
            error.message,
            true
        );
    }
}


start();