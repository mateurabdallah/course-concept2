#!/usr/bin/env python3
"""Dashboard web: classement général des clubs + détail par course (catégorie)."""

import os
import time

from flask import Flask, jsonify, render_template

from aggregator import load_config, build_combined_results

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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
