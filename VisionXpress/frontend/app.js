const state = {
    token: localStorage.getItem("vx_token") || "",
    user: JSON.parse(localStorage.getItem("vx_user") || "null"),
    page: "dashboard",
    planningDate: localStorage.getItem("vx_date") || "2026-09-01",
    blocks: [],
    requests: []
};

const $ = (selector) => document.querySelector(selector);
const main = $("#main-view");

async function api(path, options = {}) {
    const headers = options.headers ? { ...options.headers } : {};

    if (state.token) {
        headers.Authorization = `Bearer ${state.token}`;
    }

    if (
        !(options.body instanceof FormData) &&
        options.body !== undefined
    ) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(path, {
        ...options,
        headers
    });

    const text = await response.text();

    let data = {};

    try {
        data = text ? JSON.parse(text) : {};
    } catch {
        data = {
            detail: text
        };
    }

    if (response.status === 401) {
        logout(false);
    }

    if (!response.ok) {
        throw Object.assign(
            new Error(
                data.detail || "Request failed"
            ),
            {
                status: response.status,
                data
            }
        );
    }

    return data;
}

function toast(message, type = "info") {
    const root = $("#toast-root");

    if (!root) {
        return;
    }

    const el = document.createElement("div");

    el.className = `toast ${type}`;
    el.textContent = message;

    root.appendChild(el);

    setTimeout(
        () => el.remove(),
        3200
    );
}

function fmt(value) {
    return (
        value == null ||
        value === ""
    )
        ? "Not provided"
        : String(value);
}

function escapeHtml(value) {
    return String(value ?? "").replace(
        /[&<>'"]/g,
        (c) => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            "'": "&#39;",
            '"': "&quot;"
        }[c])
    );
}

function priorityClass(priority = "LOW") {
    return String(priority).toLowerCase();
}

function initials(text) {
    return String(text || "VX")
        .slice(0, 2)
        .toUpperCase();
}

function showApp() {
    $("#login-view").classList.add("hidden");
    $("#app-view").classList.remove("hidden");

    $("#user-name").textContent =
        state.user.user_id;

    $("#user-department").textContent =
        state.user.department;

    $("#user-avatar").textContent =
        initials(state.user.department);

    $("#planning-date").value =
        state.planningDate;

    buildNav();
    renderPage();
    refreshNotifications();
}

function showLogin() {
    $("#app-view").classList.add("hidden");
    $("#login-view").classList.remove("hidden");
}

function logout(server = true) {
    if (server) {
        api(
            "/api/auth/logout",
            {
                method: "POST"
            }
        ).catch(() => {});
    }

    state.token = "";
    state.user = null;

    localStorage.removeItem("vx_token");
    localStorage.removeItem("vx_user");

    showLogin();
}

function updateWorkflowVisibility() {
    const workflow =
        $("#dashboard-workflow");

    if (!workflow) {
        return;
    }

    workflow.style.display =
        state.page === "dashboard"
            ? ""
            : "none";
}

function buildNav() {
    if (!state.user) {
        return;
    }

    const department =
        state.user.department;

    const items = [
        ["dashboard", "Dashboard"]
    ];

    if (
        ["TMS", "TDMS", "SMMS"]
            .includes(department)
    ) {
        items.push(
            ["submit", "Submit Request"],
            ["track", "Track Request"]
        );
    }

    if (department === "COA") {
        items.push(
            ["coa", "COA Schedule"]
        );
    }

    if (
        department === "TDMS" ||
        department === "BDMS"
    ) {
        items.push(
            ["blocks", "Block Dashboard"]
        );
    }

    if (department === "BDMS") {
        items.push(
            ["approvals", "BDMS Approvals"]
        );
    }

    items.push(
        ["notifications", "Alerts"]
    );

    $("#nav-menu").innerHTML =
        items
            .map(
                ([id, label]) =>
                    `
                    <button
                        class="nav-item ${
                            state.page === id
                                ? "active"
                                : ""
                        }"
                        data-page="${id}"
                    >
                        ${label}
                    </button>
                    `
            )
            .join("");

    document
        .querySelectorAll(".nav-item")
        .forEach(
            (button) => {
                button.onclick = () => {
                    state.page =
                        button.dataset.page;

                    buildNav();
                    renderPage();
                };
            }
        );
}

async function renderPage() {
    const labels = {
        dashboard: "CONTROL CENTER",
        submit: "MAINTENANCE REQUEST",
        track: "REQUEST TRACKING",
        coa: "COA OPERATIONS",
        blocks: "BLOCK CONTROL",
        approvals: "BDMS DECISION DESK",
        notifications: "NOTIFICATIONS"
    };

    $("#page-kicker").textContent =
        labels[state.page] ||
        "CONTROL CENTER";

    $("#page-title").textContent =
        state.page === "dashboard"
            ? "Dashboard"
            : (
                state.page.charAt(0).toUpperCase() +
                state.page.slice(1)
            );

    updateWorkflowVisibility();

    main.innerHTML = `
        <div class="loading">
            Loading control view…
        </div>
    `;

    try {
        if (state.page === "dashboard") {
            return await renderDashboard();
        }

        if (state.page === "submit") {
            return renderSubmit();
        }

        if (state.page === "track") {
            return renderTrack();
        }

        if (state.page === "coa") {
            return await renderCOA();
        }

        if (state.page === "blocks") {
            return await renderBlocks();
        }

        if (state.page === "approvals") {
            return await renderApprovals();
        }

        if (state.page === "notifications") {
            return await renderNotifications();
        }
    } catch (error) {
        main.innerHTML = `
            <div class="panel">
                <div
                    class="danger-text"
                    style="padding:20px"
                >
                    ${escapeHtml(error.message)}
                </div>
            </div>
        `;
    }
}

