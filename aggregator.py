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

    # ترتيب المتسابقين حسب الزمن (من الأسرع للأبطأ)
    timed.sort(key=lambda r: r["_secs"])

    results = []
    
    # حساب الترتيب مع مراعاة التعادل بدون أخطاء عملية
    for i, r in enumerate(timed):
        if i > 0 and r["_secs"] == timed[i - 1]["_secs"]:
            actual_place = results[-1]["place"]
        else:
            actual_place = i + 1

        points = POINTS_SCALE.get(actual_place, 0)
        results.append({
            "place": actual_place,
            "participant": r["participant"],
            "club": r["club"],
            "score": r["score"],
            "points": points,
        })

    # إضافة من هم بدون توقيت أو غائبين
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
    for club in config.get("clubs", []):
        name, url = club.get("nom", "Club"), club.get("url", "")
        
        # حماية: تجاهل الرابط إذا كان غير مكتمل أو محلي غير صالح
        if "REMPLACER_ID" in url or not url.startswith("http"):
            club_status.append({"nom": name, "statut": "غير محدد (مؤقت)", "nb": 0})
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

    return {"races": races, "standings": standings, "clubs": club_status}
