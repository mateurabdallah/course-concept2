"""Logique: récupération des résultats, calcul des points par course (catégorie),
et classement général des clubs (comme un tournoi officiel d'aviron)."""

import csv
import io
import json
import os
from collections import defaultdict

import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clubs_config.json")

DEFAULT_CONFIG = {
    "refresh_seconds": 60,
    "clubs": [
        {"nom": f"Club {i+1}", "url": "https://log.concept2.com/api/ergrace/races/REMPLACER_ID/results/export"}
        for i in range(10)
    ],
}

# Barème de points par place (comme les tournois officiels d'aviron)
POINTS_SCALE = {1: 10, 2: 8, 3: 6, 4: 5, 5: 4, 6: 3, 7: 2, 8: 1}


def load_config():
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_time_to_seconds(value):
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    parts = value.split(":")
    try:
        parts = [float(p) for p in parts]
    except ValueError:
        return None
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def fetch_club_results(club_name, url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return [], str(e)

    text = resp.content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        affiliation = (row.get("Affiliation") or "").strip()
        rows.append({
            "club": affiliation if affiliation else club_name,
            "participant": (row.get("Participant") or "").strip(),
            "category": (row.get("Class") or "غير محدد").strip() or "غير محدد",
            "score": (row.get("Score") or "").strip(),
        })
    return rows, None


def rank_race(rows):
    """Trie une course par temps, attribue rangs (avec égalités) et points."""
    timed = []
    untimed = []
    for r in rows:
        secs = parse_time_to_seconds(r["score"])
        if secs is None:
            untimed.append(r)
        else:
            r2 = dict(r)
            r2["_secs"] = secs
            timed.append(r2)

    timed.sort(key=lambda r: r["_secs"])

    results = []
    place = 0
    prev_secs = None
    skipped = 0
    for r in timed:
        place += 1
        if prev_secs is not None and r["_secs"] == prev_secs:
            actual_place = results[-1]["place"]
            skipped += 1
        else:
            actual_place = place
            place += skipped
            skipped = 0
        points = POINTS_SCALE.get(actual_place, 0)
        results.append({
            "place": actual_place,
            "participant": r["participant"],
            "club": r["club"],
            "score": r["score"],
            "points": points,
        })
        prev_secs = r["_secs"]

    for r in untimed:
        results.append({
            "place": "ABS",
            "participant": r["participant"],
            "club": r["club"],
            "score": r["score"] or "ABS",
            "points": 0,
        })

    return results


def build_combined_results(config):
    all_rows = []
    club_status = []
    for club in config["clubs"]:
        name, url = club["nom"], club["url"]
        if "REMPLACER_ID" in url:
            club_status.append({"nom": name, "statut": "non configuré", "nb": 0})
            continue
        rows, error = fetch_club_results(name, url)
        if error:
            club_status.append({"nom": name, "statut": f"erreur: {error}", "nb": 0})
        else:
            club_status.append({"nom": name, "statut": "ok", "nb": len(rows)})
        all_rows.extend(rows)

    by_category = defaultdict(list)
    for r in all_rows:
        by_category[r["category"]].append(r)

    races = []
    club_points = defaultdict(int)
    for category in sorted(by_category.keys()):
        ranked = rank_race(by_category[category])
        for r in ranked:
            club_points[r["club"]] += r["points"]
        races.append({"category": category, "results": ranked})

    standings = [{"club": club, "points": pts} for club, pts in club_points.items()]
    standings.sort(key=lambda s: -s["points"])
    for i, s in enumerate(standings, start=1):
        s["rank"] = i

    return {"races": races, "standings": standings, "clubs": club_status}        parts = [float(p) for p in parts]
    except ValueError:
        return None
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def fetch_club_results(club_name, url):
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return [], str(e)

    text = resp.content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows = []
    for row in reader:
        affiliation = (row.get("Affiliation") or "").strip()
        rows.append({
            "club": affiliation if affiliation else club_name,
            "participant": (row.get("Participant") or "").strip(),
            "category": (row.get("Class") or "").strip(),
            "score": (row.get("Score") or "").strip(),
            "avg_pace": (row.get("Avg Pace") or "").strip(),
            "spm": (row.get("SPM") or "").strip(),
        })
    return rows, None


def build_combined_results(config):
    all_rows = []
    club_status = []
    for club in config["clubs"]:
        name, url = club["nom"], club["url"]
        if "REMPLACER_ID" in url:
            club_status.append({"nom": name, "statut": "non configuré", "nb": 0})
            continue
        rows, error = fetch_club_results(name, url)
        if error:
            club_status.append({"nom": name, "statut": f"erreur: {error}", "nb": 0})
        else:
            club_status.append({"nom": name, "statut": "ok", "nb": len(rows)})
        all_rows.extend(rows)

    for r in all_rows:
        secs = parse_time_to_seconds(r["score"])
        r["_secs"] = secs if secs is not None else float("inf")

    all_rows.sort(key=lambda r: r["_secs"])
    for i, r in enumerate(all_rows, start=1):
        r["place"] = i
        del r["_secs"]

    categories = sorted(set(r["category"] for r in all_rows if r["category"]))

    return {"rows": all_rows, "clubs": club_status, "categories": categories}