async function renderDashboard() {
    const data = await api(
        `/api/dashboard?planning_date=${state.planningDate}`
    );

    const blocks = data.blocks || [];
    const requests = data.requests || [];

    state.blocks = blocks;
    state.requests = requests;

    main.innerHTML = `
        <div class="stats-grid">

            <div class="stat-card">
                <div class="label">
                    Planning date
                </div>

                <div
                    class="value"
                    style="font-size:19px"
                >
                    ${escapeHtml(
                        state.planningDate
                    )}
                </div>

                <div class="hint">
                    Active control window
                </div>
            </div>


            <div class="stat-card">
                <div class="label">
                    Recommended blocks
                </div>

                <div class="value">
                    ${
                        blocks.filter(
                            (block) =>
                                block.status ===
                                    "PENDING_APPROVAL" ||
                                block.status ===
                                    "RECOMMENDED"
                        ).length
                    }
                </div>

                <div class="hint">
                    Awaiting decision
                </div>
            </div>


            <div class="stat-card">
                <div class="label">
                    Approved
                </div>

                <div class="value">
                    ${
                        blocks.filter(
                            (block) =>
                                block.status ===
                                "APPROVED"
                        ).length
                    }
                </div>

                <div class="hint">
                    Confirmed blocks
                </div>
            </div>


            <div class="stat-card">
                <div class="label">
                    Tasks
                </div>

                <div class="value">
                    ${
                        data.scheduled_tasks ||
                        0
                    }
                </div>

                <div class="hint">
                    In current workflow
                </div>
            </div>


            <div class="stat-card">
                <div class="label">
                    System status
                </div>

                <div
                    class="value success-text"
                    style="font-size:19px"
                >
                    SAFE
                </div>

                <div class="hint">
                    0 known resource conflicts
                </div>
            </div>

        </div>


        <div
            class="two-col"
            style="margin-top:16px"
        >

            <section class="panel">

                <div class="section-title">

                    <h3>
                        ${
                            state.user.department ===
                            "TDMS"

                                ? "Recommended maintenance blocks"

                                : "Your request activity"
                        }
                    </h3>

                    <span>
                        ${
                            state.user.department ===
                            "TDMS"

                                ? "Sorted by urgency"

                                : "Latest activity"
                        }
                    </span>

                </div>

                ${
                    state.user.department === "TDMS"
                        ? renderBlockCards(
                            blocks.slice(0, 8),
                            true
                        )
                        : renderRequestCards(
                            requests.slice(0, 8)
                        )
                }

            </section>


            <section class="panel">

                <div class="section-title">

                    <h3>
                        Quick actions
                    </h3>

                    <span>
                        Operator shortcuts
                    </span>

                </div>

                ${quickActions()}

            </section>

        </div>
    `;
}

function quickActions() {
    const department =
        state.user.department;

    if (
        [
            "TMS",
            "TDMS",
            "SMMS"
        ].includes(department)
    ) {
        return `
        <div class="block-list">

            <button
                class="primary wide"
                onclick="go('submit')"
            >
                Submit maintenance request
            </button>

            <button
                class="secondary wide"
                onclick="go('track')"
            >
                Track a request by Task ID
            </button>

            ${
                department === "TDMS"
                    ? `
                    <button
                        class="secondary wide"
                        onclick="go('blocks')"
                    >
                        Open block dashboard
                    </button>
                    `
                    : ""
            }

        </div>
        `;
    }

    if (department === "COA") {
        return `
        <div class="block-list">

            <button
                class="primary wide"
                onclick="go('coa')"
            >
                Upload COA schedule
            </button>

            <button
                class="secondary wide"
                onclick="go('notifications')"
            >
                View block alerts
            </button>

        </div>
        `;
    }

    return `
    <div class="block-list">

        <button
            class="primary wide"
            onclick="loadDemo()"
        >
            Load synthetic demo data
        </button>

        <button
            class="primary wide"
            onclick="generatePlan()"
        >
            Generate / refresh block plan
        </button>

        <button
            class="secondary wide"
            onclick="go('approvals')"
        >
            Open pending approvals
        </button>

        <button
            class="secondary wide"
            onclick="go('blocks')"
        >
            Review all blocks
        </button>

    </div>
    `;
}

function go(page) {
    state.page = page;
    buildNav();
    renderPage();
}

function renderBlockCards(
    blocks,
    canReview = false
) {
    if (!blocks.length) {
        return `
        <div class="empty">
            No blocks available for this
            planning date.
        </div>
        `;
    }

    return `
    <div class="block-list">

        ${
            blocks
                .map(
                    (block) =>
                        `
                        <div class="block-card">

                            <div class="block-main">

                                <div class="block-top">

                                    <span
                                        class="
                                            pill
                                            ${priorityClass(
                                                block.priority
                                            )}
                                        "
                                    >
                                        ${escapeHtml(
                                            block.priority
                                        )}
                                    </span>

                                    <span class="pill">
                                        ${escapeHtml(
                                            String(
                                                block.status
                                            ).replaceAll(
                                                "_",
                                                " "
                                            )
                                        )}
                                    </span>

                                    ${
                                        block.coordination
                                            ? `
                                            <span class="pill">
                                                COORDINATED
                                            </span>
                                            `
                                            : ""
                                    }

                                </div>


                                <div class="block-time">

                                    ${escapeHtml(
                                        block.start_time
                                    )}

                                    →

                                    ${escapeHtml(
                                        block.end_time
                                    )}

                                </div>


                                <div class="block-meta">

                                    ${escapeHtml(
                                        block.section_id
                                    )}

                                    · Score

                                    ${
                                        Number(
                                            block.priority_score
                                        ).toFixed(0)
                                    }

                                    ·

                                    ${
                                        block.tasks.length
                                    }

                                    task${
                                        block.tasks.length === 1
                                            ? ""
                                            : "s"
                                    }

                                </div>

                            </div>


                            <div class="block-actions">

                                <button
                                    class="small-btn"
                                    onclick="
                                        openBlock(
                                            '${escapeHtml(
                                                block.block_id
                                            )}'
                                        )
                                    "
                                >
                                    Details
                                </button>


                                ${
                                    canReview &&
                                    block.status ===
                                        "PENDING_APPROVAL"
                                        ? `
                                        <button
                                            class="small-btn"
                                            onclick="
                                                openModify(
                                                    '${escapeHtml(
                                                        block.block_id
                                                    )}'
                                                )
                                            "
                                        >
                                            Modify
                                        </button>
                                        `
                                        : ""
                                }

                            </div>

                        </div>
                        `
                )
                .join("")
        }

    </div>
    `;
}

