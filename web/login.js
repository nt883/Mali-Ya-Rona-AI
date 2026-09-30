const STORAGE_KEY = "mali.actor_id";

function getStoredActorId() {
    return localStorage.getItem(STORAGE_KEY) || "";
}

function setStoredActorId(id) {
    localStorage.setItem(STORAGE_KEY, id);
}

function clearStoredActorId() {
    localStorage.removeItem(STORAGE_KEY);
}

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
        .filter(actor => actor.profile_type !== "citizen")
        .filter(actor => actor.profile_type !== "supplier")
        .forEach(actor => {
            const option = document.createElement("option");
            option.value = actor.actor_id;
            option.textContent = `${actor.actor_id} — ${actor.display_name} (${actor.role})`;
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
    const select = document.getElementById("actorSelect");
    const actorId = select.value;

    if (!actorId) {
        showError("Select an official first.");
        return;
    }

    setStoredActorId(actorId);
    window.location.href = "/govbank";
}

document.getElementById("actorSelect").addEventListener("change", () => {
    hideError();
    renderPreview();
});

document.getElementById("signInButton").addEventListener("click", signIn);

loadActors();