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


@app.route("/startlist")
def startlist_page():
    return render_template("startlist.html")


@app.route("/api/startlist", methods=["GET"])
def get_startlist():
    data = load_startlist_data()
    races = group_by_category(data.get("entries", []))
    return jsonify({
        "files": data.get("files", []),
        "total": len(data.get("entries", [])),
        "races": races
    })


@app.route("/api/startlist/upload", methods=["POST"])
def upload_startlist():
    files = request.files.getlist("files")
    results = []
    for f in files:
        if not f.filename:
            continue
        try:
            filename, club, entries = parse_engagement_file(f)
            add_file_entries(filename, club, entries)
            results.append({"filename": filename, "club": club, "count": len(entries)})
        except Exception as e:
            results.append({"filename": f.filename, "error": str(e)})
    return jsonify({"results": results})


@app.route("/api/startlist/clear", methods=["POST"])
def clear_startlist():
    clear_startlist_data()
    return jsonify({"status": "ok"})


@app.route("/api/startlist/export.csv", methods=["GET"])
def export_startlist_csv():
    data = load_startlist_data()
    entries = data.get("entries", [])
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Participant", "Club"])
    for e in entries:
        writer.writerow([e.get("category", ""), e.get("participant", ""), e.get("club", "")])
        
    mem = io.BytesIO()
    mem.write(output.getvalue().encode("utf-8-sig"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="startlist.csv")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