function renderRequestCards(requests) {
    if (!requests.length) {
        return `
        <div class="empty">
            No request activity yet.
        </div>
        `;
    }

    return `
    <div class="request-list">

        ${
            requests
                .map(
                    (request) =>
                        `
                        <div class="block-card">

                            <div>

                                <div class="block-top">

                                    <span class="pill">
                                        ${escapeHtml(
                                            request.request_id
                                        )}
                                    </span>

                                    <span class="pill">
                                        ${escapeHtml(
                                            request.status
                                        )}
                                    </span>

                                </div>


                                <div class="block-meta">

                                    ${escapeHtml(
                                        request.section_id
                                    )}

                                    ·

                                    ${escapeHtml(
                                        request.work_description ||
                                        ""
                                    )}

                                </div>

                            </div>


                            <button
                                class="small-btn"
                                onclick="
                                    trackTask(
                                        '${escapeHtml(
                                            request.request_id
                                        )}'
                                    )
                                "
                            >
                                View
                            </button>

                        </div>
                        `
                )
                .join("")
        }

    </div>
    `;
}

function renderSubmit() {
    main.innerHTML = `
        <section class="panel">

            <div class="section-title">

                <h3>
                    Submit a maintenance request
                </h3>

                <span>
                    Manual entry or CSV/XLSX import
                </span>

            </div>


            <div class="upload-zone">

                <div class="page-kicker">
                    FAST IMPORT
                </div>

                <h3 style="margin:8px 0">
                    Upload a populated maintenance file
                </h3>

                <p class="muted">
                    The backend validates headers,
                    values, dates, times,
                    section IDs and duplicates
                    before anything is saved.
                </p>

                <label for="maint-file">
                    Choose CSV / XLSX
                </label>

                <input
                    id="maint-file"
                    type="file"
                    accept=".csv,.xlsx,.xlsm"
                >

                <div
                    class="upload-info"
                    id="maint-file-name"
                >
                    No file selected
                </div>


                <div class="form-actions">

                    <button
                        class="secondary"
                        type="button"
                        onclick="
                            downloadMaintenanceTemplate()
                        "
                    >
                        Download template
                    </button>

                    <button
                        class="primary"
                        type="button"
                        onclick="uploadMaintenance()"
                    >
                        Validate & submit
                    </button>

                </div>

            </div>


            <div id="maint-upload-result"></div>


            <div
                class="section-title"
                style="margin-top:28px"
            >

                <h3>
                    Or enter details manually
                </h3>

                <span>
                    Safety-relevant fields are
                    validated server-side
                </span>

            </div>


            ${manualForm()}

        </section>
    `;

    $("#maint-file").onchange =
        () => {
            $("#maint-file-name")
                .textContent =
                $("#maint-file")
                    .files[0]
                    ?.name ||
                "No file selected";
        };

    $("#manual-form")
        .onsubmit =
        submitManual;
}

function manualForm() {

    const fields = [
        ["location", "Station / location"],
        ["section_id", "Section ID"],
        ["asset_id", "Asset ID"],
        ["asset_type", "Asset type"],
        [
            "maintenance_category",
            "Maintenance category"
        ],
        ["defect_id", "Defect ID"],
        ["defect_severity", "Defect severity"],
        ["failure_risk", "Failure risk"],
        [
            "asset_operational_status",
            "Asset operational status"
        ],
        [
            "affected_asset_quantity",
            "Affected asset quantity"
        ],
        [
            "last_maintenance_date",
            "Last maintenance date"
        ],
        ["due_date", "Due date"],
        [
            "estimated_duration_minutes",
            "Estimated duration (minutes)"
        ],
        [
            "required_resources",
            "Required resources"
        ],
        [
            "block_type_required",
            "Block type"
        ],
        ["preferred_date", "Preferred date"],
        [
            "preferred_start_time",
            "Preferred start time"
        ],
        [
            "preferred_end_time",
            "Preferred end time"
        ]
    ];

    return `
    <form
        id="manual-form"
        class="form-grid"
    >

        <div class="full">

            <label>
                Work description
            </label>

            <textarea
                name="work_description"
                required
                placeholder="Describe the maintenance work precisely"
            ></textarea>

        </div>


        ${
            fields
                .map(
                    ([name, label]) => {

                        let control = "";


                        if (
                            [
                                "defect_severity",
                                "failure_risk"
                            ].includes(name)
                        ) {

                            control = `
                                <select
                                    name="${name}"
                                    required
                                >
                                    <option value="">
                                        Select
                                    </option>

                                    <option>
                                        CRITICAL
                                    </option>

                                    <option>
                                        HIGH
                                    </option>

                                    <option>
                                        MEDIUM
                                    </option>

                                    <option>
                                        LOW
                                    </option>
                                </select>
                            `;

                        } else if (
                            name ===
                            "asset_operational_status"
                        ) {

                            control = `
                                <select
                                    name="${name}"
                                    required
                                >
                                    <option>
                                        OPERATIONAL
                                    </option>

                                    <option>
                                        RESTRICTED
                                    </option>

                                    <option>
                                        DEGRADED
                                    </option>

                                    <option>
                                        FAILED
                                    </option>

                                    <option>
                                        NORMAL
                                    </option>
                                </select>
                            `;

                        } else if (
                            name ===
                            "block_type_required"
                        ) {

                            control = `
                                <select
                                    name="${name}"
                                    required
                                >
                                    <option>
                                        PARTIAL
                                    </option>

                                    <option>
                                        FULL
                                    </option>
                                </select>
                            `;

                        } else if (
                            name.includes("date")
                        ) {

                            control = `
                                <input
                                    type="date"
                                    name="${name}"
                                >
                            `;

                        } else if (
                            name.includes("time")
                        ) {

                            control = `
                                <input
                                    type="time"
                                    name="${name}"
                                >
                            `;

                        } else {

                            const required =
                                [
                                    "location",
                                    "section_id",
                                    "asset_id",
                                    "asset_type",
                                    "maintenance_category",
                                    "defect_severity",
                                    "failure_risk",
                                    "asset_operational_status",
                                    "estimated_duration_minutes"
                                ].includes(name)
                                    ? "required"
                                    : "";

                            control = `
                                <input
                                    name="${name}"
                                    ${required}
                                >
                            `;
                        }


                        return `
                        <div>

                            <label>
                                ${label}
                            </label>

                            ${control}

                        </div>
                        `;
                    }
                )
                .join("")
        }


        <div>

            <label>
                Safety related
            </label>

            <select
                name="safety_related"
                required
            >
                <option value="false">
                    No
                </option>

                <option value="true">
                    Yes
                </option>
            </select>

        </div>


        <div>

            <label>
                Requires block
            </label>

            <select
                name="requires_block"
                required
            >
                <option value="true">
                    Yes
                </option>

                <option value="false">
                    No
                </option>
            </select>

        </div>


        <div>

            <label>
                Overdue
            </label>

            <select
                name="overdue"
                required
            >
                <option value="false">
                    No
                </option>

                <option value="true">
                    Yes
                </option>
            </select>

        </div>


        <div class="form-actions full">

            <button
                class="secondary"
                type="reset"
            >
                Clear
            </button>

            <button
                class="primary"
                type="submit"
            >
                Submit request
            </button>

        </div>

    </form>
    `;
}

