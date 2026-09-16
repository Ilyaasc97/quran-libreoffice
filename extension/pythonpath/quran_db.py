# -*- coding: utf-8 -*-
"""
Quran Database Access Module for LibreOffice Extension
Pure Python implementation using pre-indexed JSON data.
Completely eliminates SQLite3 C-extension / DLL loading conflicts in LibreOffice on Windows.
"""

import os
import json
import re
from collections import defaultdict

BASMALAH = "بِسۡمِ ٱللَّهِ ٱلرَّحۡمَٰنِ ٱلرَّحِيمِ"

def normalize_arabic(text):
    if not text:
        return ""
    text = re.sub(r'[\u064B-\u065F\u0670\u06D6-\u06ED]', '', text)
    text = re.sub(r'[أإآٱ]', 'ا', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'ة', 'ه', text)
    return text.strip()

def get_data_path():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(current_dir, "..", "data", "quran.json"),
        os.path.join(current_dir, "data", "quran.json"),
        os.path.join(os.path.dirname(current_dir), "data", "quran.json")
    ]
    for c in candidates:
        if os.path.exists(c):
            return os.path.abspath(c)
    return os.path.abspath(candidates[0])

# Process-level singleton cache
_CACHED_DATA = None

class QuranDB:
    def __init__(self, data_path=None):
        global _CACHED_DATA
        if _CACHED_DATA is None:
            self.data_path = data_path or get_data_path()
            if not os.path.exists(self.data_path):
                raise FileNotFoundError(f"Quran data file not found at: {self.data_path}")
            with open(self.data_path, "r", encoding="utf-8") as f:
                _CACHED_DATA = json.load(f)

        self.surahs = _CACHED_DATA.get("surahs", [])
        self.ayahs = _CACHED_DATA.get("ayahs", [])

        # Build fast lookup indexes
        self.surahs_by_no = {s["sura_no"]: s for s in self.surahs}
        self.ayahs_by_surah = defaultdict(list)
        for a in self.ayahs:
            self.ayahs_by_surah[a["sura_no"]].append(a)

    def get_all_surahs(self):
        """Returns a list of all 114 surahs."""
        return self.surahs

    def get_surah(self, sura_no):
        """Returns info for a specific surah."""
        return self.surahs_by_no.get(int(sura_no))

    def get_ayahs(self, sura_no, from_ayah=1, to_ayah=None):
        """Returns verses within the specified range."""
        sura_no = int(sura_no)
        from_ayah = int(from_ayah)
        surah_ayahs = self.ayahs_by_surah.get(sura_no, [])

        if to_ayah is None:
            return [a for a in surah_ayahs if a["aya_no"] >= from_ayah]
        else:
            to_ayah = int(to_ayah)
            return [a for a in surah_ayahs if from_ayah <= a["aya_no"] <= to_ayah]

    def search(self, text, limit=50):
        """Search Quran verses by normalized Arabic text."""
        norm_query = normalize_arabic(text)
        if not norm_query:
            return []

        results = []
        for a in self.ayahs:
            search_str = a.get("search_text") or normalize_arabic(a.get("aya_text_emlaey", ""))
            if norm_query in search_str:
                s = self.surahs_by_no.get(a["sura_no"], {})
                res_item = dict(a)
                res_item["sura_name_ar"] = s.get("sura_name_ar", "")
                results.append(res_item)
                if len(results) >= limit:
                    break
        return results

    def build_quran_payload(self, sura_no, from_ayah, to_ayah,
                            include_basmalah=True,
                            include_header=False,
                            line_per_ayah=False,
                            include_brackets=True,
                            include_qala=True,
                            include_ref=True):
        """
        Builds formatted sections for insertion matching Islamic academic citation:
        قَالَ تَعَالَى: ﴿ ... ﴾ [اسم السورة: الآيات]
        """
        sura_no = int(sura_no)
        from_ayah = int(from_ayah)
        to_ayah = int(to_ayah)

        surah = self.get_surah(sura_no)
        if not surah:
            return None

        ayahs = self.get_ayahs(sura_no, from_ayah, to_ayah)
        if not ayahs:
            return None

        # Standalone Header if requested
        header_text = None
        if include_header:
            if from_ayah == to_ayah:
                header_text = f"سُورَةُ {surah['sura_name_ar']} - الآية {from_ayah}"
            else:
                header_text = f"سُورَةُ {surah['sura_name_ar']} - الآيات {from_ayah} إلى {to_ayah}"

        # Basmalah if requested
        basmalah_text = None
        if include_basmalah and from_ayah == 1 and sura_no not in (1, 9):
            basmalah_text = BASMALAH

        # Qala Taala prefix
        qala_text = "قَالَ تَعَالَى:" if include_qala else None

        # Citation reference at end: [الفَاتِحة: 1-4] or [الفَاتِحة: 4]
        ref_text = None
        if include_ref:
            sura_name = surah["sura_name_ar"]
            RLM = "\u200F"
            if from_ayah == to_ayah:
                ref_text = f"{RLM}[{sura_name}: {RLM}{from_ayah}{RLM}]{RLM}"
            else:
                ref_text = f"{RLM}[{sura_name}: {RLM}{from_ayah}-{to_ayah}{RLM}]{RLM}"

        verse_texts = [a["aya_text"].strip() for a in ayahs]

        # Authentic King Fahd Complex ornate Quran brackets (KFGQPC):
        # U+FD5F: Opens and embraces text from the right in RTL
        # U+FD5E: Closes and embraces text from the left in RTL
        OPEN_BRACKET = "\uFD5F"   # ﵟ (Embraces from right)
        CLOSE_BRACKET = "\uFD5E"  # ﵞ (Embraces from left)

        sep = "\n" if line_per_ayah else " "
        body_text = sep.join(verse_texts)
        if include_brackets:
            body_text = f"{OPEN_BRACKET} {body_text} {CLOSE_BRACKET}"

        # Build combined quote line
        quote_parts = []
        if qala_text:
            quote_parts.append(qala_text)
        quote_parts.append(body_text)
        if ref_text:
            quote_parts.append(ref_text)
        main_line = "\u200F" + " ".join(quote_parts) + "\u200F"

        parts = []
        if header_text:
            parts.append(header_text)
        if basmalah_text:
            parts.append(basmalah_text)
        parts.append(main_line)

        combined = "\n".join(parts)

        return {
            "surah": surah,
            "from_ayah": from_ayah,
            "to_ayah": to_ayah,
            "header": header_text,
            "basmalah": basmalah_text,
            "qala_taala": qala_text,
            "reference": ref_text,
            "verses": verse_texts,
            "body_text": body_text,
            "main_line": main_line,
            "combined_text": combined
        }
