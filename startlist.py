import os
import json
import pandas as pd
from io import BytesIO

DATA_FILE = "/tmp/startlist_data.json"

def load_startlist_data():
    if not os.path.exists(DATA_FILE):
        return {"files": [], "entries": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"files": [], "entries": []}

def save_startlist_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving: {e}")

def clear_startlist_data():
    save_startlist_data({"files": [], "entries": []})

def parse_engagement_file(file_storage):
    filename = file_storage.filename
    content = file_storage.read()

    try:
        df = pd.read_excel(BytesIO(content), header=None)

        # استخراج اسم النادي
        club_name = "نادي غير محدد"
        for r in range(min(15, len(df))):
            row_vals = [str(x) for x in df.iloc[r].values if pd.notna(x)]
            row_str = " ".join(row_vals)
            if any(k in row_str for k in ["Club", "club", "نادي"]):
                clean = row_str.replace("Club :", "").replace("Club:", "").replace("N°", "").strip()
                if clean:
                    club_name = clean
                    break

        # تحديد رؤوس الصفوف
        header_row_idx = 7
        for r in range(min(20, len(df))):
            row_vals = [str(x) for x in df.iloc[r].values if pd.notna(x)]
            row_str = " ".join(row_vals)
            if "Nom" in row_str or "Prénom" in row_str or "الاسم" in row_str:
                header_row_idx = r
                break

        header_row = [str(c).strip() for c in df.iloc[header_row_idx].values]
        
        start_cat_idx = 5
        for idx_col, h_text in enumerate(header_row):
            if "licence" in h_text.lower() or "رخصة" in h_text:
                start_cat_idx = idx_col + 1
                break

        category_columns = header_row[start_cat_idx:]
        entries = []

        for idx in range(header_row_idx + 1, len(df)):
            row = df.iloc[idx]
            nom = str(row.iloc[1]).strip() if len(row) > 1 and pd.notna(row.iloc[1]) else ""
            prenom = str(row.iloc[2]).strip() if len(row) > 2 and pd.notna(row.iloc[2]) else ""

            if not nom or nom.lower() in ["nan", "none"] or nom.isdigit():
                continue

            full_name = f"{nom} {prenom}".strip()
            selected_category = "عام"

            for c_offset, cat_name in enumerate(category_columns):
                col_pos = start_cat_idx + c_offset
                if col_pos < len(row):
                    val = str(row.iloc[col_pos]).strip().lower()
                    if val in ['x', '1', 'true', '1.0']:
                        selected_category = cat_name
                        break

            entries.append({
                "participant": full_name,
                "club": club_name,
                "category": selected_category
            })

        return filename, club_name, entries

    except Exception as e:
        raise Exception(f"فشل قراءة الملف: {str(e)}")

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
        cat = entry.get("category", "عام")
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
