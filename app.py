from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import json, itertools, math, os, subprocess

app = Flask(__name__)
CORS(app)

DATA_FILE = "joueurs.json"

# === Helpers JSON ===
def load_joueurs():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_joueurs(joueurs):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(joueurs, f, ensure_ascii=False, indent=2)

# === GitHub sync ===
def push_to_github(message="Mise à jour automatique"):
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")

    if not token or not repo:
        print("⚠️ GITHUB_TOKEN ou GITHUB_REPO manquant.")
        return

    try:
        subprocess.run(["git", "config", "--global", "user.email", "render@app.com"], check=True)
        subprocess.run(["git", "config", "--global", "user.name", "Render Auto Commit"], check=True)
        subprocess.run(["git", "add", DATA_FILE], check=True)
        subprocess.run(["git", "commit", "-m", message], check=False)
        subprocess.run(["git", "push", f"https://{token}@github.com/{repo}.git"], check=True)
        print("✅ Push GitHub OK")
    except Exception as e:
        print("❌ Erreur push GitHub :", e)

# === Routes API ===
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/joueurs", methods=["GET"])
def get_joueurs():
    return jsonify(load_joueurs())

@app.route("/api/joueurs", methods=["POST"])
def add_joueur():
    """Ajoute un joueur individuel"""
    new_joueur = request.get_json()
    joueurs = load_joueurs()

    # anti-doublon
    if any(j["nom"].strip().lower() == new_joueur["nom"].strip().lower() for j in joueurs):
        return jsonify({"error": "Ce joueur existe déjà"}), 400

    joueurs.append(new_joueur)
    save_joueurs(joueurs)
    push_to_github(f"Ajout de {new_joueur.get('nom', 'un joueur')}")
    return jsonify(joueurs)

@app.route("/api/joueurs", methods=["PUT"])
def replace_joueurs():
    """Remplace toute la liste"""
    data = request.get_json()
    if not isinstance(data, list):
        return jsonify({"error": "Format invalide"}), 400
    save_joueurs(data)
    push_to_github("Sauvegarde complète de la liste")
    return jsonify(data)

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
    joueurs = load_joueurs()
    dispo = [j for j in joueurs if j.get("disponible")]

    if len(dispo) < 9:
        return jsonify({"error": "Moins de 9 joueurs disponibles"}), 400

    index_cible = 84.4
    meilleure_diff = math.inf
    meilleure_combinaison = None

    for combinaison in itertools.combinations(dispo, 9):
        total_index = sum(min(float(j["index"]), 18.4) for j in combinaison)
        diff = abs(total_index - index_cible)
        if diff < meilleure_diff:
            meilleure_diff = diff
            meilleure_combinaison = combinaison

    if not meilleure_combinaison:
        return jsonify({"error": "Aucune combinaison trouvée"}), 400

    equipe = sorted(meilleure_combinaison, key=lambda j: float(j["index"]))
    total_reel = sum(float(j["index"]) for j in equipe)
    total_plaf = sum(min(float(j["index"]), 18.4) for j in equipe)

    return jsonify({
        "equipe": equipe,
        "total_index_reel": round(total_reel, 1),
        "total_index_plafonne": round(total_plaf, 1)
    })

@app.route("/api/status")
def status():
    return jsonify({"message": "API Golf disponible"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
