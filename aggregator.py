"""Logique partagée: récupération, parsing et fusion des résultats ErgRace."""

import csv
import io
import json
import os

import requests

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clubs_config.json")

DEFAULT_CONFIG = {
    "refresh_seconds": 60,
    "clubs": [
        {"nom": f"Club {i+1}", "url": "https://log.concept2.com/api/ergrace/races/REMPLACER_ID/results/export"}
        for i in range(10)
    ],
}


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
