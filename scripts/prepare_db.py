import json
import sqlite3
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

def normalize_arabic(text):
    if not text:
        return ""
    # Remove tashkeel and Quranic annotations
    text = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED]', '', text)
    # Unify Alefs
    text = re.sub(r'[أإآٱ]', 'ا', text)
    # Unify Yaa / Alef Maqsura
    text = re.sub(r'ى', 'ي', text)
    # Unify Taa Marbutah
    text = re.sub(r'ة', 'ه', text)
    return text.strip()

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
source_json = os.path.join(base_dir, "assets", "data", "UthmanicHafs_v2-0", "UthmanicHafs_v2-0 data", "hafsData_v2-0.json")
out_dir = os.path.join(base_dir, "extension", "data")
os.makedirs(out_dir, exist_ok=True)
out_db = os.path.join(out_dir, "quran.db")

with open(source_json, "r", encoding="utf-8") as f:
    records = json.load(f)

print(f"Loaded {len(records)} records.")

if os.path.exists(out_db):
    os.remove(out_db)

conn = sqlite3.connect(out_db)
cur = conn.cursor()

cur.execute("""
CREATE TABLE surahs (
    sura_no INTEGER PRIMARY KEY,
    sura_name_ar TEXT NOT NULL,
    sura_name_en TEXT NOT NULL,
    ayah_count INTEGER NOT NULL,
    first_page INTEGER NOT NULL
)
""")

cur.execute("""
CREATE TABLE ayahs (
    id INTEGER PRIMARY KEY,
    sura_no INTEGER NOT NULL,
    aya_no INTEGER NOT NULL,
    jozz INTEGER NOT NULL,
    page INTEGER NOT NULL,
    line_start INTEGER,
    line_end INTEGER,
    aya_text TEXT NOT NULL,
    aya_text_emlaey TEXT NOT NULL,
    search_text TEXT NOT NULL
)
""")

cur.execute("CREATE INDEX idx_ayahs_sura_aya ON ayahs(sura_no, aya_no)")
cur.execute("CREATE INDEX idx_ayahs_search ON ayahs(search_text)")

surahs_map = {}
for r in records:
    s_no = r["sura_no"]
    if s_no not in surahs_map:
        surahs_map[s_no] = {
            "name_ar": r["sura_name_ar"],
            "name_en": r["sura_name_en"],
            "ayah_count": 0,
            "first_page": r["page"]
        }
    surahs_map[s_no]["ayah_count"] += 1

    norm = normalize_arabic(r["aya_text_emlaey"])
    cur.execute("""
    INSERT INTO ayahs (id, sura_no, aya_no, jozz, page, line_start, line_end, aya_text, aya_text_emlaey, search_text)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        r["id"],
        r["sura_no"],
        r["aya_no"],
        r["jozz"],
        r["page"],
        r.get("line_start"),
        r.get("line_end"),
        r["aya_text"],
        r["aya_text_emlaey"],
        norm
    ))

for s_no, info in sorted(surahs_map.items()):
    cur.execute("""
    INSERT INTO surahs (sura_no, sura_name_ar, sura_name_en, ayah_count, first_page)
    VALUES (?, ?, ?, ?, ?)
    """, (s_no, info["name_ar"], info["name_en"], info["ayah_count"], info["first_page"]))

conn.commit()
conn.close()

db_size = os.path.getsize(out_db)
print(f"Database successfully updated with search_text at {out_db} ({db_size / (1024*1024):.2f} MB)")
