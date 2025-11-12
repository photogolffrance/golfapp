const API_URL = "http://127.0.0.1:5000";
const tableBody = document.querySelector("#tableJoueurs tbody");
const resultatDiv = document.getElementById("resultat");
const calculBtn = document.getElementById("calculBtn");
const saveBtn = document.getElementById("saveBtn");
const resetBtn = document.getElementById("resetBtn");

async function chargerJoueurs() {
    const res = await fetch(`${API_URL}/joueurs`);
    const joueurs = await res.json();
    tableBody.innerHTML = "";
    joueurs.forEach((j, i) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${j.nom}</td>
            <td>${j.index}</td>
            <td><input type="checkbox" ${j.disponible ? "checked" : ""}></td>
            <td><input type="checkbox" ${j.choix_capitaine ? "checked" : ""}></td>
        `;
        tableBody.appendChild(tr);
    });
}

async function sauvegarderDispos() {
    const lignes = tableBody.querySelectorAll("tr");
    const dispos = Array.from(lignes).map(l => l.children[2].firstChild.checked);
    await fetch(`${API_URL}/update_disponibilite`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(dispos)
    });
    alert("Disponibilités sauvegardées !");
}

async function calculerEquipe() {
    resultatDiv.innerHTML = "<em>Calcul en cours...</em>";
    calculBtn.disabled = true;

    const res = await fetch(`${API_URL}/calculer_meilleure_equipe`, {method: "POST"});
    calculBtn.disabled = false;

    if (!res.ok) {
        const err = await res.json();
        resultatDiv.innerHTML = `<strong>❌ ${err.error}</strong>`;
        return;
    }

    const data = await res.json();
    let html = `<h3>🏆 Meilleure équipe (Index global : ${data.index_global})</h3><ul>`;
    data.equipe.forEach(j => html += `<li>${j.nom} – Index ${j.index}</li>`);
    html += "</ul>";

    resultatDiv.innerHTML = html;
    resultatDiv.scrollIntoView({behavior: "smooth"});
}

async function resetDispos() {
    if (!confirm("Remettre toutes les disponibilités à NON ?")) return;
    await fetch(`${API_URL}/reset_dispos`, {method: "POST"});
    chargerJoueurs();
    alert("Toutes les disponibilités ont été remises à zéro !");
}

saveBtn.addEventListener("click", sauvegarderDispos);
calculBtn.addEventListener("click", calculerEquipe);
resetBtn.addEventListener("click", resetDispos);

chargerJoueurs();
