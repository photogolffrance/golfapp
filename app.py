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

    SEUIL = 84.4
    PLAFOND = 18.4
    NB = 9

    if len(dispo) < NB:
        return jsonify({"error": "Moins de 9 joueurs disponibles"}), 400

    # forced = choix du capitaine (tous ceux cochés)
    forced = [j for j in dispo if j.get("choix_capitaine")]
    if len(forced) > NB:
        return jsonify({"error": "Trop de choix du capitaine (>9)"}), 400

    pool = [j for j in dispo if j not in forced]
    need = NB - len(forced)

    import itertools, math

    def official_total(team):
        # calcule total officiel (plafonnement jusqu'à 2 joueurs > PLAFOND)
        real = [float(j["index"]) for j in team]
        real_sorted_desc = sorted(real, reverse=True)
        cap_count = 0
        official = 0.0
        for v in real_sorted_desc:
            if v > PLAFOND and cap_count < 2:
                official += PLAFOND
                cap_count += 1
            else:
                official += v
        return round(official, 2), round(sum(real), 2)

    meilleure = None
    meilleur_ecart = None
    meilleur_any = None  # meilleure même si en dessous du seuil (max officiel)

    # générer combinaisons selon besoin
    if need == 0:
        candidats = [tuple()]  # pas besoin de tirer dans pool
    else:
        candidats = itertools.combinations(pool, need)

    # parcourir combinaisons
    for combo in candidats:
        team = forced + list(combo)
        off, real = official_total(team)
        if off >= SEUIL:
            ecart = off - SEUIL
            if (meilleure is None) or (ecart < meilleur_ecart):
                meilleure = {"team": team, "off": off, "real": real}
                meilleur_ecart = ecart
        else:
            # garder la meilleure en dessous (max officiel)
            if (meilleur_any is None) or (off > meilleur_any["off"]):
                meilleur_any = {"team": team, "off": off, "real": real}

    # si on a une combinaison valide (>= SEUIL)
    if meilleure:
        res_team = sorted(meilleure["team"], key=lambda x: float(x["index"]))
        # on renvoie la team SANS indiquer qui est choix du capitaine (confidentialité)
        return jsonify({
            "success": True,
            "team": [{"nom": p["nom"], "index": round(float(p["index"]), 1)} for p in res_team],
            "index_officiel": meilleure["off"],
            "index_reel": round(meilleure["real"], 1),
            "message": "Équipe calculée — objectif 84.4 atteint."
        })

    # sinon, on ne peut pas atteindre SEUIL avec les choix forcés
    # on renvoie la meilleure possible et un message d'alerte invitant la révision des choix du capitaine
    if meilleur_any:
        res_team = sorted(meilleur_any["team"], key=lambda x: float(x["index"]))
        return jsonify({
            "success": False,
            "team": [{"nom": p["nom"], "index": round(float(p["index"]), 1)} for p in res_team],
            "index_officiel": meilleur_any["off"],
            "index_reel": round(meilleur_any["real"], 1),
            "message": "❌ En dessous de 84.4 : les choix du capitaine doivent être revus pour atteindre 84.4"
        }), 400

    return jsonify({"error": "Aucune combinaison trouvée"}), 400


@app.route("/api/status")
def status():
    return jsonify({"message": "API Golf disponible"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

