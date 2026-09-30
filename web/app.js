let dashboardData = null;
let currentFilter = "all";


const moneyFormatter =
    new Intl.NumberFormat(
        "en-ZA",
        {
            style: "currency",
            currency: "ZAR"
        }
    );


function formatMoneyFromCents(cents) {

    return moneyFormatter.format(
        (cents || 0) / 100
    );
}


function severityLabel(
    severity
) {

    if (severity === "high") {
        return "HIGH REVIEW";
    }

    if (severity === "medium") {
        return "MEDIUM REVIEW";
    }

    if (severity === "low") {
        return "LOW REVIEW";
    }

    return "CLEAR";
}


async function loadDashboard() {

    const button =
        document.getElementById(
            "refreshButton"
        );

    button.disabled = true;

    button.textContent =
        "Scanning…";

    try {

        const [
            dashboardResponse,
            flowResponse
        ] = await Promise.all([

            fetch(
                "/api/dashboard"
            ),

            fetch(
                "/api/money-flow"
            )

        ]);


        dashboardData =
            await dashboardResponse.json();

        const flowData =
            await flowResponse.json();


        renderSummary(
            dashboardData
        );

        renderProjects(
            dashboardData.projects
        );

        renderMoneyFlow(
            flowData
        );

    }

    catch (error) {

        console.error(error);

        alert(
            "Could not load monitoring data."
        );

    }

    finally {

        button.disabled = false;

        button.textContent =
            "Rescan external data";
    }
}


function renderSummary(data) {

    const summary =
        data.summary;

    const metadata =
        data.metadata;


    document.getElementById(
        "projectCount"
    ).textContent =
        summary.projects;


    document.getElementById(
        "flagCount"
    ).textContent =
        summary.review_flags;


    document.getElementById(
        "highCount"
    ).textContent =
        summary.high_flags;


    document.getElementById(
        "mediumCount"
    ).textContent =
        summary.medium_flags;


    document.getElementById(
        "clearCount"
    ).textContent =
        summary.clear_projects;


    document.getElementById(
        "modeBadge"
    ).textContent =
        `${metadata.source_mode} • ${metadata.as_of}`;
}


function renderProjects(projects) {

    const grid =
        document.getElementById(
            "projectGrid"
        );

    grid.innerHTML = "";


    const filtered =
        projects.filter(project => {

            if (currentFilter === "all") {
                return true;
            }

            return (
                project.highest_severity
                === currentFilter
            );
        });


    if (filtered.length === 0) {

        grid.innerHTML = `
            <div class="empty-state">
                <strong>No projects match this filter.</strong>
                <p>Try another review category.</p>
            </div>
        `;

        return;
    }


    filtered.forEach(project => {

        const card =
            document.createElement(
                "article"
            );

        card.className =
            `project-card project-card-modern ${project.highest_severity}`;


        const issueCount =
            project.flag_count || 0;


        const findingsHtml =
            issueCount > 0
            ? project.flags
                .slice(0, 2)
                .map(flag => `
                    <div class="issue-item">
                        <div class="issue-rule">
                            ${flag.rule_id}
                        </div>
                        <div class="issue-reason">
                            ${flag.reason}
                        </div>
                    </div>
                `)
                .join("")
            : `
                <div class="clear-state-box">
                    <div class="clear-state-title">
                        No unusualities detected
                    </div>
                    <div class="clear-state-text">
                        This project currently has no review flags under the active rules.
                    </div>
                </div>
            `;


        const reviewState =
            project.highest_severity === "high"
            ? "Needs urgent review"
            : project.highest_severity === "medium"
            ? "Needs review"
            : "No current action";


        card.innerHTML = `

            <div class="case-top-line"></div>

            <div class="case-header">

                <div class="case-community">
                    ${project.community || "Unknown community"}
                </div>

                <div class="case-badge ${project.highest_severity}">
                    ${severityLabel(project.highest_severity)}
                </div>

            </div>


            <h3 class="case-title">
                ${project.name}
            </h3>


            <div class="case-tags">

                <span class="case-tag">
                    Sector: ${project.sector || "-"}
                </span>

                <span class="case-tag">
                    Supplier: ${project.supplier || "Unknown"}
                </span>

                <span class="case-tag">
                    Official status: ${project.official_status || "-"}
                </span>

            </div>


            <div class="case-stats">

                <div class="case-stat">
                    <span class="case-stat-label">
                        Findings
                    </span>
                    <strong class="case-stat-value">
                        ${issueCount}
                    </strong>
                </div>

                <div class="case-stat">
                    <span class="case-stat-label">
                        Review state
                    </span>
                    <strong class="case-stat-value small">
                        ${reviewState}
                    </strong>
                </div>

                <div class="case-stat">
                    <span class="case-stat-label">
                        Institution
                    </span>
                    <strong class="case-stat-value small">
                        ${project.implementing_institution || "-"}
                    </strong>
                </div>

                <div class="case-stat">
                    <span class="case-stat-label">
                        Due date
                    </span>
                    <strong class="case-stat-value small">
                        ${project.due_at || "-"}
                    </strong>
                </div>

            </div>


            <div class="case-findings">

                <div class="case-findings-head">
                    Current findings
                </div>

                ${findingsHtml}

            </div>


            <div class="case-footer">

                <button class="inspect-button">
                    Inspect branch →
                </button>

            </div>
        `;


        card.addEventListener(
            "click",
            () => openProject(project.id)
        );


        grid.appendChild(card);
    });
}


