#!/usr/bin/env python3
"""
db_manager.py - CLI tool to inspect, search, and manage the Chinese Calligraphy Font Database.
"""
import argparse
import json
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "data" / "calligraphy_fonts.db"

def get_connection():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run scripts/populate_full_database.py first.")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def list_fonts(category=None, medium=None, artist=None, downloaded_only=False):
    conn = get_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM fonts WHERE 1=1"
    params = []

    if category:
        query += " AND style_category = ?"
        params.append(category)
    if medium:
        query += " AND medium = ?"
        params.append(medium)
    if artist:
        query += " AND (artist LIKE ? OR name_zh LIKE ? OR historical_reference LIKE ?)"
        params.extend([f"%{artist}%", f"%{artist}%", f"%{artist}%"])
    if downloaded_only:
        query += " AND is_downloaded = 1"

    query += " ORDER BY style_category, is_downloaded DESC, name_zh ASC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def show_stats():
    conn = get_connection()
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM fonts").fetchone()[0]
    downloaded = c.execute("SELECT COUNT(*) FROM fonts WHERE is_downloaded = 1").fetchone()[0]
    
    by_category = c.execute("SELECT style_category, COUNT(*) FROM fonts GROUP BY style_category").fetchall()
    by_medium = c.execute("SELECT medium, COUNT(*) FROM fonts GROUP BY medium").fetchall()
    by_dynasty = c.execute("SELECT dynasty_era, COUNT(*) FROM fonts GROUP BY dynasty_era ORDER BY COUNT(*) DESC LIMIT 8").fetchall()
    conn.close()

    print("\n=== Calligraphy Font Database Statistics ===")
    print(f"Total Fonts: {total} (Downloaded offline: {downloaded})")
    print("\nBy Style Category:")
    for cat, cnt in by_category:
        print(f"  {cat:15}: {cnt}")
    print("\nBy Writing Medium:")
    for med, cnt in by_medium:
        print(f"  {med:15}: {cnt}")
    print("\nTop Dynasties / Eras:")
    for dyn, cnt in by_dynasty:
        print(f"  {dyn:25}: {cnt}")
    print("=============================================\n")

def main():
    parser = argparse.ArgumentParser(description="Calligraphy Font Database Manager")
    parser.add_argument("--list", action="store_true", help="List all fonts")
    parser.add_argument("--category", choices=["kaishu", "lishu", "other"], help="Filter by category")
    parser.add_argument("--medium", choices=["brush", "pen"], help="Filter by medium")
    parser.add_argument("--artist", help="Filter by artist name or keyword")
    parser.add_argument("--downloaded", action="store_true", help="Show only downloaded fonts")
    parser.add_argument("--stats", action="store_true", help="Show summary statistics")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    fonts = list_fonts(
        category=args.category,
        medium=args.medium,
        artist=args.artist,
        downloaded_only=args.downloaded
    )

    if args.json:
        print(json.dumps(fonts, ensure_ascii=False, indent=2))
        return

    print(f"\nFound {len(fonts)} fonts:\n")
    print(f"{'ID':25} | {'NAME (ZH)':18} | {'STYLE':18} | {'MEDIUM':6} | {'ARTIST':20} | {'DL':2}")
    print("-" * 105)
    for f in fonts:
        dl_mark = "✓" if f["is_downloaded"] else " "
        print(f"{f['id'][:25]:25} | {f['name_zh'][:18]:18} | {f['style_display'][:18]:18} | {f['medium']:6} | {f['artist'][:20]:20} | {dl_mark}")

if __name__ == "__main__":
    main()
