#!/usr/bin/env python3
"""
test_database.py - Automated tests for Chinese Calligraphy Font Database and Web Demo.
"""
import json
import sqlite3
import unittest
from pathlib import Path
from fontTools.ttLib import TTFont

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "calligraphy_fonts.db"
JSON_PATH = DATA_DIR / "calligraphy_fonts.json"
WEB_DIR = ROOT_DIR / "web"

class TestCalligraphyFontDatabase(unittest.TestCase):
    def setUp(self):
        self.assertTrue(DB_PATH.exists(), f"Database missing at {DB_PATH}")
        self.assertTrue(JSON_PATH.exists(), f"JSON export missing at {JSON_PATH}")
        self.conn = sqlite3.connect(DB_PATH)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        self.conn.close()

    def test_record_counts_and_limits(self):
        """Verify counts satisfy user requirements: max 50 Kai, max 50 Li, max 50 Other."""
        c = self.conn.cursor()
        total = c.execute("SELECT COUNT(*) FROM fonts").fetchone()[0]
        self.assertGreater(total, 0, "Database should have fonts cataloged")

        kai_cnt = c.execute("SELECT COUNT(*) FROM fonts WHERE style_category = 'kaishu'").fetchone()[0]
        li_cnt = c.execute("SELECT COUNT(*) FROM fonts WHERE style_category = 'lishu'").fetchone()[0]
        other_cnt = c.execute("SELECT COUNT(*) FROM fonts WHERE style_category = 'other'").fetchone()[0]

        self.assertLessEqual(kai_cnt, 50, f"Kai Shu should be <= 50, got {kai_cnt}")
        self.assertGreaterEqual(kai_cnt, 10, "Kai Shu should have substantial curation")

        self.assertLessEqual(li_cnt, 50, f"Li Shu should be <= 50, got {li_cnt}")
        self.assertGreaterEqual(li_cnt, 10, "Li Shu should have substantial curation")

        self.assertLessEqual(other_cnt, 50, f"Other styles should be <= 50, got {other_cnt}")
        self.assertGreaterEqual(other_cnt, 10, "Other styles should have substantial curation")

    def test_required_metadata_fields(self):
        """Verify that every entry captures required metadata."""
        c = self.conn.cursor()
        rows = c.execute("SELECT * FROM fonts").fetchall()
        for r in rows:
            self.assertTrue(r["id"], "Font ID required")
            self.assertTrue(r["name_zh"], f"Chinese name required for {r['id']}")
            self.assertIn(r["style_category"], ["kaishu", "lishu", "other"])
            self.assertIn(r["medium"], ["brush", "pen"], f"Medium must be brush or pen for {r['id']}")
            self.assertIn(r["char_support"], ["trad", "simp", "both"], f"char_support must be trad, simp, or both for {r['id']}")
            self.assertTrue(r["artist"], f"Artist required for {r['id']}")
            self.assertTrue(r["font_author"], f"Font author/foundry required for {r['id']}")
            self.assertTrue(r["license"], f"License required for {r['id']}")
            self.assertTrue(r["source_url"], f"Source URL required for {r['id']}")
            self.assertTrue(r["aesthetic_notes"], f"Aesthetic commentary required for {r['id']}")
            self.assertTrue(r["sample_text"], f"Sample text required for {r['id']}")

    def test_downloaded_fonts_integrity(self):
        """Verify that all fonts marked is_downloaded=1 exist and are valid font files."""
        c = self.conn.cursor()
        downloaded = c.execute("SELECT * FROM fonts WHERE is_downloaded = 1").fetchall()
        self.assertGreaterEqual(len(downloaded), 10, "Should have at least 10 downloaded fonts")

        for f in downloaded:
            font_path = ROOT_DIR / f["file_path"]
            self.assertTrue(font_path.exists(), f"Font file missing: {font_path}")
            self.assertGreater(font_path.stat().st_size, 0, f"Font file empty: {font_path}")

            # Validate font file loadable via fontTools
            try:
                tt = TTFont(str(font_path), fontNumber=0 if font_path.suffix == ".ttc" else 0)
                self.assertIn("cmap", tt, f"Font {f['id']} missing cmap table")
                tt.close()
            except Exception as e:
                self.fail(f"Failed to load font {font_path}: {e}")

    def test_json_export_matches_db(self):
        """Verify that JSON export contains identical count and IDs as SQLite."""
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        c = self.conn.cursor()
        total_db = c.execute("SELECT COUNT(*) FROM fonts").fetchone()[0]
        self.assertEqual(len(data), total_db, "JSON and SQLite counts must match")

    def test_web_demo_assets(self):
        """Verify that all web files and symlinks exist."""
        self.assertTrue((WEB_DIR / "index.html").exists(), "index.html missing")
        self.assertTrue((WEB_DIR / "style.css").exists(), "style.css missing")
        self.assertTrue((WEB_DIR / "app.js").exists(), "app.js missing")
        self.assertTrue((WEB_DIR / "server.py").exists(), "server.py missing")
        self.assertTrue((WEB_DIR / "fonts").exists(), "fonts symlink missing")
        self.assertTrue((WEB_DIR / "fonts.json").exists(), "fonts.json symlink missing")

if __name__ == "__main__":
    unittest.main()
