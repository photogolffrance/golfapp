from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import json
import itertools
import math
import os

app = Flask(__name__)
CORS(app)

DATA_FILE = "joueurs.json"
NB_JOUEURS = 9
SEUIL = 84.4
PLAFOND = 18.4
COMBO_LIMIT = 2_000_000  # si combinaisons > ceci, on utilisera heuristique


def safe_float(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def load_joueurs():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # normalization
    normal = []
    for j in data:
        nom = j.get("nom", "").strip()
        idx = safe_float(j.get("index", 0))
        dispo = bool(j.get("disponible") or j.get("dispo") or j.get("disponibilite", False))
        cap = bool(j.get("choix_capitaine") or j.get("capitaine", False))
        normal.append({"nom": nom, "index": idx, "disponible": dispo, "choix_capitaine": cap})
    return normal


def save_joueurs(joueurs):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(joueurs, f, ensure_ascii=False, indent=2)


def calc_official_and_real(team):
    """
    team: list of player dicts
    returns (official_total, real_total, capped_player_names)
    official: apply PLAFOND to at most 2 largest indexes > PLAFOND
    """
    real_total = sum(safe_float(j["index"]) for j in team)
    above = sorted([j for j in team if safe_float(j["index"]) > PLAFOND],
                   key=lambda x: safe_float(x["index"]), reverse=True)
    capped = above[:2]
    reduction = sum((safe_float(j["index"]) - PLAFOND) for j in capped)
    official_total = real_total - reduction
    capped_names = [j["nom"] for j in capped]
    return round(official_total, 2), round(real_total, 2), capped_names


def choose_best(disponibles):
    """
    Choose best combination of NB_JOUEURS among 'disponibles' such that:
      - includes all players flagged as choix_capitaine (they are forced)
      - official_total >= SEUIL and as close as possible (minimize official_total - SEUIL)
    If none reaches SEUIL, return combination that maximizes official_total.
    Uses exhaustive search if comb count <= COMBO_LIMIT, otherwise heuristic.
    """
    forced = [j for j in disponibles if j.get("choix_capitaine")]
    pool = [j for j in disponibles if not j.get("choix_capitaine")]

    if len(forced) > NB_JOUEURS:
        return {"error": "Trop de choix du capitaine (>9)"}

    need = NB_JOUEURS - len(forced)
    if need < 0:
        return {"error": "Trop de choix du capitaine"}

    # compute combinatorial count
    try:
        comb_count = math.comb(len(pool), need) if need >= 0 else 0
    except Exception:
        comb_count = float("inf")

    # helper to evaluate a candidate team
    def eval_team(team):
        official, real, capped = calc_official_and_real(team)
        return {"official": official, "real": real, "capped": capped, "team": team}

    best_valid = None  # smallest official >= SEUIL
    best_valid_gap = None
    best_any = None  # best official < SEUIL (max official)

    if comb_count <= COMBO_LIMIT:
        # exhaustive
        for combo in itertools.combinations(pool, need):
            team = forced + list(combo)
            official, real, capped = calc_official_and_real(team)
            if official >= SEUIL:
                gap = official - SEUIL
                if best_valid is None or gap < best_valid_gap:
                    best_valid = {"team": team, "official": official, "real": real, "capped": capped}
                    best_valid_gap = gap
            else:
                if best_any is None or official > best_any["official"]:
                    best_any = {"team": team, "official": official, "real": real, "capped": capped}
    else:
        # heuristic: start with lowest indexes (greedy) and try to improve
        pool_sorted = sorted(pool, key=lambda x: safe_float(x["index"]))
        team = forced + pool_sorted[:need]
        official, real, capped = calc_official_and_real(team)
        if official >= SEUIL:
            best_valid = {"team": team, "official": official, "real": real, "capped": capped}
            best_valid_gap = official - SEUIL
        else:
            # try replacing highest in team with next available to increase official (but careful)
            remaining = [p for p in pool_sorted if p not in team]
            improved = True
            attempts = 0
            while improved and attempts < 5000:
                improved = False
                attempts += 1
                # find non-forced player with smallest index in team
                non_forced = [p for p in team if p not in forced]
                if not non_forced or not remaining:
                    break
                to_replace = min(non_forced, key=lambda x: safe_float(x["index"]))
                # try swap with largest remaining
                candidate = max(remaining, key=lambda x: safe_float(x["index"]))
                # perform swap
                new_team = [p for p in team if p != to_replace] + [candidate]
                official_n, real_n, capped_n = calc_official_and_real(new_team)
                if official_n >= SEUIL:
                    gap = official_n - SEUIL
                    if best_valid is None or gap < best_valid_gap:
                        best_valid = {"team": new_team, "official": official_n, "real": real_n, "capped": capped_n}
                        best_valid_gap = gap
                        team = new_team
                        remaining = [r for r in remaining if r != candidate] + [to_replace]
                        improved = True
                else:
                    # keep best_any
                    if best_any is None or official_n > best_any["official"]:
                        best_any = {"team": new_team, "official": official_n, "real": real_n, "capped": capped_n}
                    # also try smaller candidate
                    # rotate remaining
                    remaining = remaining[1:] + remaining[:1]

            if best_valid is None:
                # fall back to best found
                if best_any is None:
                    official, real, capped = calc_official_and_real(team)
                    best_any = {"team": team, "official": official, "real": real, "capped": capped}

    if best_valid:
        return {"success": True,
                "team": best_valid["team"],
                "official": round(best_valid["official"], 2),
                "real": round(best_valid["real"], 2),
                "capped": best_valid["capped"]}
    else:
        # return best_any (may be None)
        if best_any:
            return {"success": False,
                    "team": best_any["team"],
                    "official": round(best_any["official"], 2),
                    "real": round(best_any["real"], 2),
                    "capped": best_any["capped"]}
        else:
            return {"error": "Aucune combinaison trouvée"}


# --- ROUTES --- #

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/joueurs", methods=["GET"])
def api_get_joueurs():
    return jsonify(load_joueurs())


@app.route("/api/joueurs", methods=["POST"])
def api_save_joueurs():
    payload = request.get_json()
    # expect a list
    if not isinstance(payload, list):
        return jsonify({"error": "Format invalide, liste attendue"}), 400
    normalized = []
    for j in payload:
        nom = str(j.get("nom", "")).strip()
        idx = safe_float(j.get("index", 0))
        dispo = bool(j.get("disponible", False))
        cap = bool(j.get("choix_capitaine", False))
        normalized.append({"nom": nom, "index": idx, "disponible": dispo, "choix_capitaine": cap})
    save_joueurs(normalized)
    return jsonify({"message": "Sauvegarde OK", "count": len(normalized)})


@app.route("/api/reset_dispos", methods=["POST"])
def api_reset_dispos():
    joueurs = load_joueurs()
    for j in joueurs:
        j["disponible"] = False
    save_joueurs(joueurs)
    return jsonify({"message": "Disponibilités remises à zéro", "count": len(joueurs)})


@app.route("/api/calcul", methods=["POST"])
def api_calcul():
    # client may send current list to avoid file staleness
    payload = request.get_json(silent=True)
    if payload and isinstance(payload, dict) and "joueurs" in payload:
        joueurs = payload["joueurs"]
        # normalize incoming joueur objects
        norm = []
        for j in joueurs:
            nom = str(j.get("nom", "")).strip()
            idx = safe_float(j.get("index", 0))
            dispo = bool(j.get("disponible", False))
            cap = bool(j.get("choix_capitaine", False))
            norm.append({"nom": nom, "index": idx, "disponible": dispo, "choix_capitaine": cap})
        disponibles = [j for j in norm if j["disponible"]]
    else:
        # fallback to reading file
        disponibles = [j for j in load_joueurs() if j["disponible"]]

    if len(disponibles) < NB_JOUEURS:
        return jsonify({"error": "Moins de 9 joueurs disponibles"}), 400

    result = choose_best(disponibles)
    if "error" in result:
        return jsonify({"error": result["error"]}), 400

    # prepare output: sort team by index ascending (user wanted that)
    team = sorted(result["team"], key=lambda x: safe_float(x["index"]))
    official = result.get("official")
    real = result.get("real")
    capped = result.get("capped", [])

    out_team = []
    # mark which two were capped (if any) according to capped list
    for p in team:
        out_team.append({
            "nom": p["nom"],
            "index": round(safe_float(p["index"]), 2),
            "plafonne": p["nom"] in capped
        })

    return jsonify({
        "success": bool(result.get("success", False)),
        "team": out_team,
        "index_officiel": official,
        "index_reel": real,
        "capped": capped,
        "message": "OK" if result.get("success") else "Aucune combinaison >= seuil trouvée; meilleure trouvée."
    })


if __name__ == "__main__":
    # dev server
    app.run(host="0.0.0.0", port=5000, debug=True)