async function openProject(
    projectId
) {

    const response =
        await fetch(
            `/api/projects/${projectId}`
        );

    const data =
        await response.json();


    const branch =
        data.branch;

    const project =
        branch.project;

    const community =
        branch.community || {};

    const supplier =
        branch.supplier || {};


    document.getElementById(
        "detailTitle"
    ).textContent =
        project.name;


    const path =
        document.getElementById(
            "branchPath"
        );


    path.innerHTML = `
        <span class="branch-node">
            ${
                community.name
                || "Community"
            }
        </span>

        <span class="branch-arrow">
            →
        </span>

        <span class="branch-node">
            ${project.name}
        </span>

        <span class="branch-arrow">
            →
        </span>

        <span class="branch-node">
            ${
                supplier.name
                || "Supplier"
            }
        </span>
    `;


    const expenseHtml =
        branch.expenses
        .map(
            expenseBranch => {

                const expense =
                    expenseBranch.expense;

                return `

                    <div
                        class="flag-box none"
                    >

                        <strong>
                            ${expense.invoice_id}
                        </strong>

                        <p>
                            ${
                                expense.quantity
                            }
                            ×
                            ${
                                formatMoneyFromCents(
                                    expense
                                    .unit_price_cents
                                )
                            }
                            per
                            ${expense.unit}
                        </p>

                        <p>
                            Comparable catalogue
                            entries:
                            ${
                                expenseBranch
                                .catalogue_offers
                                .length
                            }
                        </p>

                    </div>

                `;
            }
        )
        .join("");


    const transferHtml =
        branch.transfers.length

        ? branch.transfers.map(
            transfer => `

                <div
                    class="flag-box medium"
                >

                    <strong>
                        ${
                            transfer.reference
                            || transfer.id
                        }
                    </strong>

                    <p>
                        Sent:
                        ${
                            formatMoneyFromCents(
                                transfer
                                .sent_claim_cents
                            )
                        }
                    </p>

                    <p>
                        Received:
                        ${
                            formatMoneyFromCents(
                                transfer
                                .received_claim_cents
                            )
                        }
                    </p>

                </div>

            `
        ).join("")

        : `
            <p>
                No project-level transfers
                recorded.
            </p>
        `;


    const flagHtml =
        data.flags.length

        ? data.flags.map(
            flag => `

                <div
                    class="
                        flag-box
                        ${flag.severity}
                    "
                >

                    <strong>
                        ${flag.rule_id}
                    </strong>

                    <p>
                        ${flag.reason}
                    </p>

                </div>

            `
        ).join("")

        : `

            <div
                class="flag-box none"
            >

                <strong>
                    CLEAR
                </strong>

                <p>
                    No current monitoring rule
                    produced a review flag.
                </p>

            </div>

        `;


    document.getElementById(
        "detailContent"
    ).innerHTML = `

        <div class="detail-grid">


            <div class="detail-section">

                <h3>
                    Project
                </h3>

                <div class="detail-row">
                    <span>
                        Sector
                    </span>

                    <strong>
                        ${project.sector}
                    </strong>
                </div>


                <div class="detail-row">
                    <span>
                        Institution
                    </span>

                    <strong>
                        ${
                            project
                            .implementing_institution
                        }
                    </strong>
                </div>


                <div class="detail-row">
                    <span>
                        Official status
                    </span>

                    <strong>
                        ${
                            project
                            .delivery
                            .official_status
                        }
                    </strong>
                </div>


                <div class="detail-row">
                    <span>
                        Due date
                    </span>

                    <strong>
                        ${
                            project
                            .tender
                            .due_at
                        }
                    </strong>
                </div>

            </div>


            <div class="detail-section">

                <h3>
                    Connected party
                </h3>

                <div class="detail-row">
                    <span>
                        Community
                    </span>

                    <strong>
                        ${
                            community.name
                            || "-"
                        }
                    </strong>
                </div>


                <div class="detail-row">
                    <span>
                        Supplier
                    </span>

                    <strong>
                        ${
                            supplier.name
                            || "-"
                        }
                    </strong>
                </div>


                <div class="detail-row">
                    <span>
                        Supplier verification
                    </span>

                    <strong>
                        ${
                            supplier.verification
                            || "Unknown"
                        }
                    </strong>
                </div>

            </div>


            <div class="detail-section">

                <h3>
                    Expenses
                </h3>

                ${expenseHtml}

            </div>


            <div class="detail-section">

                <h3>
                    Transfers
                </h3>

                ${transferHtml}

            </div>


            <div class="detail-section">

                <h3>
                    Review flags
                </h3>

                ${flagHtml}

            </div>


            <div class="detail-section">

                <h3>
                    Community evidence
                </h3>

                <div class="detail-row">

                    <span>
                        Reports
                    </span>

                    <strong>
                        ${
                            branch
                            .community_reports
                            .length
                        }
                    </strong>

                </div>

                <div class="detail-row">

                    <span>
                        Delivery proof
                    </span>

                    <strong>
                        ${
                            project
                            .delivery
                            .proof_status
                        }
                    </strong>

                </div>

            </div>

        </div>
    `;


    const panel =
        document.getElementById(
            "detailPanel"
        );


    panel.classList.remove(
        "hidden"
    );


    panel.scrollIntoView({
        behavior: "smooth"
    });
}


