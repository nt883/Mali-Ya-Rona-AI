let actors = [];

function showError(message) {
    const box = document.getElementById("loginError");
    box.textContent = message;
    box.classList.remove("hidden");
}

function hideError() {
    document.getElementById("loginError").classList.add("hidden");
}

async function loadActors() {
    try {
        const response = await fetch("/api/registry/actors");
        const body = await response.json();
        actors = body.actors || [];
    } catch (error) {
        showError("Could not load the registry of officials.");
        return;
    }

    const select = document.getElementById("actorSelect");
    select.innerHTML = `<option value="">Select an official…</option>`;

    actors
        .filter(a => a.profile_type !== "citizen")
        .filter(a => a.profile_type !== "supplier")
        .forEach(actor => {
            const option = document.createElement("option");
            option.value = actor.actor_id;
            option.textContent =
                `${actor.actor_id} — ${actor.display_name} (${actor.role})`;
            select.appendChild(option);
        });
}

function renderPreview() {
    const select = document.getElementById("actorSelect");
    const preview = document.getElementById("actorPreview");
    const button = document.getElementById("signInButton");

    const actor = actors.find(a => a.actor_id === select.value);

    if (!actor) {
        preview.textContent = "No official selected.";
        button.disabled = true;
        return;
    }

    preview.innerHTML = `
        <strong>${actor.display_name}</strong>
        Credential: ${actor.actor_id}<br>
        Role: ${actor.role}<br>
        Institution: ${actor.institution_id || "—"}
    `;

    button.disabled = false;
}

function signIn() {
    const actorId = document.getElementById("actorSelect").value;

    if (!actorId) {
        showError("Select an official first.");
        return;
    }

    window.location.href =
        `/govbank?actor=${encodeURIComponent(actorId)}`;
}

document.getElementById("actorSelect").addEventListener("change", () => {
    hideError();
    renderPreview();
});

document.getElementById("signInButton").addEventListener("click", signIn);

loadActors();