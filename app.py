#!/usr/bin/env python3
"""Dashboard web: classement général + résultats par course + gestion des listes de départ."""

import csv
import io
import os
import time

from flask import Flask, jsonify, render_template, request, send_file

from aggregator import load_config, build_combined_results
from startlist import (
    parse_engagement_file, load_startlist_data, add_file_entries,
    clear_startlist_data, group_by_category,
)

app = Flask(__name__)

cache = {"data": {"races": [], "standings": [], "clubs": []}, "updated_at": None, "last_fetch": 0}


def get_fresh_data():
    config = load_config()
    interval = config.get("refresh_seconds", 60)
    now = time.time()
    if now - cache["last_fetch"] >= interval or cache["updated_at"] is None:
        data = build_combined_results(config)
        cache["data"] = data
        cache["last_fetch"] = now
        cache["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    return cache


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/results")
def api_results():
    state = get_fresh_data()
    return jsonify({
        "races": state["data"]["races"],
        "standings": state["data"]["standings"],
        "clubs": state["data"]["clubs"],
        "updated_at": state["updated_at"],
    })


@app.route("/startlist")
def startlist_page():
    return render_template("startlist.html")


@app.route("/api/startlist")
def api_startlist():
    data = load_startlist_data()
    grouped = group_by_category(data["entries"])
    races = [{"category": cat, "entries": entries} for cat, entries in grouped.items()]
    return jsonify({"files": data["files"], "races": races, "total": len(data["entries"])})


@app.route("/api/startlist/upload", methods=["POST"])
def api_startlist_upload():
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error": "لا توجد ملفات"}), 400
    results = []
    for f in files:
        try:
            content = f.read()
            club, entries = parse_engagement_file(content, f.filename)
            add_file_entries(f.filename, club, entries)
            results.append({"filename": f.filename, "club": club, "count": len(entries)})
        except Exception as e:
            results.append({"filename": f.filename, "error": str(e)})
    return jsonify({"results": results})


@app.route("/api/startlist/clear", methods=["POST"])
def api_startlist_clear():
    clear_startlist_data()
    return jsonify({"ok": True})


@app.route("/api/startlist/export.csv")
def api_startlist_export_csv():
    data = load_startlist_data()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Class", "Participant", "Affiliation"])
    for e in data["entries"]:
        writer.writerow([e["category"], e["participant"], e["club"]])
    mem = io.BytesIO(output.getvalue().encode("utf-8-sig"))
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="start_list.csv")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
