import os
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from startlist import (
    parse_engagement_file, add_file_entries, 
    load_startlist_data, clear_startlist_data, group_by_category
)

app = Flask(__name__)
app.secret_key = 'secret_key_for_startlist'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

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
        if not files or files[0].filename == '':
            return jsonify({'error': 'لم يتم اختيار أي ملف'}), 400

        results = []
        for file in files:
            try:
                filename, club_name, entries = parse_engagement_file(file)
                add_file_entries(filename, club_name, entries)
                results.append({'filename': filename, 'club': club_name, 'count': len(entries)})
            except Exception as e:
                return jsonify({'error': f"خطأ في {file.filename}: {str(e)}"}), 400

        return jsonify({'status': 'success', 'results': results}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/startlist/data', methods=['GET'])
def api_data():
    try:
        data = load_startlist_data()
        races = group_by_category(data.get('entries', []))
        return jsonify({
            'files': data.get('files', []),
            'total_entries': len(data.get('entries', [])),
            'races': races
        }), 200
    except Exception as e:
        return jsonify({'files': [], 'total_entries': 0, 'races': [], 'error': str(e)}), 200

@app.route('/api/startlist/clear', methods=['POST'])
def api_clear():
    try:
        clear_startlist_data()
        return jsonify({'status': 'ok'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
