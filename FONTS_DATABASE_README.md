# Open-Source Chinese Calligraphy Font Database & Interactive Studio

This worktree contains a curated database of artistic open-source Chinese calligraphy fonts, representative offline font downloads, and an interactive browser-based calligraphy sandbox and catalog demo.

## Overview & Highlights

- **Aesthetic Focus**: Curated exclusively for authentic artistic calligraphy with traceable provenance—derived from historical rubbings, stone tablets, and master manuscripts (e.g. Yan Zhenqing 颜真卿, Liu Gongquan 柳公权, Ouyang Xun 欧阳询, Zhao Mengfu 赵孟頫, Wang Xizhi 王羲之, Cao Quan Bei 曹全碑, Zhang Qian Bei 张迁碑, Su Shi 苏轼, Mi Fu 米芾, Huai Su 怀素) or authored by recognized calligraphers (Ma Shan Zheng 马善政, Wei Zimang 韦子莽, Liu Jian 刘流江, Rong Jingxian 荣景先, Aoyagi Kouzan 青柳衡山).
- **Style Categories**:
  - **Kai Shu (楷书)**: 27 styles (within max 50 limit)
  - **Li Shu (隶书)**: 16 styles (within max 50 limit)
  - **Other Styles (行书, 草书, 魏碑, 篆书, 钢笔/硬笔)**: 19 styles (within max 50 limit)
- **Writing Mediums**:
  - **Brush (毛笔)**: 57 styles
  - **Hard Pen / Steel Pen (硬笔/钢笔)**: 5 styles
- **Offline Downloaded Fonts**: 17 complete TrueType/OpenType font files stored locally in `data/fonts/` for immediate offline rendering and live browser preview.
- **Licenses**: Strictly open source and free commercial licenses (SIL Open Font License 1.1, GNU GPL 2.0 with font exception, Arphic Public License, and Public Domain).

---

## Directory Structure

```text
├── data/
│   ├── calligraphy_fonts.db        # SQLite database
│   ├── calligraphy_fonts.json      # Structured JSON export
│   ├── fonts/                      # 17 locally downloaded font files (.ttf, .ttc)
│   └── licenses/                   # Upstream license files
├── scripts/
│   ├── download_fonts.py           # Automated font downloader and extractor
│   ├── populate_full_database.py   # Database generator & catalog builder
│   └── db_manager.py               # CLI tool to query, filter, and inspect database
├── web/
│   ├── index.html                  # Classical Chinese aesthetics web demo
│   ├── style.css                   # Xuan paper, Gold fleck, and Stone Rubbing themes
│   ├── app.js                      # Dynamic @font-face loader and interactive sandbox
│   ├── server.py                   # Local web server
│   ├── fonts -> ../data/fonts      # Symlink for web assets
│   └── fonts.json -> ../data/...   # Symlink for web assets
└── tests/
    └── test_database.py            # Unit tests for database integrity & font validity
```

---

## Quick Start: Interactive Calligraphy Demo Webpage

Launch the local web server:

```bash
python3 web/server.py 8088
```

Open your browser at **`http://localhost:8088`** to experience:
1. **书斋临摹台 (Interactive Calligraphy Sandbox)**:
   - Live custom text input with traditional calligraphy presets (*永字八法*, *春江花月夜*, *王维五言对联*, *兰亭集序*, *赤壁怀古*, *厚德载物*).
   - Layout toggle: Traditional vertical right-to-left (*竖排右起*) vs modern horizontal (*横排*).
   - Paper atmosphere switcher:
     - **澄心堂宣纸** (Warm natural Xuan paper)
     - **洒金熟宣** (Gold fleck paper)
     - **汉唐碑帖拓片** (Black stone rubbing with chalk-white strokes)
   - Dynamic font switcher with 17 offline @font-face fonts.
2. **历代书法字库全库鉴赏 (Font Catalog Browser)**:
   - Filter by style (*楷书*, *隶书*, *行草/篆/魏碑/硬笔*).
   - Filter by medium (*毛笔*, *硬笔*).
   - Filter by availability (*本地已就绪* vs *全库收录*).
   - Real-time text search by calligrapher, font name, and reference work.
   - Click "✍️ 载入临摹台挥毫" on any card to immediately test that font in the studio.

---

## CLI Database Manager

Inspect and query the database directly from the terminal:

```bash
# View summary statistics
python3 scripts/db_manager.py --stats

# List all cataloged fonts
python3 scripts/db_manager.py --list

# Filter by style category
python3 scripts/db_manager.py --category lishu
python3 scripts/db_manager.py --category kaishu

# Filter by medium (brush vs pen)
python3 scripts/db_manager.py --medium pen

# Filter by artist / calligrapher keyword
python3 scripts/db_manager.py --artist 颜真卿
python3 scripts/db_manager.py --artist 王羲之
python3 scripts/db_manager.py --artist 曹全碑

# Show only downloaded fonts ready for offline rendering
python3 scripts/db_manager.py --downloaded

# Output query results as structured JSON
python3 scripts/db_manager.py --category kaishu --downloaded --json
```

---

## Automated Validation

Run the test suite:

```bash
/home/kevin/Workspace/calligraphy/.venv/bin/python -m unittest tests/test_database.py
```

Tests verify:
1. Category limits (strictly `<= 50` Kai Shu, `<= 50` Li Shu, `<= 50` Other styles).
2. Non-empty mandatory metadata (source, style, medium, artist, author, license, aesthetic notes, sample text).
3. Font integrity of all downloaded fonts (loading `cmap` tables via `fontTools`).
4. JSON export synchronization with SQLite.
5. Presence and accessibility of all web assets.
