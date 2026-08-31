from flask import Flask, render_template, request, jsonify, send_file
import os
import io

from startlist import (
    parse_engagement_file, add_file_entries, 
    load_startlist_data, clear_startlist_data, group_by_category
)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/startlist')
def startlist_page():
    return render_template('startlist.html')

@app.route('/api/startlist/upload', methods=['POST'])
def api_upload():
    try:
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files uploaded'}), 400

        results = []
        for file in files:
            if file.filename == '':
                continue
            try:
                filename, club_name, entries = parse_engagement_file(file)
                add_file_entries(filename, club_name, entries)
                results.append({'filename': filename, 'club': club_name, 'count': len(entries)})
            except Exception as e:
                results.append({'filename': file.filename, 'error': str(e)})

        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/startlist/data', methods=['GET'])
def api_data():
    data = load_startlist_data()
    races = group_by_category(data.get('entries', []))
    return jsonify({
        'files': data.get('files', []),
        'total_entries': len(data.get('entries', [])),
        'races': races
    })

@app.route('/api/startlist/clear', methods=['POST'])
def api_clear():
    clear_startlist_data()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