async function submitManual(event) {

    event.preventDefault();

    const data = {};

    new FormData(event.target)
        .forEach(
            (value, key) => {
                data[key] = value;
            }
        );

    for (
        const key of [
            "safety_related",
            "requires_block",
            "overdue"
        ]
    ) {
        data[key] =
            data[key] === "true";
    }

    for (
        const key of [
            "affected_asset_quantity",
            "estimated_duration_minutes"
        ]
    ) {
        if (data[key] !== "") {
            data[key] =
                Number(data[key]);
        }
    }

    try {

        const result =
            await api(
                "/api/maintenance/manual",
                {
                    method:
                        "POST",

                    body:
                        JSON.stringify(data)
                }
            );

        toast(
            `Request ${result.request.request_id} submitted`,
            "success"
        );

        event.target.reset();

    } catch (error) {

        showValidation(
            error.data || {
                errors: [
                    error.message
                ]
            },
            "maint-upload-result"
        );

        toast(
            "Please correct the validation errors",
            "error"
        );
    }
}

function showValidation(
    data,
    target
) {

    const element =
        document.getElementById(target);

    if (!element) {
        return;
    }

    element.innerHTML = `
        <div class="validation-box">

            <strong>
                ${
                    data.valid === false
                        ? "Validation failed"
                        : "Validation result"
                }
            </strong>

            ${
                (data.errors || [])
                    .map(
                        (error) => {

                            if (
                                typeof error ===
                                "string"
                            ) {

                                return `
                                    <div class="error-row">
                                        <div>
                                            ${escapeHtml(error)}
                                        </div>
                                    </div>
                                `;
                            }

                            return `
                                <div class="error-row">

                                    <strong>
                                        Row
                                        ${escapeHtml(error.row)}

                                        ${
                                            error.request_id ||
                                            error.train_id
                                                ? `
                                                ·
                                                ${escapeHtml(
                                                    error.request_id ||
                                                    error.train_id
                                                )}
                                                `
                                                : ""
                                        }
                                    </strong>

                                    <div>
                                        ${escapeHtml(
                                            (
                                                error.errors ||
                                                []
                                            ).join(" · ")
                                        )}
                                    </div>

                                </div>
                            `;
                        }
                    )
                    .join("")
            }

        </div>
    `;
}

async function uploadMaintenance() {

    const file =
        $("#maint-file")
            .files[0];

    if (!file) {

        return toast(
            "Select a file first",
            "error"
        );
    }

    const form =
        new FormData();

    form.append(
        "file",
        file
    );

    try {

        const result =
            await api(
                "/api/maintenance/upload",
                {
                    method: "POST",
                    body: form
                }
            );

        $("#maint-upload-result")
            .innerHTML =
            `
            <div class="validation-box">

                <div class="success-text">

                    ✓

                    ${result.saved}

                    maintenance request(s)
                    accepted and submitted.

                </div>

            </div>
            `;

        toast(
            "Maintenance file accepted",
            "success"
        );

    } catch (error) {

        showValidation(
            error.data || {
                errors: [
                    error.message
                ]
            },
            "maint-upload-result"
        );
    }
}

function renderTrack() {

    main.innerHTML =
        `
        <section class="panel">

            <div class="section-title">

                <h3>
                    Track your request
                </h3>

                <span>
                    Search using Task ID
                </span>

            </div>


            <div class="search-row">

                <input
                    class="search-input"
                    id="track-input"
                    placeholder="Example: TMS-036"
                >

                <button
                    class="primary"
                    onclick="
                        trackTask(
                            $('#track-input').value
                        )
                    "
                >
                    Track
                </button>

            </div>


            <div id="track-result"></div>

        </section>
        `;
}

async function trackTask(taskId) {

    taskId =
        (taskId || "").trim();

    if (!taskId) {

        return toast(
            "Enter a Task ID",
            "error"
        );
    }

    try {

        const result =
            await api(
                `/api/maintenance/requests/${encodeURIComponent(taskId)}`
            );

        $("#track-result")
            .innerHTML =
            renderTaskDetail(result);

    } catch (error) {

        $("#track-result")
            .innerHTML =
            `
            <div class="empty danger-text">
                ${escapeHtml(
                    error.message
                )}
            </div>
            `;
    }
}

