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

    # قراءة شيت Excel بالكامل بدون افتراض هيدر ثابت
    df = pd.read_excel(BytesIO(content), header=None)

    # 1. البحث الآلي عن اسم النادي في أول 10 أسطر
    club_name = "نادي غير محدد"
    for r in range(min(10, len(df))):
        for c in range(len(df.columns)):
            val = str(df.iloc[r, c])
            if "Club" in val or "club" in val or "نادي" in val:
                # أخذ القيمة أو الخلية المجاورة لها
                next_val = str(df.iloc[r, c + 1]) if c + 1 < len(df.columns) and pd.notna(df.iloc[r, c + 1]) else ""
                combined = f"{val} {next_val}".strip()
                club_name = combined.replace("Club :", "").replace("Club:", "").replace("N°", "").strip()
                break
        if club_name != "نادي غير محدد":
            break

    # 2. البحث عن السطر الذي يحتوي على أسماء الأعمدة (Nom / Prénom)
    header_row_idx = None
    for r in range(len(df)):
        row_str = " ".join([str(x) for x in df.iloc[r].values if pd.notna(x)])
        if "Nom" in row_str or "Prénom" in row_str:
            header_row_idx = r
            break

    if header_row_idx is None:
        raise ValueError("لم يتم العثور على جدول المشاركين داخل الملف")

    header_row = [str(c).strip() for c in df.iloc[header_row_idx].values]
    
    # تحديد موقع الفئات (تأتي عادة بعد رقم الرخصة N°licence)
    start_cat_idx = 5
    for idx_col, h_text in enumerate(header_row):
        if "licence" in h_text.lower():
            start_cat_idx = idx_col + 1
            break

    category_columns = header_row[start_cat_idx:]

    entries = []

    # 3. قراءة المشاركين من السطر التالي للهيدر
    for idx in range(header_row_idx + 1, len(df)):
        row = df.iloc[idx]
        nom = row.iloc[1] if len(row) > 1 else None
        prenom = row.iloc[2] if len(row) > 2 else None

        if pd.isna(nom) or str(nom).strip() == "" or str(nom).strip().isdigit():
            continue

        full_name = f"{str(nom).strip()} {str(prenom).strip() if pd.notna(prenom) else ''}".strip()

        # استخراج الفئة المفعلة بـ x
        selected_category = "غير محدد"
        for c_offset, cat_name in enumerate(category_columns):
            col_pos = start_cat_idx + c_offset
            if col_pos < len(row):
                val = str(row.iloc[col_pos]).strip().lower()
                if val in ['x', '1', 'true', '1.0']:
                    selected_category = cat_name
                    break

        entries.append({
            "participant": full_name,
            "club": club_name if club_name else "نادي غير محدد",
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
