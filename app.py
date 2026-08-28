#!/usr/bin/env python3
"""
Dashboard web pour le classement combiné ErgRace de plusieurs clubs.
"""

import os
import threading
import time
from datetime import datetime

from flask import Flask, jsonify, render_template

from aggregator import load_config, build_combined_results

app = Flask(__name__)

state = {"data": {"rows": [], "clubs": [], "categories": []}, "updated_at": None, "updating": False}
state_lock = threading.Lock()
_thread_started = False
_thread_lock = threading.Lock()


def refresh_loop():
    while True:
        config = load_config()
        with state_lock:
            state["updating"] = True
        data = build_combined_results(config)
        with state_lock:
            state["data"] = data
            state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            state["updating"] = False
        time.sleep(config.get("refresh_seconds", 60))


def start_background_thread():
    global _thread_started
    with _thread_lock:
        if not _thread_started:
            t = threading.Thread(target=refresh_loop, daemon=True)
            t.start()
            _thread_started = True


start_background_thread()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/results")
def api_results():
    with state_lock:
        return jsonify({
            "rows": state["data"]["rows"],
            "clubs": state["data"]["clubs"],
            "categories": state["data"]["categories"],
            "updated_at": state["updated_at"],
            "updating": state["updating"],
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
