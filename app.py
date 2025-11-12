from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import json
import itertools
import os

app = Flask(__name__)
CORS(app)

DATA_FILE = "joueurs.json"

# --- Fonctions utilitaires --- #
def charger_joueurs():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def sauvegarder_joueurs(joueurs):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(joueurs, f, indent=2, ensure_ascii=False)

# --- Routes principales --- #
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/joueurs", methods=["GET"])
def get_joueurs():
    return jsonify(charger_joueurs())

@app.route("/api/joueurs", methods=["POST"])
def ajouter_joueur():
    joueurs = charger_joueurs()
    data = request.get_json()
    data["disponible"] = bool(data.get("disponible", False))
    data["choix_capitaine"] = bool(data.get("choix_capitaine", False))
    joueurs.append(data)
    sauvegarder_joueurs(joueurs)
    return jsonify({"message": "Joueur ajouté avec succès", "joueurs": joueurs})

@app.route("/api/joueurs/<int:index>", methods=["DELETE"])
def supprimer_joueur(index):
    joueurs = charger_joueurs()
    if 0 <= index < len(joueurs):
        joueurs.pop(index)
        sauvegarder_joueurs(joueurs)
        return jsonify({"message": "Joueur supprimé"})
    return jsonify({"error": "Index invalide"}), 400

@app.route("/api/reset_dispos", methods=["POST"])
def reset_dispos():
    joueurs = charger_joueurs()
    for j in joueurs:
        j["disponible"] = False
    sauvegarder_joueurs(joueurs)
    return jsonify({"message": "Toutes les disponibilités ont été remises à zéro", "joueurs": joueurs})

@app.route("/api/sauvegarder", methods=["POST"])
def sauvegarder():
    data = request.get_json()
    sauvegarder_joueurs(data)
    return jsonify({"message": "Données sauvegardées avec succès"})

@app.route("/api/meilleure_equipe", methods=["POST"])
def meilleure_equipe():
    joueurs = charger_joueurs()
    dispos = [j for j in joueurs if j.get("disponible")]
    cap_choices = [j for j in joueurs if j.get("choix_capitaine")]

    if len(dispos) < 9:
        return jsonify({"error": "Moins de 9 joueurs disponibles."}), 400

    # --- On sélectionne les 9 meilleurs pour approcher 84.4 --- #
    meilleure_combo = None
    meilleur_ecart = float("inf")

    for combo in itertools.combinations(dispos, 9):
        total = 0
        plafonnes = 0
        for j in combo:
            idx = j["index"]
            if idx > 18.4:
                idx = 18.4
                plafonnes += 1
            total += idx

        if plafonnes <= 2 and total >= 84.4:
            ecart = total - 84.4
            if 0 <= ecart < meilleur_ecart:
                meilleur_ecart = ecart
                meilleure_combo = combo

    if not meilleure_combo:
        return jsonify({"error": "Aucune combinaison valide trouvée."}), 400

    equipe = sorted(meilleure_combo, key=lambda x: x["index"])
    total_reel = sum(j["index"] for j in equipe)
    total_officiel = sum(min(j["index"], 18.4) for j in equipe)

    # Indiquer les plafonnés
    for j in equipe:
        j["plafonne"] = j["index"] > 18.4

    message = (
        f"✅ Équipe validée : {total_officiel:.1f} (≥ 84.4)"
        if total_officiel >= 84.4
        else f"❌ En dessous de 84.4 : {total_officiel:.1f}"
    )

    resultat = {
        "joueurs": equipe,
        "index_reel": round(total_reel, 1),
        "index_officiel": round(total_officiel, 1),
        "message": message,
    }

    return jsonify(resultat)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
