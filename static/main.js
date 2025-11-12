// main.js — client side logic
const API_CALC = "/api/calcul";
const API_JOUEURS = "/api/joueurs";
const API_SAVE = "/api/joueurs";
const API_RESET = "/api/reset_dispos";

let joueurs = [];
let sortState = { col: "index", dir: 1 };

// elements
const tbody = document.querySelector("#players-table tbody");
const btnAdd = document.getElementById("btn-add");
const btnSave = document.getElementById("btn-save");
const btnReset = document.getElementById("btn-reset");
const btnCalc = document.getElementById("btn-calc");
const btnCopy = document.getElementById("btn-copy");
const resultDiv = document.getElementById("result");
const statusSpan = document.getElementById("status");

// spinner / status helpers
function showStatus(text) { statusSpan.textContent = text; }
function clearStatus() { statusSpan.textContent = ""; }

// fetch and render
async function loadPlayers() {
  try {
    const r = await fetch(API_JOUEURS);
    joueurs = await r.json();
    renderTable();
  } catch (e) {
    alert("Erreur chargement joueurs: " + e);
  }
}

function renderTable() {
  // sort according to sortState
  joueurs.sort((a,b)=> {
    const col = sortState.col;
    if (col === "nom") {
      return sortState.dir * (a.nom.localeCompare(b.nom, 'fr', {sensitivity:'base'}));
    } else {
      return sortState.dir * (parseFloat(a.index) - parseFloat(b.index));
    }
  });

  tbody.innerHTML = "";
  joueurs.forEach((j,i)=>{
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td contenteditable="true" class="cell-nom">${escapeHtml(j.nom)}</td>
      <td contenteditable="true" class="cell-index">${Number(j.index).toFixed(1)}</td>
      <td><input type="checkbox" class="cell-dispo" ${j.disponible ? "checked" : ""}></td>
      <td><input type="checkbox" class="cell-cap" ${j.choix_capitaine ? "checked" : ""}></td>
      <td><button class="btn-del">🗑️</button></td>
    `;
    // events
    tr.querySelector(".cell-nom").addEventListener("input", (e)=>{ joueurs[i].nom = e.target.innerText.trim(); });
    tr.querySelector(".cell-index").addEventListener("input", (e)=>{
      const v = e.target.innerText.replace(",", ".").trim();
      joueurs[i].index = isNaN(parseFloat(v)) ? 0 : parseFloat(v);
      e.target.innerText = Number(joueurs[i].index).toFixed(1);
    });
    tr.querySelector(".cell-dispo").addEventListener("change", (e)=>{ joueurs[i].disponible = e.target.checked; });
    tr.querySelector(".cell-cap").addEventListener("change", (e)=>{ joueurs[i].choix_capitaine = e.target.checked; });
    tr.querySelector(".btn-del").addEventListener("click", ()=>{
      if (confirm("Supprimer ce joueur ?")) {
        joueurs.splice(i,1);
        renderTable();
      }
    });
    tbody.appendChild(tr);
  });
}

// helpers
function escapeHtml(str){ return String(str).replace(/[&<>"'`=\/]/g, function(s){ return ({
  '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;','/':'&#x2F;','`':'&#x60;','=':'&#x3D;'
})[s]; }); }

// add player
btnAdd.addEventListener("click", ()=>{
  const nom = prompt("Nom du joueur (Prénom NOM) ?");
  if (!nom) return;
  const idxRaw = prompt("Index du joueur (ex: 12.7) ?");
  const idx = parseFloat(String(idxRaw).replace(",", "."));
  if (isNaN(idx)) return alert("Index invalide");
  joueurs.push({ nom: nom.trim(), index: idx, disponible: false, choix_capitaine: false });
  renderTable();
});

// save
btnSave.addEventListener("click", async ()=>{
  showStatus("Sauvegarde en cours...");
  try {
    const resp = await fetch(API_SAVE, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify(joueurs)});
    const data = await resp.json();
    showStatus(data.message || "Sauvegardé");
    setTimeout(clearStatus, 1500);
  } catch (e) {
    alert("Erreur sauvegarde: " + e);
    clearStatus();
  }
});

// reset dispo
btnReset.addEventListener("click", async ()=>{
  if (!confirm("Remettre toutes les disponibilités à NON ?")) return;
  showStatus("Remise à zéro...");
  await fetch(API_RESET, { method: "POST" });
  await loadPlayers();
  showStatus("Disponibilités remises à zéro");
  setTimeout(clearStatus, 1200);
});

// calculate
btnCalc.addEventListener("click", async ()=>{
  // send current (so client edits not yet saved to file are considered)
  showStatus("⏳ Calcul en cours…");
  btnCalc.disabled = true;
  resultDiv.style.display = "none";
  try {
    const resp = await fetch(API_CALC, { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({ joueurs })});
    if (!resp.ok) {
      const err = await resp.json().catch(()=>({error:"Erreur serveur"}));
      resultDiv.innerHTML = `<p class="err">${err.error || err.message || "Erreur lors du calcul."}</p>`;
      resultDiv.style.display = "block";
      resultDiv.scrollIntoView({behavior:"smooth"});
      showStatus("");
      btnCalc.disabled = false;
      return;
    }
    const data = await resp.json();
    // build display
    let html = `<h2>🏌️ Sélection pour le prochain match (index officiel : ${data.index_officiel})</h2>`;
    html += `<p>Index réel : ${data.index_reel}</p>`;
    html += `<ul>`;
    data.team.forEach(p=>{
      html += `<li>${escapeHtml(p.nom)}${p.plafonne ? ' <span class="capped">✳️</span>':''} — ${p.index}</li>`;
    });
    html += `</ul>`;
    html += `<p><strong>${data.success ? '✅ Objectif atteint' : '❌ Objectif non atteint — meilleure trouvée'}</strong></p>`;
    resultDiv.innerHTML = html;
    resultDiv.style.display = "block";
    resultDiv.scrollIntoView({behavior:"smooth"});
    showStatus("");
    btnCalc.disabled = false;
  } catch (e) {
    alert("Erreur calcul: " + e);
    showStatus("");
    btnCalc.disabled = false;
  }
});

// copy result
btnCopy.addEventListener("click", ()=>{
  if (resultDiv.style.display === "none" || !resultDiv.innerText.trim()) return alert("Aucun résultat à copier");
  navigator.clipboard.writeText(resultDiv.innerText).then(()=> alert("Résultat copié dans le presse-papiers"));
});

// sorting by header
document.querySelectorAll("th[data-col]").forEach(th=>{
  th.addEventListener("click", ()=>{
    const col = th.dataset.col;
    if (sortState.col === col) sortState.dir *= -1;
    else { sortState.col = col; sortState.dir = 1; }
    renderTable();
  });
});

// initial load
loadPlayers();