function renderTaskDetail(result) {

    const steps = [
        "SUBMITTED",
        "RECOMMENDED",
        "PENDING_APPROVAL",
        "APPROVED",
        "REJECTED"
    ];

    return `
    <div style="padding-top:22px">

        <div class="detail-grid">

            <div class="detail">
                <small>
                    Task ID
                </small>

                <strong>
                    ${escapeHtml(
                        result.request_id
                    )}
                </strong>
            </div>


            <div class="detail">
                <small>
                    Status
                </small>

                <strong>
                    ${escapeHtml(
                        result.status
                    )}
                </strong>
            </div>


            <div class="detail">
                <small>
                    Department
                </small>

                <strong>
                    ${escapeHtml(
                        result.department
                    )}
                </strong>
            </div>


            <div class="detail">
                <small>
                    Section
                </small>

                <strong>
                    ${escapeHtml(
                        result.section_id
                    )}
                </strong>
            </div>

        </div>


        <div class="status-track">

            ${
                steps
                    .map(
                        (step, index) => {

                            const active =
                                result.status === step ||
                                (
                                    result.status ===
                                        "APPROVED" &&
                                    step !== "REJECTED" &&
                                    index < 3
                                ) ||
                                (
                                    [
                                        "PENDING_APPROVAL",
                                        "RECOMMENDED"
                                    ].includes(
                                        result.status
                                    ) &&
                                    index < 2
                                );

                            return `
                                <div
                                    class="
                                        step
                                        ${
                                            active
                                                ? "done"
                                                : ""
                                        }
                                    "
                                >
                                    ${step.replaceAll(
                                        "_",
                                        " "
                                    )}
                                </div>
                            `;
                        }
                    )
                    .join("")
            }

        </div>


        <div class="detail-grid">

            <div class="detail">
                <small>
                    Work
                </small>

                <strong>
                    ${escapeHtml(
                        result.work_description
                    )}
                </strong>
            </div>


            <div class="detail">
                <small>
                    Asset
                </small>

                <strong>
                    ${escapeHtml(
                        result.asset_id
                    )}

                    ·

                    ${escapeHtml(
                        result.asset_type
                    )}
                </strong>
            </div>


            <div class="detail">
                <small>
                    Priority inputs
                </small>

                <strong>

                    ${escapeHtml(
                        result.defect_severity
                    )}

                    /

                    ${escapeHtml(
                        result.failure_risk
                    )}

                    /

                    safety=${escapeHtml(
                        result.safety_related
                    )}

                </strong>
            </div>


            <div class="detail">

                <small>
                    Requested window
                </small>

                <strong>

                    ${escapeHtml(
                        result.preferred_date ||
                        "Any date"
                    )}

                    ${escapeHtml(
                        result.preferred_start_time ||
                        ""
                    )}

                    ${
                        result.preferred_end_time
                            ? `
                                →
                                ${escapeHtml(
                                    result.preferred_end_time
                                )}
                            `
                            : ""
                    }

                </strong>

            </div>

        </div>


        ${
            result.rejection_reason
                ? `
                <div class="validation-box">

                    <div class="danger-text">

                        Rejection reason:

                        ${escapeHtml(
                            result.rejection_reason
                        )}

                    </div>

                </div>
                `
                : ""
        }


        ${
            result.block_id
                ? `
                <div class="form-actions">

                    <button
                        class="secondary"
                        onclick="
                            openBlock(
                                '${escapeHtml(
                                    result.block_id
                                )}'
                            )
                        "
                    >
                        Open assigned block
                    </button>

                </div>
                `
                : ""
        }

    </div>
    `;
}

/* Continue using the remaining functions from the corrected
   application file for COA, blocks, approvals, notifications,
   modal handling, template downloads, login and demo data. */

async function renderCOA() {
    const data = await api("/api/coa/uploads");

    main.innerHTML = `
        <section class="panel">

            <div class="section-title">
                <h3>COA train schedule</h3>
                <span>
                    Upload and review schedules
                </span>
            </div>

            <div class="upload-zone">

                <div class="page-kicker">
                    TRAIN OPERATIONS
                </div>

                <h3 style="margin:8px 0">
                    Upload COA schedule
                </h3>

                <p class="muted">
                    Rows are validated against
                    section master, time format,
                    dates and duplicate Train IDs.
                </p>

                <label for="coa-file">
                    Choose CSV / XLSX
                </label>

                <input
                    id="coa-file"
                    type="file"
                    accept=".csv,.xlsx,.xlsm"
                >

                <div
                    class="upload-info"
                    id="coa-file-name"
                >
                    No file selected
                </div>

                <div class="form-actions">

                    <button
                        class="secondary"
                        type="button"
                        onclick="downloadCOATemplate()"
                    >
                        Download template
                    </button>

                    <button
                        class="primary"
                        type="button"
                        onclick="uploadCOA()"
                    >
                        Validate & upload
                    </button>

                </div>

            </div>

            <div id="coa-result"></div>

            <div
                class="section-title"
                style="margin-top:28px"
            >
                <h3>
                    Uploaded schedules
                </h3>
                <span>
                    Most recent first
                </span>
            </div>

            <div class="request-list">

                ${
                    (data.uploads || [])
                        .map(
                            (upload) =>
                                `
                                <div class="block-card">

                                    <div>

                                        <div class="block-top">

                                            <span class="pill">
                                                ${escapeHtml(
                                                    upload.planning_date
                                                )}
                                            </span>

                                            <span class="pill">
                                                ${upload.row_count}
                                                trains
                                            </span>

                                        </div>

                                        <div class="block-meta">
                                            ${escapeHtml(
                                                upload.filename
                                            )}
                                            · uploaded by
                                            ${escapeHtml(
                                                upload.uploaded_by
                                            )}
                                        </div>

                                    </div>

                                </div>
                                `
                        )
                        .join("")
                    ||
                    `
                    <div class="empty">
                        No uploads yet.
                    </div>
                    `
                }

            </div>

        </section>
    `;

    $("#coa-file").onchange =
        () => {
            $("#coa-file-name")
                .textContent =
                $("#coa-file")
                    .files[0]
                    ?.name ||
                "No file selected";
        };
}

async function uploadCOA() {

    const file =
        $("#coa-file")
            .files[0];

    if (!file) {
        return toast(
            "Select a COA file first",
            "error"
        );
    }

    const form =
        new FormData();

    form.append(
        "file",
        file
    );

    try {

        const result =
            await api(
                "/api/coa/upload",
                {
                    method: "POST",
                    body: form
                }
            );

        $("#coa-result")
            .innerHTML =
            `
            <div class="validation-box">

                <div class="success-text">

                    ✓ ${result.saved}
                    train rows accepted.

                </div>

            </div>
            `;

        toast(
            "COA schedule accepted",
            "success"
        );

        await renderCOA();

    } catch (error) {

        showValidation(
            error.data || {
                errors: [
                    error.message
                ]
            },
            "coa-result"
        );
    }
}

async function renderBlocks() {

    const result =
        await api(
            `/api/blocks?planning_date=${state.planningDate}`
        );

    state.blocks =
        result.blocks || [];

    main.innerHTML =
        `
        <section class="panel">

            <div class="section-title">

                <h3>
                    ${
                        state.user.department ===
                        "TDMS"
                            ? "Recommended blocks"
                            : "Blocks"
                    }
                </h3>

                <span>
                    Sorted by urgency ·
                    ${escapeHtml(
                        state.planningDate
                    )}
                </span>

            </div>

            ${renderBlockCards(
                state.blocks,
                state.user.department ===
                    "BDMS"
            )}

        </section>

        <section
            class="panel"
            style="margin-top:16px"
        >

            <div class="section-title">

                <h3>
                    Schedule timeline
                </h3>

                <span>
                    Section-wise approved /
                    recommended blocks
                </span>

            </div>

            ${renderTimeline(
                state.blocks
            )}

        </section>
        `;
}

