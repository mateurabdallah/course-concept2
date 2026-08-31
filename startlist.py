import os
import json
import pandas as pd
from io import BytesIO

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "startlist_data.json")


def load_startlist_data():
    if not os.path.exists(DATA_FILE):
        return {"files": [], "entries": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"files": [], "entries": []}


def save_startlist_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def clear_startlist_data():
    save_startlist_data({"files": [], "entries": []})


def parse_engagement_file(file_storage):
    filename = file_storage.filename
    content = file_storage.read()
    
    df = pd.read_excel(BytesIO(content), header=None)
    
    club_raw = str(df.iloc[4, 1]) if pd.notna(df.iloc[4, 1]) else "نادي غير محدد"
    club_name = club_raw.replace("Club :", "").strip()
    if not club_name:
        club_name = "نادي غير محدد"

    header_row = [str(c).strip() for c in df.iloc[7].values]
    category_columns = header_row[5:]

    entries = []

    for idx in range(8, len(df)):
        row = df.iloc[idx]
        nom = row.iloc[1]
        prenom = row.iloc[2]
        
        if pd.isna(nom) or str(nom).strip() == "":
            continue
            
        full_name = f"{str(nom).strip()} {str(prenom).strip()}"
        
        selected_category = "غير محدد"
        for c_idx, cat_name in enumerate(category_columns, start=5):
            val = str(row.iloc[c_idx]).strip().lower()
            if val in ['x', '1', 'true']:
                selected_category = cat_name
                break
                
        entries.append({
            "participant": full_name,
            "club": club_name,
            "category": selected_category
        })

    return filename, club_name, entries


def add_file_entries(filename, club_name, new_entries):
    data = load_startlist_data()
    
    data["files"] = [f for f in data["files"] if f.get("filename") != filename]
    data["entries"] = [e for e in data["entries"] if e.get("_filename") != filename]
    
    data["files"].append({"filename": filename, "club": club_name, "count": len(new_entries)})
    
    for entry in new_entries:
        entry["_filename"] = filename
        data["entries"].append(entry)
        
    save_startlist_data(data)


def group_by_category(entries):
    categories = {}
    for entry in entries:
        cat = entry.get("category", "غير محدد")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(entry)
        
    races = []
    for cat in sorted(categories.keys()):
        races.append({
            "category": cat,
            "entries": categories[cat]
        })
    return races
