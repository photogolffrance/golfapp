// main.js
let joueurs = [];
let sortOrder = { nom: 1, index: 1 };

const tbody = document.querySelector("#playersTable tbody");
const resultDiv = document.getElementById("result");

function safeNum(v) {
    const n = parseFloat(v);
    return isNaN(n) ? 0 : n;
}

async function loadPlayers() {
    try {
        const res = await axios.get("/joueurs");
        joueurs = res.data.map(j => ({
            nom: j.nom,
            index: safeNum(j.index),
            disponible: !!j.disponible,
            choix_capitaine: !!j.choix_capitaine
        }));
        renderTable();
    } catch (e) {
        alert("Erreur chargement joueurs : " + e);
    }
}

function renderTable() {
    tbody.innerHTML = "";
    joueurs.forEach((j, i) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td contenteditable="true" oninput="editNom(${i}, this.innerText)">${j.nom}</td>
            <td contenteditable="true" oninput="editIndex(${i}, this.innerText)">${j.index}</td>
            <td><input type="checkbox" ${j.disponible ? "checked" : ""} onchange="toggleDispo(${i})"></td>
            <td><input type="checkbox" ${j.choix_capitaine ? "checked" : ""} onchange="toggleCap(${i})"></td>
            <td><button class="delete-btn" onclick="del(${i})">🗑️</button></td>
        `;
        tbody.appendChild(tr);
    });
}

function editNom(i, v) { joueurs[i].nom = v.trim(); }
function editIndex(i, v) { joueurs[i].index = safeNum(v); }
function toggleDispo(i) { joueurs[i].disponible = !joueurs[i].disponible; }
function toggleCap(i) { joueurs[i].choix_capitaine = !joueurs[i].choix_capitaine; }
function del(i) { if(confirm("Supprimer ce joueur ?")) { joueurs.splice(i,1); renderTable(); } }

document.getElementById("addBtn").onclick = () => {
    joueurs.push({ nom: "Nouveau joueur", index: 0.0, disponible: true, choix_capitaine: false });
    renderTable();
};

document.getElementById("saveBtn").onclick = async () => {
    try {
        await axios.post("/sauvegarder", joueurs);
        alert("✅ Sauvegardé !");
    } catch (e) {
        alert("Erreur sauvegarde : " + e);
    }
};

document.getElementById("calcBtn").onclick = async () => {
    try {
        const resp = await axios.post("/calcul", { joueurs });
        const data = resp.data;
        showResult(data);
        // faire défiler vers le résultat
        resultDiv.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
        alert("Erreur calcul : " + e);
    }
};

document.querySelectorAll("th[data-col]").forEach(th => {
    th.addEventListener("click", () => {
        const col = th.dataset.col;
        sortOrder[col] *= -1;
        joueurs.sort((a,b) => {
            if (a[col] > b[col]) return sortOrder[col];
            if (a[col] < b[col]) return -sortOrder[col];
            return 0;
        });
        renderTable();
    });
});

function showResult(data) {
    if (!data || !data.selection) {
        resultDiv.style.display = "block";
        resultDiv.innerHTML = `<p style="color:red">Erreur lors du calcul.</p>`;
        return;
    }
    if (data.selection.length === 0) {
        resultDiv.style.display = "block";
        resultDiv.innerHTML = `<p style="color:red">${data.message}</p>`;
        return;
    }

    const capped = data.capped_players || [];
    // selection is already sorted by index on server, but ensure it client-side too
    const selectionSorted = data.selection.slice().sort((a,b) => a.index - b.index);

    const selHtml = selectionSorted.map(j => {
        const isCapped = capped.includes(j.nom);
        return `<li>${j.nom}${isCapped ? ' <span class="capped">✳️</span>' : ''} - Index ${j.index}</li>`;
    }).join("");

    const ok = data.success;
    const status = ok ? `<p style="color:green"><strong>✅ Objectif atteint — index officiel : ${data.official_total}</strong></p>`
                      : `<p style="color:red"><strong>❌ Objectif NON atteint — meilleur index officiel trouvé : ${data.official_total}</strong></p>`;

    resultDiv.style.display = "block";
    resultDiv.innerHTML = `
        <h3>🏌️ SÉLECTION DES 9 JOUEURS :</h3>
        <ul>${selHtml}</ul>
        <p><strong>Index global (officiel, plafonné) :</strong> ${data.official_total}</p>
        <p><strong>Index global réel :</strong> ${data.real_total}</p>
        ${status}
        <p>${data.message}</p>
    `;
}

window.onload = loadPlayers;