function renderTimeline(blocks) {

    if (!blocks.length) {
        return `
            <div class="empty">
                No schedule data.
            </div>
        `;
    }

    const sections =
        [
            ...new Set(
                blocks.map(
                    block =>
                        block.section_id
                )
            )
        ].sort();

    const head = [
        "",
        "00",
        "02",
        "04",
        "06",
        "08",
        "10",
        "12",
        "14",
        "16",
        "18",
        "20",
        "22"
    ];

    let html = `
        <div class="timeline">

            <div class="timeline-grid">

                ${head
                    .map(
                        (
                            hour,
                            index
                        ) =>
                            `
                            <div
                                class="
                                    timeline-head
                                    ${
                                        index === 0
                                            ? "timeline-label"
                                            : ""
                                    }
                                "
                            >
                                ${hour}
                            </div>
                            `
                    )
                    .join("")}
    `;

    for (
        const section of sections
    ) {

        const sectionBlocks =
            blocks.filter(
                block =>
                    block.section_id ===
                    section
            );

        html += `
            <div class="timeline-label">
                ${escapeHtml(section)}
            </div>

            <div class="bar-wrap">

                ${
                    sectionBlocks
                        .map(
                            (block) => {

                                const start =
                                    mins(
                                        block.start_time
                                    );

                                const end =
                                    mins(
                                        block.end_time
                                    );

                                const left =
                                    Math.max(
                                        0,
                                        (
                                            start /
                                            1440
                                        ) * 100
                                    );

                                const width =
                                    Math.max(
                                        1,
                                        (
                                            (
                                                end -
                                                start
                                            ) /
                                            1440
                                        ) * 100
                                    );

                                return `
                                <div
                                    class="
                                        bar
                                        ${
                                            block.coordination
                                                ? "coordinated"
                                                : ""
                                        }
                                        ${
                                            block.status ===
                                            "APPROVED"
                                                ? "approved"
                                                : ""
                                        }
                                    "
                                    style="
                                        left:${left}%;
                                        width:${width}%;
                                    "
                                    title="${escapeHtml(
                                        block.block_id
                                    )}"
                                >
                                    ${escapeHtml(
                                        block.block_id
                                    )}
                                    ·
                                    ${escapeHtml(
                                        block.priority
                                    )}
                                </div>
                                `;
                            }
                        )
                        .join("")
                }

            </div>
        `;
    }

    html += `
            </div>
        </div>
    `;

    return html;
}

function mins(time) {

    const parts =
        String(time)
            .split(":")
            .map(Number);

    return (
        parts[0] * 60 +
        parts[1]
    );
}

async function renderApprovals() {

    const result =
        await api(
            `/api/blocks?planning_date=${state.planningDate}&status=PENDING_APPROVAL`
        );

    main.innerHTML =
        `
        <section class="panel">

            <div class="section-title">

                <h3>
                    Pending BDMS approvals
                </h3>

                <span>
                    ${result.blocks.length}
                    block(s)
                </span>

            </div>

            ${
                renderBlockCards(
                    result.blocks,
                    true
                )
            }

        </section>
        `;
}

async function openBlock(id) {

    try {

        const block =
            await api(
                `/api/blocks/${encodeURIComponent(id)}`
            );

        openModal(
            renderBlockModal(
                block
            )
        );

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}

function renderBlockModal(block) {

    return `
    <div class="modal-head">

        <div>

            <div class="page-kicker">
                ${escapeHtml(
                    block.status
                )}
            </div>

            <h3>
                ${escapeHtml(
                    block.block_id
                )}
            </h3>

            <div class="muted">

                ${escapeHtml(
                    block.section_id
                )}

                ·

                ${escapeHtml(
                    block.planning_date
                )}

                ·

                ${escapeHtml(
                    block.start_time
                )}

                →

                ${escapeHtml(
                    block.end_time
                )}

            </div>

        </div>


        <button
            class="close-btn"
            onclick="closeModal()"
        >
            ✕
        </button>

    </div>


    <div
        class="detail-grid"
        style="margin-top:18px"
    >

        <div class="detail">

            <small>
                Priority
            </small>

            <strong>

                ${escapeHtml(
                    block.priority
                )}

                · score

                ${Number(
                    block.priority_score
                ).toFixed(0)}

            </strong>

        </div>


        <div class="detail">

            <small>
                Coordination
            </small>

            <strong>

                ${
                    block.coordination
                        ? "Multiple departments coordinated"
                        : "Single maintenance task(s)"
                }

            </strong>

        </div>


        <div class="detail">

            <small>
                Existing block
            </small>

            <strong>

                ${
                    block.existing_block
                        ? "Yes"
                        : "No existing block matched"
                }

            </strong>

        </div>


        <div class="detail">

            <small>
                Duration
            </small>

            <strong>

                ${block.duration_minutes}

                minutes

            </strong>

        </div>

    </div>


    <div
        class="section-title"
        style="margin-top:24px"
    >

        <h3>
            Maintenance tasks in this block
        </h3>

        <span>
            ${block.tasks.length}
            task(s)
        </span>

    </div>


    <div class="request-list">

        ${
            block.tasks
                .map(
                    (task) =>
                        `
                        <div
                            class="panel"
                            style="margin:0"
                        >

                            <div class="block-top">

                                <span
                                    class="
                                        pill
                                        ${priorityClass(
                                            task.priority
                                        )}
                                    "
                                >
                                    ${escapeHtml(
                                        task.priority
                                    )}
                                </span>

                                <span class="pill">

                                    ${escapeHtml(
                                        task.department
                                    )}

                                </span>

                                <span class="pill">

                                    ${escapeHtml(
                                        task.task_id
                                    )}

                                </span>

                            </div>


                            <div
                                class="detail-grid"
                                style="margin-top:10px"
                            >

                                <div class="detail">

                                    <small>
                                        Location
                                    </small>

                                    <strong>
                                        ${escapeHtml(
                                            task.location
                                        )}
                                    </strong>

                                </div>


                                <div class="detail">

                                    <small>
                                        Asset
                                    </small>

                                    <strong>

                                        ${escapeHtml(
                                            task.asset_id
                                        )}

                                        ·

                                        ${escapeHtml(
                                            task.asset_type
                                        )}

                                    </strong>

                                </div>


                                <div class="detail">

                                    <small>
                                        Work
                                    </small>

                                    <strong>
                                        ${escapeHtml(
                                            task.work_description
                                        )}
                                    </strong>

                                </div>


                                <div class="detail">

                                    <small>
                                        Resources
                                    </small>

                                    <strong>
                                        ${escapeHtml(
                                            task.required_resources
                                        )}
                                    </strong>

                                </div>

                            </div>

                        </div>
                        `
                )
                .join("")
        }

    </div>


    ${
        state.user.department ===
            "BDMS" &&
        block.status ===
            "PENDING_APPROVAL"

            ? `
            <div class="form-actions">

                <button
                    class="secondary"
                    onclick="
                        openModify(
                            '${escapeHtml(
                                block.block_id
                            )}'
                        )
                    "
                >
                    Modify
                </button>

                <button
                    class="danger-button"
                    onclick="
                        rejectBlock(
                            '${escapeHtml(
                                block.block_id
                            )}'
                        )
                    "
                >
                    Reject
                </button>

                <button
                    class="primary"
                    onclick="
                        approveBlock(
                            '${escapeHtml(
                                block.block_id
                            )}'
                        )
                    "
                >
                    Approve block
                </button>

            </div>
            `
            : ""
    }
    `;
}

