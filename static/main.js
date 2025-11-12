const apiBase = "/api";

async function chargerJoueurs() {
  const res = await fetch(`${apiBase}/joueurs`);
  const data = await res.json();
  afficherTableau(data);
}

async function sauvegarder() {
  const lignes = document.querySelectorAll("#tableau tbody tr");
  const joueurs = [];
  lignes.forEach((tr) => {
    joueurs.push({
      nom: tr.querySelector(".nom").textContent,
      index: parseFloat(tr.querySelector(".index").textContent),
      disponible: tr.querySelector(".dispo").checked,
      choix_capitaine: tr.querySelector(".capitaine").checked,
    });
  });
  await fetch(`${apiBase}/sauvegarder`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(joueurs),
  });
  alert("✅ Sauvegarde effectuée !");
}

async function resetDispos() {
  await fetch(`${apiBase}/reset_dispos`, { method: "POST" });
  alert("Toutes les disponibilités ont été remises à zéro !");
  chargerJoueurs();
}

function afficherTableau(joueurs) {
  const container = document.getElementById("tableau");
  let html = `<table><thead><tr>
      <th>Nom</th>
      <th>Index</th>
      <th>Disponible</th>
      <th>Choix capitaine</th>
      <th>Supprimer</th>
    </tr></thead><tbody>`;

  joueurs.forEach((j, i) => {
    html += `<tr>
      <td class="nom">${j.nom}</td>
      <td class="index">${j.index}</td>
      <td><input type="checkbox" class="dispo" ${j.disponible ? "checked" : ""}></td>
      <td><input type="checkbox" class="capitaine" ${j.choix_capitaine ? "checked" : ""}></td>
      <td><button onclick="supprimerJoueur(${i})">🗑️</button></td>
    </tr>`;
  });
  html += `</tbody></table>`;
  container.innerHTML = html;
}

async function supprimerJoueur(i) {
  await fetch(`${apiBase}/joueurs/${i}`, { method: "DELETE" });
  chargerJoueurs();
}

async function ajouterJoueur() {
  const nom = prompt("Nom du joueur ?");
  const index = parseFloat(prompt("Index du joueur ?"));
  if (!nom || isNaN(index)) return alert("Entrée invalide !");
  await fetch(`${apiBase}/joueurs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nom, index, disponible: false, choix_capitaine: false }),
  });
  chargerJoueurs();
}

async function calculerEquipe() {
  const res = await fetch(`${apiBase}/meilleure_equipe`, { method: "POST" });
  const data = await res.json();

  const div = document.getElementById("resultat");
  if (data.error) {
    div.innerHTML = `<p style="color:red">${data.error}</p>`;
    div.scrollIntoView({ behavior: "smooth" });
    return;
  }

  let html = `<h2>🏌️ Sélection des 9 joueurs :</h2><ul>`;
  data.joueurs.forEach((j) => {
    const plaf = j.plafonne ? " *" : "";
    html += `<li>${j.nom} – Index ${j.index}${plaf}</li>`;
  });
  html += `</ul>`;
  html += `<p><strong>Index global réel :</strong> ${data.index_reel}<br>
           <strong>Index global officiel :</strong> ${data.index_officiel}</p>`;
  html += `<p>${data.message}</p>`;

  div.innerHTML = html;
  div.scrollIntoView({ behavior: "smooth" });
}

document.getElementById("btn-ajouter").addEventListener("click", ajouterJoueur);
document.getElementById("btn-sauvegarder").addEventListener("click", sauvegarder);
document.getElementById("btn-reset").addEventListener("click", resetDispos);
document.getElementById("btn-calculer").addEventListener("click", calculerEquipe);

chargerJoueurs();
