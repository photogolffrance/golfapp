from flask import Flask, jsonify, request, render_template
import json
import os
import itertools
import math

app = Flask(__name__)

FICHIER_JOUEURS = "joueurs.json"
NB_JOUEURS = 9
SEUIL_INDEX = 84.4
PLAFOND = 18.4
COMBO_LIMIT = 2_000_000


def charger_joueurs():
    if os.path.exists(FICHIER_JOUEURS):
        with open(FICHIER_JOUEURS, "r", encoding="utf-8") as f:
            data = json.load(f)
        for j in data:
            if "disponible" not in j and "dispo" in j:
                j["disponible"] = j.pop("dispo")
            if "choix_capitaine" not in j and "capitaine" in j:
                j["choix_capitaine"] = j.pop("capitaine")
            j["disponible"] = bool(j.get("disponible", False))
            j["choix_capitaine"] = bool(j.get("choix_capitaine", False))
            try:
                j["index"] = float(j.get("index", 0))
            except:
                j["index"] = 0.0
        return data
    return []


def sauvegarder_joueurs(joueurs):
    with open(FICHIER_JOUEURS, "w", encoding="utf-8") as f:
        json.dump(joueurs, f, indent=4, ensure_ascii=False)


def calc_officiel_and_capped(selection):
    real_total = sum(float(j["index"]) for j in selection)
    au_dessus = sorted([j for j in selection if float(j["index"]) > PLAFOND],
                       key=lambda x: float(x["index"]), reverse=True)
    nb_assimiles = min(2, len(au_dessus))
    official_total = real_total
    capped_players = []
    if nb_assimiles > 0:
        to_reduce = au_dessus[:nb_assimiles]
        reduction = sum(float(j["index"]) - PLAFOND for j in to_reduce)
        official_total = real_total - reduction
        capped_players = [j["nom"] for j in to_reduce]
    return official_total, real_total, capped_players


def choose_best_combination(disponibles):
    choix_cap = [j for j in disponibles if j.get("choix_capitaine")]
    reste = [j for j in disponibles if not j.get("choix_capitaine")]
    if len(choix_cap) > NB_JOUEURS:
        return {"error": "Trop de choix du capitaine (plus de 9)."}

    need = NB_JOUEURS - len(choix_cap)
    if need < 0:
        return {"error": "Trop de choix du capitaine."}
    if need == 0:
        candidates = [tuple(choix_cap)]
    else:
        try:
            comb_count = math.comb(len(reste), need)
        except:
            comb_count = float("inf")

        if comb_count <= COMBO_LIMIT:
            candidates = (tuple(choix_cap) + combo for combo in itertools.combinations(reste, need))
        else:
            selection = choix_cap + sorted(reste, key=lambda x: x["index"])[:need]
            rest_weak = sorted([r for r in reste if r not in selection], key=lambda x: x["index"], reverse=True)
            non_cap_in_sel = [s for s in selection if s not in choix_cap]
            i_weak = 0
            while True:
                official, real, _ = calc_officiel_and_capped(selection)
                if official >= SEUIL_INDEX or i_weak >= len(rest_weak) or not non_cap_in_sel:
                    break
                best_to_replace = min(non_cap_in_sel, key=lambda x: x["index"])
                candidate_replacement = rest_weak[i_weak]
                if candidate_replacement["index"] <= best_to_replace["index"]:
                    break
                selection.remove(best_to_replace)
                selection.append(candidate_replacement)
                non_cap_in_sel.remove(best_to_replace)
                non_cap_in_sel.append(candidate_replacement)
                i_weak += 1
            candidates = [tuple(selection)]

    best_found = None
    best_official = None
    best_real = None
    best_capped = []

    for equipe in candidates:
        equipe_list = list(equipe)
        official_total, real_total, capped = calc_officiel_and_capped(equipe_list)
        if official_total >= SEUIL_INDEX:
            if (best_found is None) or (best_official is None) or (official_total < best_official):
                best_found = equipe_list
                best_official = official_total
                best_real = real_total
                best_capped = capped
        else:
            if best_found is None:
                if best_official is None or official_total > best_official:
                    best_found = equipe_list
                    best_official = official_total
                    best_real = real_total
                    best_capped = capped

    # ensure selection sorted by index ascending for output
    if best_found:
        best_found = sorted(best_found, key=lambda x: float(x["index"]))

    success = (best_official is not None and best_official >= SEUIL_INDEX)
    return {
        "selection": best_found,
        "official_total": round(best_official, 1) if best_official is not None else None,
        "real_total": round(best_real, 1) if best_real is not None else None,
        "capped_players": best_capped,
        "success": success
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/joueurs", methods=["GET"])
def get_joueurs():
    return jsonify(charger_joueurs())


@app.route("/sauvegarder", methods=["POST"])
def save_joueurs():
    joueurs = request.json
    for j in joueurs:
        if "disponible" not in j and "dispo" in j:
            j["disponible"] = j.pop("dispo")
        if "choix_capitaine" not in j and "capitaine" in j:
            j["choix_capitaine"] = j.pop("capitaine")
        j["disponible"] = bool(j.get("disponible", False))
        j["choix_capitaine"] = bool(j.get("choix_capitaine", False))
        try:
            j["index"] = float(j.get("index", 0))
        except:
            j["index"] = 0.0
    sauvegarder_joueurs(joueurs)
    return jsonify({"message": "Sauvegarde réussie"})


@app.route("/calcul", methods=["POST"])
def calcul():
    payload = request.json
    joueurs = payload.get("joueurs", [])
    for j in joueurs:
        j["disponible"] = bool(j.get("disponible", False))
        j["choix_capitaine"] = bool(j.get("choix_capitaine", False))
        try:
            j["index"] = float(j.get("index", 0))
        except:
            j["index"] = 0.0

    disponibles = [j for j in joueurs if j.get("disponible")]
    if len(disponibles) < NB_JOUEURS:
        return jsonify({
            "message": "❌ Moins de 9 joueurs disponibles !",
            "selection": [],
            "official_total": None,
            "real_total": None,
            "capped_players": []
        })

    result = choose_best_combination(disponibles)
    if "error" in result:
        return jsonify({"message": result["error"], "selection": [], "official_total": None, "real_total": None, "capped_players": []})

    selection = result["selection"]
    official_total = result["official_total"]
    real_total = result["real_total"]
    capped = result["capped_players"]
    success = result["success"]

    if success:
        message = f"✅ OK — Index officiel : {official_total} (règle appliquée), objectif ≥ {SEUIL_INDEX}"
    else:
        message = f"❌ Impossible d'atteindre {SEUIL_INDEX}. Meilleure valeur officielle trouvée : {official_total}"

    sel_out = []
    for j in selection:
        sel_out.append({
            "nom": j.get("nom"),
            "index": j.get("index"),
            "disponible": j.get("disponible", True),
            "choix_capitaine": j.get("choix_capitaine", False)
        })

    return jsonify({
        "message": message,
        "selection": sel_out,
        "official_total": official_total,
        "real_total": real_total,
        "capped_players": capped,
        "success": success
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