async function openModify(id) {

    try {

        const result =
            await api(
                `/api/blocks/${encodeURIComponent(id)}/slots`
            );

        openModal(
            renderModifyModal(
                result
            )
        );

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}

function renderModifyModal(result) {

    return `
    <div class="modal-head">

        <div>

            <div class="page-kicker">
                MANUAL MODIFICATION
            </div>

            <h3>
                ${escapeHtml(
                    result.block.block_id
                )}
            </h3>

        </div>

        <button
            class="close-btn"
            onclick="closeModal()"
        >
            ✕
        </button>

    </div>


    <div class="slot-list">

        ${
            (
                result.available_slots ||
                []
            )
                .map(
                    slot =>
                        `
                        <div class="slot-option">

                            <div>

                                <div class="slot-time">

                                    ${escapeHtml(
                                        slot.start_time
                                    )}

                                    →

                                    ${escapeHtml(
                                        slot.end_time
                                    )}

                                </div>

                                <div class="slot-meta">

                                    ${escapeHtml(
                                        slot.suitability
                                    )}

                                </div>

                            </div>

                            <button
                                class="small-btn"
                                onclick="
                                    applyModify(
                                        '${escapeHtml(
                                            result.block.block_id
                                        )}',
                                        '${escapeHtml(
                                            slot.start_time
                                        )}',
                                        '${escapeHtml(
                                            slot.end_time
                                        )}'
                                    )
                                "
                            >
                                Select
                            </button>

                        </div>
                        `
                )
                .join("")
            ||
            `
            <div class="empty">
                No alternative feasible
                slots are available.
            </div>
            `
        }

    </div>
    `;
}

