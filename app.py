from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import json
import itertools
import math
import os
import subprocess

app = Flask(__name__)
CORS(app)

DATA_FILE = "joueurs.json"

# === Chargement des joueurs ===
def load_joueurs():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

# === Sauvegarde locale ===
def save_joueurs(joueurs):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(joueurs, f, ensure_ascii=False, indent=2)

# === Sauvegarde sur GitHub ===
def push_to_github(message="Mise à jour automatique des joueurs"):
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")

    if not token or not repo:
        print("⚠️ GITHUB_TOKEN ou GITHUB_REPO manquant - commit ignoré.")
        return

    try:
        print("🔄 Commit et push vers GitHub...")

        subprocess.run(["git", "config", "--global", "user.email", "render@app.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "Render Auto Commit"], check=True)

        subprocess.run(["git", "add", DATA_FILE], check=True)
        subprocess.run(["git", "commit", "-m", message], check=False)
        subprocess.run(["git", "push", f"https://{token}@github.com/{repo}.git"], check=True)

        print("✅ Fichier joueurs.json synchronisé avec GitHub.")
    except Exception as e:
        print("❌ Erreur lors du push GitHub :", e)

# === Route principale ===
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/joueurs", methods=["GET"])
def get_joueurs():
    return jsonify(load_joueurs())

@app.route("/api/joueurs", methods=["POST"])
def add_joueur():
    joueurs = load_joueurs()
    new_joueur = request.json
    joueurs.append(new_joueur)
    save_joueurs(joueurs)
    push_to_github(f"Ajout de {new_joueur.get('nom', 'un joueur')}")
    return jsonify({"success": True})

@app.route("/api/joueurs/<nom>", methods=["PUT"])
def update_joueur(nom):
    joueurs = load_joueurs()
    updated = request.json
    for j in joueurs:
        if j["nom"] == nom:
            j.update(updated)
    save_joueurs(joueurs)
    push_to_github(f"Mise à jour de {nom}")
    return jsonify({"success": True})

@app.route("/api/joueurs/<nom>", methods=["DELETE"])
def delete_joueur(nom):
    joueurs = load_joueurs()
    joueurs = [j for j in joueurs if j["nom"] != nom]
    save_joueurs(joueurs)
    push_to_github(f"Suppression de {nom}")
    return jsonify({"success": True})

@app.route("/api/reset_dispos", methods=["POST"])
def reset_dispos():
    joueurs = load_joueurs()
    for j in joueurs:
        j["disponible"] = False
    save_joueurs(joueurs)
    push_to_github("Remise à zéro des disponibilités")
    return jsonify({"success": True})

@app.route("/api/meilleure_equipe", methods=["POST"])
def meilleure_equipe():
    data = request.get_json()
    joueurs = load_joueurs()
    dispo = [j for j in joueurs if j.get("disponible")]

    if len(dispo) < 9:
        return jsonify({"error": "moins de 9 joueurs disponibles"}), 400

    capitaine = next((j for j in joueurs if j.get("capitaine")), None)
    index_cible = 84.4
    meilleure_diff = math.inf
    meilleure_combinaison = None

    for combinaison in itertools.combinations(dispo, 9):
        total_index = 0
        for j in combinaison:
            idx = min(float(j["index"]), 18.4)
            total_index += idx
        diff = abs(total_index - index_cible)
        if diff < meilleure_diff:
            meilleure_diff = diff
            meilleure_combinaison = combinaison

    if not meilleure_combinaison:
        return jsonify({"error": "aucune combinaison trouvée"}), 400

    equipe = sorted(meilleure_combinaison, key=lambda j: float(j["index"]))
    total_reel = sum(float(j["index"]) for j in equipe)
    total_plaf = sum(min(float(j["index"]), 18.4) for j in equipe)

    result = {
        "equipe": equipe,
        "total_index_reel": round(total_reel, 1),
        "total_index_plafonne": round(total_plaf, 1)
    }

    return jsonify(result)

@app.route("/api/status")
def status():
    return jsonify({"message": "API Golf disponible"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