function createSvgElement(
    type,
    attributes = {}
) {

    const element =
        document.createElementNS(
            "http://www.w3.org/2000/svg",
            type
        );


    Object.entries(
        attributes
    ).forEach(
        ([key, value]) => {

            element.setAttribute(
                key,
                value
            );
        }
    );


    return element;
}


function splitNodeName(
    text
) {

    const words =
        text.split(" ");

    const lines = [
        "",
        ""
    ];


    words.forEach(
        word => {

            if (
                (
                    lines[0]
                    + " "
                    + word
                ).trim().length
                <= 24
            ) {

                lines[0] =
                    (
                        lines[0]
                        + " "
                        + word
                    ).trim();

            }

            else {

                lines[1] =
                    (
                        lines[1]
                        + " "
                        + word
                    ).trim();
            }
        }
    );


    return lines;
}


function renderMoneyFlow(flow) {

    const svg =
        document.getElementById(
            "moneyFlowSvg"
        );

    svg.innerHTML = "";


    if (
        !flow
        || !flow.available
    ) {

        svg.setAttribute(
            "height",
            "120"
        );

        return;
    }


    document.getElementById(
        "flowDate"
    ).textContent =
        `Data date: ${flow.as_of || "-"}`;


    document.getElementById(
        "flowNote"
    ).textContent =
        flow.route_note || "";


    // ==================================================
    // LEVEL NORMALISATION
    // ==================================================

    function normalizeLevel(
        level
    ) {

        const aliases = {

            national:
                "national",

            province:
                "provincial",

            provincial:
                "provincial",

            district:
                "district",

            municipality:
                "local",

            municipal:
                "local",

            metro:
                "local",

            local:
                "local",

            supplier:
                "supplier"

        };


        return (
            aliases[level]
            || level
        );
    }


    const levelOrder = [
        "national",
        "provincial",
        "district",
        "local",
        "supplier"
    ];


    // ==================================================
    // GROUP NODES
    // ==================================================

    const grouped = {};


    flow.nodes.forEach(
        node => {

            const level =
                normalizeLevel(
                    node.level
                );


            if (!grouped[level]) {

                grouped[level] = [];
            }


            grouped[level].push(
                node
            );
        }
    );


    // Keep only levels that actually exist.

    const activeLevels =
        levelOrder.filter(
            level =>
                grouped[level]
                && grouped[level].length
        );


    // Include an unexpected future level instead
    // of silently throwing the node away.

    Object.keys(
        grouped
    ).forEach(
        level => {

            if (
                !activeLevels.includes(
                    level
                )
            ) {

                activeLevels.push(
                    level
                );
            }
        }
    );


    // ==================================================
    // SVG SIZE
    // ==================================================

    const nodeWidth = 210;
    const nodeHeight = 92;

    const columnGap = 130;

    const leftMargin = 55;
    const topMargin = 80;


    const maximumRows =
        Math.max(
            1,
            ...Object.values(
                grouped
            ).map(
                list =>
                    list.length
            )
        );


    const svgWidth =
        Math.max(
            900,
            leftMargin * 2
            +
            activeLevels.length
            * nodeWidth
            +
            (
                activeLevels.length
                - 1
            )
            * columnGap
        );


    const svgHeight =
        Math.max(
            440,
            topMargin * 2
            +
            maximumRows
            * 145
        );


    svg.setAttribute(
        "viewBox",
        `0 0 ${svgWidth} ${svgHeight}`
    );


    svg.setAttribute(
        "width",
        "100%"
    );


    svg.setAttribute(
        "height",
        svgHeight
    );


    // ==================================================
    // NODE POSITIONS
    // ==================================================

    const positions = {};


    activeLevels.forEach(
        (level, columnIndex) => {

            const nodes =
                grouped[level] || [];


            const x =
                leftMargin
                +
                columnIndex
                * (
                    nodeWidth
                    + columnGap
                );


            const spacing =
                svgHeight
                /
                (
                    nodes.length
                    + 1
                );


            nodes.forEach(
                (node, rowIndex) => {

                    positions[
                        node.id
                    ] = {

                        x:
                            x,

                        y:
                            spacing
                            * (
                                rowIndex
                                + 1
                            ),

                        level:
                            level
                    };
                }
            );
        }
    );


    // ==================================================
    // COUNT PARALLEL TRANSFERS
    // ==================================================

    const edgeGroups = {};


    flow.transfers.forEach(
        transfer => {

            const key =
                `${transfer.from_id}__${transfer.to_id}`;


            if (!edgeGroups[key]) {

                edgeGroups[key] = [];
            }


            edgeGroups[key].push(
                transfer
            );
        }
    );


    // ==================================================
    // CONNECTIONS
    // ==================================================

    flow.transfers.forEach(
        (transfer, globalIndex) => {

            const from =
                positions[
                    transfer.from_id
                ];


            const to =
                positions[
                    transfer.to_id
                ];


            if (!from || !to) {

                console.warn(
                    "Money-flow node position missing:",
                    {
                        transfer,
                        from,
                        to,
                        positions
                    }
                );

                return;
            }


            const edgeKey =
                `${transfer.from_id}__${transfer.to_id}`;


            const siblings =
                edgeGroups[
                    edgeKey
                ];


            const siblingIndex =
                siblings.indexOf(
                    transfer
                );


            const siblingCount =
                siblings.length;


            // If multiple transfers connect
            // the same institutions, separate them.

            const parallelOffset =
                (
                    siblingIndex
                    -
                    (
                        siblingCount
                        - 1
                    ) / 2
                )
                * 26;


            const startX =
                from.x
                + nodeWidth;


            const startY =
                from.y
                + parallelOffset;


            const endX =
                to.x;


            const endY =
                to.y
                + parallelOffset;


            const controlDistance =
                Math.max(
                    50,
                    (
                        endX
                        - startX
                    ) / 2
                );


            const pathData =
                `M ${startX} ${startY}
                 C ${startX + controlDistance} ${startY},
                   ${endX - controlDistance} ${endY},
                   ${endX} ${endY}`;


            const isReview =
                transfer.status
                === "review";


            const pathId =
                `money-route-${globalIndex}`;


            // ------------------------------------------
            // Transfer path
            // ------------------------------------------

            const path =
                createSvgElement(
                    "path",
                    {
                        id:
                            pathId,

                        d:
                            pathData,

                        class:
                            isReview
                            ? "flow-link review"
                            : "flow-link"
                    }
                );


            svg.appendChild(
                path
            );


            // ------------------------------------------
            // Amount label
            // ------------------------------------------

            const sentAmount =
                transfer.amount_sent_cents
                ??
                transfer.amount_cents
                ??
                0;


            const labelX =
                (
                    startX
                    + endX
                ) / 2;


            const labelY =
                (
                    startY
                    + endY
                ) / 2
                - 14;


            const amountLabel =
                createSvgElement(
                    "text",
                    {
                        x:
                            labelX,

                        y:
                            labelY,

                        class:
                            isReview
                            ? "flow-amount review"
                            : "flow-amount"
                    }
                );


            amountLabel.textContent =
                formatMoneyFromCents(
                    sentAmount
                );


            svg.appendChild(
                amountLabel
            );


            // ------------------------------------------
            // Purpose label
            // ------------------------------------------

            const purposeLabel =
                createSvgElement(
                    "text",
                    {
                        x:
                            labelX,

                        y:
                            labelY + 15,

                        class:
                            "flow-purpose"
                    }
                );


            purposeLabel.textContent =
                transfer.service_sector
                || transfer.purpose
                || "public service";


            svg.appendChild(
                purposeLabel
            );


            // ------------------------------------------
            // Review label
            // ------------------------------------------

            if (isReview) {

                const reviewLabel =
                    createSvgElement(
                        "text",
                        {
                            x:
                                labelX,

                            y:
                                labelY + 31,

                            class:
                                "flow-review-label"
                        }
                    );


                reviewLabel.textContent =
                    "REVIEW REQUIRED";


                svg.appendChild(
                    reviewLabel
                );
            }


            // ------------------------------------------
            // MOVING MONEY PACKET
            // ------------------------------------------

            function addMovingPacket(
                radius,
                delay,
                duration
            ) {

                const packet =
                    createSvgElement(
                        "circle",
                        {
                            r:
                                radius,

                            class:
                                isReview
                                ? "money-packet review"
                                : "money-packet"
                        }
                    );


                const motion =
                    createSvgElement(
                        "animateMotion",
                        {
                            dur:
                                `${duration}s`,

                            begin:
                                `${delay}s`,

                            repeatCount:
                                "indefinite"
                        }
                    );


                const motionPath =
                    createSvgElement(
                        "mpath",
                        {
                            href:
                                `#${pathId}`
                        }
                    );


                motion.appendChild(
                    motionPath
                );


                packet.appendChild(
                    motion
                );


                svg.appendChild(
                    packet
                );
            }


            addMovingPacket(
                isReview ? 7 : 6,
                globalIndex * 0.3,
                isReview ? 2.3 : 3.0
            );


            addMovingPacket(
                isReview ? 5 : 4,
                1.4 + globalIndex * 0.3,
                isReview ? 2.3 : 3.0
            );
        }
    );


    // ==================================================
    // NODES
    // ==================================================

    flow.nodes.forEach(
        node => {

            const position =
                positions[
                    node.id
                ];


            if (!position) {

                return;
            }


            const group =
                createSvgElement(
                    "g",
                    {
                        class:
                            "flow-node-group"
                    }
                );


            const box =
                createSvgElement(
                    "rect",
                    {
                        x:
                            position.x,

                        y:
                            position.y
                            - nodeHeight / 2,

                        width:
                            nodeWidth,

                        height:
                            nodeHeight,

                        rx:
                            4,

                        class:
                            "flow-node-box"
                    }
                );


            group.appendChild(
                box
            );


            // Level

            const levelText =
                createSvgElement(
                    "text",
                    {
                        x:
                            position.x
                            + 12,

                        y:
                            position.y
                            - 25,

                        class:
                            "flow-node-level"
                    }
                );


            levelText.textContent =
                normalizeLevel(
                    node.level
                );


            group.appendChild(
                levelText
            );


            // Name

            const lines =
                splitNodeName(
                    node.name
                );


            lines.forEach(
                (line, index) => {

                    if (!line) {
                        return;
                    }


                    const text =
                        createSvgElement(
                            "text",
                            {
                                x:
                                    position.x
                                    + 12,

                                y:
                                    position.y
                                    - 4
                                    +
                                    index
                                    * 15,

                                class:
                                    "flow-node-name"
                            }
                        );


                    text.textContent =
                        line;


                    group.appendChild(
                        text
                    );
                }
            );


            // ------------------------------------------
            // Display amount
            // ------------------------------------------

            const received =
                node.funds_in_cents
                || 0;


            const sent =
                node.funds_out_cents
                || 0;


            const displayAmount =
                received > 0
                ? received
                : sent;


            const amount =
                createSvgElement(
                    "text",
                    {
                        x:
                            position.x
                            + 12,

                        y:
                            position.y
                            + 32,

                        class:
                            "flow-node-money"
                    }
                );


            amount.textContent =
                formatMoneyFromCents(
                    displayAmount
                );


            group.appendChild(
                amount
            );


            // Tooltip

            const title =
                createSvgElement(
                    "title"
                );


            title.textContent =
                `${node.name}
Received: ${formatMoneyFromCents(received)}
Sent: ${formatMoneyFromCents(sent)}`;


            group.appendChild(
                title
            );


            svg.appendChild(
                group
            );
        }
    );
}


document
.getElementById(
    "refreshButton"
)
.addEventListener(
    "click",
    loadDashboard
);


document
.getElementById(
    "closeDetail"
)
.addEventListener(
    "click",
    () => {

        document
        .getElementById(
            "detailPanel"
        )
        .classList.add(
            "hidden"
        );
    }
);


document
.querySelectorAll(
    ".filter"
)
.forEach(
    button => {

        button.addEventListener(
            "click",
            () => {

                document
                .querySelectorAll(
                    ".filter"
                )
                .forEach(
                    item =>
                        item
                        .classList
                        .remove(
                            "active"
                        )
                );


                button
                .classList
                .add(
                    "active"
                );


                currentFilter =
                    button.dataset.filter;


                renderProjects(
                    dashboardData.projects
                );
            }
        );
    }
);


loadDashboard();