async function applyModify(
    id,
    start,
    end
) {

    const reason =
        prompt(
            "Modification reason (optional):",
            "BDMS manual adjustment"
        );

    try {

        await api(
            `/api/blocks/${encodeURIComponent(id)}/modify`,
            {
                method:
                    "POST",

                body:
                    JSON.stringify({
                        start_time: start,
                        end_time: end,
                        reason: reason || ""
                    })
            }
        );

        toast(
            "Block modified and returned to pending approval",
            "success"
        );

        closeModal();
        renderPage();

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}

async function approveBlock(id) {

    try {

        await api(
            `/api/blocks/${encodeURIComponent(id)}/approve`,
            {
                method: "POST"
            }
        );

        toast(
            "Block approved and all departments notified",
            "success"
        );

        closeModal();
        renderPage();
        refreshNotifications();

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}

async function rejectBlock(id) {

    const reason =
        prompt(
            "Reason for rejection:",
            "Block requires further review"
        );

    if (!reason) {
        return;
    }

    try {

        await api(
            `/api/blocks/${encodeURIComponent(id)}/reject`,
            {
                method:
                    "POST",

                body:
                    JSON.stringify({
                        reason
                    })
            }
        );

        toast(
            "Block rejected",
            "success"
        );

        closeModal();
        renderPage();

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}

async function renderNotifications() {

    const result =
        await api(
            "/api/notifications"
        );

    main.innerHTML =
        `
        <section class="panel">

            <div class="section-title">

                <h3>
                    Alerts
                </h3>

                <span>
                    Department notifications
                </span>

            </div>


            <div class="notif-list">

                ${
                    (
                        result.notifications ||
                        []
                    )
                        .map(
                            notification =>
                                `
                                <div
                                    class="
                                        notification
                                        ${
                                            notification.is_read
                                                ? ""
                                                : "unread"
                                        }
                                    "
                                >

                                    <div class="block-top">

                                        <span class="pill">
                                            ${escapeHtml(
                                                notification.title
                                            )}
                                        </span>

                                        ${
                                            !notification.is_read
                                                ? `
                                                <span
                                                    class="
                                                        pill
                                                        high
                                                    "
                                                >
                                                    NEW
                                                </span>
                                                `
                                                : ""
                                        }

                                    </div>


                                    <div
                                        style="
                                            margin-top:8px;
                                            color:#445f70;
                                            font-size:12px;
                                            line-height:1.5;
                                        "
                                    >
                                        ${escapeHtml(
                                            notification.message
                                        )}
                                    </div>


                                    <div
                                        class="block-meta"
                                        style="
                                            margin-top:8px
                                        "
                                    >
                                        ${escapeHtml(
                                            notification.created_at
                                        )}
                                    </div>


                                    ${
                                        !notification.is_read
                                            ? `
                                            <div class="form-actions">

                                                <button
                                                    class="small-btn"
                                                    onclick="
                                                        markRead(
                                                            ${notification.id}
                                                        )
                                                    "
                                                >
                                                    Mark read
                                                </button>

                                            </div>
                                            `
                                            : ""
                                    }

                                </div>
                                `
                        )
                        .join("")
                    ||
                    `
                    <div class="empty">
                        No alerts.
                    </div>
                    `
                }

            </div>

        </section>
        `;
}

async function refreshNotifications() {

    try {

        const result =
            await api(
                "/api/notifications"
            );

        const unread =
            (
                result.notifications ||
                []
            )
                .filter(
                    notification =>
                        !notification.is_read
                )
                .length;

        const badge =
            $("#notify-count");

        if (!badge) {
            return;
        }

        badge.textContent =
            unread;

        badge.style.display =
            unread
                ? "inline-flex"
                : "none";

    } catch {
        /* Non-critical */
    }
}

async function markRead(id) {

    await api(
        `/api/notifications/${id}/read`,
        {
            method: "POST"
        }
    );

    renderPage();
    refreshNotifications();
}

$("#notify-button").onclick =
    () => go("notifications");

$("#refresh-button").onclick =
    () => renderPage();

$("#planning-date").onchange =
    (event) => {

        state.planningDate =
            event.target.value;

        localStorage.setItem(
            "vx_date",
            state.planningDate
        );

        renderPage();
    };

$("#logout-button").onclick =
    () => logout(true);

async function generatePlan() {

    try {

        const result =
            await api(
                "/api/planning/generate",
                {
                    method: "POST",

                    body:
                        JSON.stringify({
                            planning_date:
                                state.planningDate
                        })
                }
            );

        toast(
            `${
                result.blocks_created ||
                0
            } recommended blocks generated`,
            "success"
        );

        go(
            state.user.department ===
                "TDMS"
                ? "blocks"
                : state.user.department ===
                    "BDMS"
                    ? "approvals"
                    : "dashboard"
        );

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}

function openModal(html) {

    $("#modal-root")
        .innerHTML =
        `
        <div class="modal-backdrop">

            <div class="modal">

                ${html}

            </div>

        </div>
        `;

    $("#modal-root")
        .querySelector(
            ".modal-backdrop"
        )
        .onclick =
        (event) => {

            if (
                event.target
                    .classList
                    .contains(
                        "modal-backdrop"
                    )
            ) {

                closeModal();
            }
        };
}

function closeModal() {

    $("#modal-root")
        .innerHTML =
        "";
}

async function downloadMaintenanceTemplate() {

    try {

        const response =
            await fetch(
                "/api/templates/maintenance",
                {
                    method: "GET",

                    headers: {
                        Authorization:
                            `Bearer ${state.token}`
                    }
                }
            );

        if (response.status === 401) {

            logout(false);

            throw new Error(
                "Session expired. Please sign in again."
            );
        }

        if (!response.ok) {

            let message =
                "Unable to download template";

            try {

                const data =
                    await response.json();

                message =
                    data.detail ||
                    message;

            } catch {}

            throw new Error(
                message
            );
        }

        const blob =
            await response.blob();

        const url =
            URL.createObjectURL(
                blob
            );

        const link =
            document.createElement(
                "a"
            );

        link.href =
            url;

        link.download =
            "maintenance_template.xlsx";

        document.body.appendChild(
            link
        );

        link.click();

        link.remove();

        URL.revokeObjectURL(
            url
        );

        toast(
            "Maintenance template downloaded",
            "success"
        );

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}

async function downloadCOATemplate() {

    try {

        const response =
            await fetch(
                "/api/templates/coa",
                {
                    method: "GET",

                    headers: {
                        Authorization:
                            `Bearer ${state.token}`
                    }
                }
            );

        if (response.status === 401) {

            logout(false);

            throw new Error(
                "Session expired. Please sign in again."
            );
        }

        if (!response.ok) {

            let message =
                "Unable to download COA template";

            try {

                const data =
                    await response.json();

                message =
                    data.detail ||
                    message;

            } catch {}

            throw new Error(
                message
            );
        }

        const blob =
            await response.blob();

        const url =
            URL.createObjectURL(
                blob
            );

        const link =
            document.createElement(
                "a"
            );

        link.href =
            url;

        link.download =
            "coa_template.xlsx";

        document.body.appendChild(
            link
        );

        link.click();

        link.remove();

        URL.revokeObjectURL(
            url
        );

        toast(
            "COA template downloaded",
            "success"
        );

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}

$("#login-form")
    .onsubmit =
    async (event) => {

        event.preventDefault();

        try {

            const result =
                await api(
                    "/api/auth/login",
                    {
                        method: "POST",

                        body:
                            JSON.stringify({
                                department:
                                    $(
                                        "#login-department"
                                    ).value,

                                user_id:
                                    $(
                                        "#login-user"
                                    ).value,

                                password:
                                    $(
                                        "#login-password"
                                    ).value
                            })
                    }
                );

            state.token =
                result.token;

            state.user =
                result.user;

            localStorage.setItem(
                "vx_token",
                result.token
            );

            localStorage.setItem(
                "vx_user",
                JSON.stringify(
                    result.user
                )
            );

            toast(
                "Signed in",
                "success"
            );

            showApp();

        } catch (error) {

            toast(
                error.message,
                "error"
            );
        }
    };

if (
    state.token &&
    state.user
) {

    api("/api/me")
        .then(showApp)
        .catch(showLogin);

} else {

    showLogin();
}

window.go =
    go;

window.trackTask =
    trackTask;

window.openBlock =
    openBlock;

window.openModify =
    openModify;

window.applyModify =
    applyModify;

window.approveBlock =
    approveBlock;

window.rejectBlock =
    rejectBlock;

window.markRead =
    markRead;

window.generatePlan =
    generatePlan;

window.closeModal =
    closeModal;

window.uploadMaintenance =
    uploadMaintenance;

window.uploadCOA =
    uploadCOA;

window.mins =
    mins;

async function loadDemo() {

    try {

        const result =
            await api(
                "/api/demo/load",
                {
                    method: "POST"
                }
            );

        toast(
            `${
                result.maintenance_requests ||
                0
            } demo requests ready`,
            "success"
        );

        renderPage();

    } catch (error) {

        toast(
            error.message,
            "error"
        );
    }
}

window.loadDemo =
    loadDemo;

window.downloadMaintenanceTemplate =
    downloadMaintenanceTemplate;

window.downloadCOATemplate =
    downloadCOATemplate;