# -*- coding: utf-8 -*-
"""
Package Builder for Quran LibreOffice Extension (.oxt)
"""

import os
import zipfile
import sys

def build_oxt():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    ext_dir = os.path.join(root_dir, "extension")
    out_oxt = os.path.join(root_dir, "quran_libreoffice.oxt")

    if not os.path.exists(ext_dir):
        print(f"Error: extension directory not found at {ext_dir}")
        sys.exit(1)

    if os.path.exists(out_oxt):
        os.remove(out_oxt)

    print(f"Building {out_oxt} from {ext_dir}...")

    file_count = 0
    with zipfile.ZipFile(out_oxt, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(ext_dir):
            # Skip pycache and hidden directories
            dirs[:] = [d for d in dirs if d != "__pycache__" and not d.startswith(".")]

            for f in files:
                if f.endswith(".pyc") or f.endswith(".pyo") or f.startswith("."):
                    continue

                full_path = os.path.join(root, f)
                rel_path = os.path.relpath(full_path, ext_dir)
                z.write(full_path, rel_path)
                file_count += 1
                print(f"  + Added: {rel_path}")

    size_mb = os.path.getsize(out_oxt) / (1024 * 1024)
    print(f"\nSUCCESS: Created {out_oxt}")
    print(f"Total files: {file_count}, Total size: {size_mb:.2f} MB")

if __name__ == "__main__":
    build_oxt()
