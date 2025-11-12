from flask import Flask, jsonify, request
from flask_cors import CORS
import json
import itertools

app = Flask(__name__)
CORS(app)

DATA_FILE = "joueurs.json"


def load_joueurs():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_joueurs(joueurs):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(joueurs, f, ensure_ascii=False, indent=4)


@app.route("/")
def home():
    return jsonify({"message": "API Golf disponible"})


@app.route("/joueurs", methods=["GET"])
def get_joueurs():
    return jsonify(load_joueurs())


@app.route("/joueurs", methods=["POST"])
def add_joueur():
    joueurs = load_joueurs()
    data = request.json
    joueurs.append(data)
    save_joueurs(joueurs)
    return jsonify({"message": "Joueur ajouté avec succès"}), 201


@app.route("/joueurs/<int:index>", methods=["DELETE"])
def delete_joueur(index):
    joueurs = load_joueurs()
    if 0 <= index < len(joueurs):
        joueurs.pop(index)
        save_joueurs(joueurs)
        return jsonify({"message": "Joueur supprimé"}), 200
    return jsonify({"error": "Index invalide"}), 400


@app.route("/update_disponibilite", methods=["POST"])
def update_disponibilite():
    joueurs = load_joueurs()
    data = request.json
    for i, dispo in enumerate(data):
        if i < len(joueurs):
            joueurs[i]["disponible"] = dispo
    save_joueurs(joueurs)
    return jsonify({"message": "Disponibilités mises à jour"}), 200


@app.route("/reset_dispos", methods=["POST"])
def reset_dispos():
    joueurs = load_joueurs()
    for joueur in joueurs:
        joueur["disponible"] = False
    save_joueurs(joueurs)
    return jsonify({"message": "Toutes les disponibilités ont été remises à zéro"}), 200


@app.route("/calculer_meilleure_equipe", methods=["POST"])
def calculer_meilleure_equipe():
    joueurs = load_joueurs()

    # Filtrer uniquement les joueurs disponibles
    dispos = [j for j in joueurs if j["disponible"]]

    # Ajouter les choix du capitaine en priorité
    choisis_capitaine = [j for j in dispos if j["choix_capitaine"]]
    nb_restants = 9 - len(choisis_capitaine)

    if len(dispos) < 9:
        return jsonify({"error": "Moins de 9 joueurs disponibles"}), 400

    # Préparer la liste des joueurs restants
    candidats = [j for j in dispos if not j["choix_capitaine"]]

    meilleure_equipe = None
    meilleur_total = float("inf")

    # Générer toutes les combinaisons possibles pour compléter à 9 joueurs
    for combinaison in itertools.combinations(candidats, nb_restants):
        equipe = choisis_capitaine + list(combinaison)

        # Calcul de l'index global avec plafonnement à 18.4
        total = sum(min(j["index"], 18.4) for j in equipe)

        # On cherche le total le plus proche de 84.4 SANS descendre en dessous
        if total >= 84.4 and total < meilleur_total:
            meilleure_equipe = equipe
            meilleur_total = total

    if not meilleure_equipe:
        return jsonify({"error": "Aucune combinaison ne permet d’atteindre 84.4"}), 400

    # Trier la liste finale par index croissant
    meilleure_equipe = sorted(meilleure_equipe, key=lambda x: x["index"])

    # Ajout d’un astérisque pour les joueurs plafonnés
    equipe_formattee = []
    for j in meilleure_equipe:
        nom = j["nom"]
        if j["index"] > 18.4:
            nom += " *"
        equipe_formattee.append({"nom": nom, "index": j["index"]})

    return jsonify({
        "equipe": equipe_formattee,
        "index_global": round(meilleur_total, 1)
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
