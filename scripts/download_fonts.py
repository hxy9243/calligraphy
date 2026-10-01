#!/usr/bin/env python3
"""
download_fonts.py - Download and verify open-source calligraphy fonts.
"""
import io
import os
import shutil
import urllib.request
import zipfile
from pathlib import Path
import py7zr

WORKTREE_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = WORKTREE_ROOT / "data" / "fonts"
LICENSES_DIR = WORKTREE_ROOT / "data" / "licenses"

FONTS_DIR.mkdir(parents=True, exist_ok=True)
LICENSES_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def download_file(url: str, dest_path: Path):
    if dest_path.exists() and dest_path.stat().st_size > 0:
        print(f"[SKIP] {dest_path.name} already exists ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")
        return
    print(f"[DOWNLOADING] {url} -> {dest_path.name}...")
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest_path, "wb") as f:
        shutil.copyfileobj(resp, f)
    print(f"[DONE] {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")

def download_google_fonts():
    google_fonts = [
        ("mashanzheng", "MaShanZheng-Regular.ttf", "MaShanZheng.ttf"),
        ("zhimangxing", "ZhiMangXing-Regular.ttf", "ZhiMangXing.ttf"),
        ("liujianmaocao", "LiuJianMaoCao-Regular.ttf", "LiuJianMaoCao.ttf"),
        ("longcang", "LongCang-Regular.ttf", "LongCang.ttf"),
        ("yujiboku", "YujiBoku-Regular.ttf", "YujiBoku.ttf"),
        ("kleeone", "KleeOne-Regular.ttf", "KleeOne.ttf"),
    ]
    for repo_name, remote_name, local_name in google_fonts:
        font_url = f"https://raw.githubusercontent.com/google/fonts/main/ofl/{repo_name}/{remote_name}"
        license_url = f"https://raw.githubusercontent.com/google/fonts/main/ofl/{repo_name}/OFL.txt"
        try:
            download_file(font_url, FONTS_DIR / local_name)
            license_dest = LICENSES_DIR / f"{local_name}.OFL.txt"
            if not license_dest.exists():
                download_file(license_url, license_dest)
        except Exception as e:
            print(f"[ERROR] Failed downloading {local_name}: {e}")

def download_wangfonts():
    zip_url = "https://storage.googleapis.com/google-code-archive-downloads/v2/code.google.com/wangfonts/wangfonts-1.3.0.zip"
    zip_cache = FONTS_DIR / "wangfonts-1.3.0.zip"
    target_members = {
        "wangfonts/wt021.ttf": ("HanWangLiSuMedium.ttf", "WangHanZong Medium LiSu (隶书)"),
        "wangfonts/wt014.ttf": ("HanWangLiSuBold.ttf", "WangHanZong Bold LiSu (粗隶书)"),
        "wangfonts/wt040.ttf": ("HanWangYanKai.ttf", "WangHanZong Yan Kai (颜体楷书)"),
        "wangfonts/wt006.ttf": ("HanWangMediumKai.ttf", "WangHanZong Medium Kai (中楷体)"),
        "wangfonts/wt009.ttf": ("HanWangXingShu.ttf", "WangHanZong Xing Shu (行书)"),
        "wangfonts/wt024.ttf": ("HanWangWeiBei.ttf", "WangHanZong Wei Bei (魏碑体)"),
        "wangfonts/wt034.ttf": ("HanWangPenXingKai.ttf", "WangHanZong Hard Pen Xing Kai (钢笔行楷)"),
        "wangfonts/wtcc15.ttf": ("HanWangPenKai.ttf", "WangHanZong Hard Pen Kai (钢笔楷书)"),
    }

    # Check sibling lab directory if wt021.ttf is already there
    lab_wt021 = Path("/home/kevin/Workspace/calligraphy-lab/experiments/lishu-font/font/wt021.ttf")
    lab_license = Path("/home/kevin/Workspace/calligraphy-lab/experiments/lishu-font/font/license.txt")
    if lab_wt021.exists() and not (FONTS_DIR / "HanWangLiSuMedium.ttf").exists():
        shutil.copyfile(lab_wt021, FONTS_DIR / "HanWangLiSuMedium.ttf")
        print("[COPIED] HanWangLiSuMedium.ttf from lab archive.")
    if lab_license.exists() and not (LICENSES_DIR / "WangFonts-GPL.txt").exists():
        shutil.copyfile(lab_license, LICENSES_DIR / "WangFonts-GPL.txt")

    # If any other Wang fonts are needed, download archive and extract
    still_needed = [t[0] for t in target_members.values() if not (FONTS_DIR / t[0]).exists()]
    if still_needed:
        download_file(zip_url, zip_cache)
        print("[EXTRACTING] WangFonts archive...")
        with zipfile.ZipFile(zip_cache) as zf:
            for member, (local_name, desc) in target_members.items():
                dest = FONTS_DIR / local_name
                if not dest.exists():
                    print(f"Extracting {member} -> {local_name} ({desc})...")
                    dest.write_bytes(zf.read(member))
            if not (LICENSES_DIR / "WangFonts-GPL.txt").exists():
                (LICENSES_DIR / "WangFonts-GPL.txt").write_bytes(zf.read("wangfonts/license.txt"))
        if zip_cache.exists():
            zip_cache.unlink() # remove large archive

def download_coqubeli():
    """Download Cao Quan Bei (曹全碑隶体) release."""
    url = "https://github.com/MY1L/CoQuBeLi/releases/download/v.01/CoQuBeLi.0112.7z"
    dest_7z = FONTS_DIR / "CoQuBeLi.0112.7z"
    target_ttf = FONTS_DIR / "CoQuBeLi.ttf"
    if target_ttf.exists() and target_ttf.stat().st_size > 0:
        print(f"[SKIP] {target_ttf.name} already exists.")
        return
    try:
        download_file(url, dest_7z)
        with py7zr.SevenZipFile(dest_7z, mode='r') as z:
            names = z.getnames()
            print(f"[CoQuBeLi] files inside 7z: {names}")
            z.extractall(path=FONTS_DIR / "coqubeli_extracted")
        extracted_dir = FONTS_DIR / "coqubeli_extracted"
        for root, dirs, files in os.walk(extracted_dir):
            for file in files:
                if file.endswith((".ttf", ".otf")):
                    shutil.move(os.path.join(root, file), target_ttf)
                    print(f"[EXTRACTED] CoQuBeLi.ttf from {file}")
                elif "license" in file.lower() or "readme" in file.lower():
                    shutil.copyfile(os.path.join(root, file), LICENSES_DIR / f"CoQuBeLi-{file}")
        shutil.rmtree(extracted_dir, ignore_errors=True)
        if dest_7z.exists():
            dest_7z.unlink()
    except Exception as e:
        print(f"[ERROR] Failed CoQuBeLi download: {e}")

def setup_arphic_ukai():
    """Copy Arphic UKai from system fonts if available."""
    sys_ukai = Path("/usr/share/fonts/truetype/arphic/ukai.ttc")
    dest = FONTS_DIR / "ArphicUKai.ttc"
    if sys_ukai.exists() and not dest.exists():
        print(f"[COPY] Arphic UKai from {sys_ukai} -> {dest.name}")
        shutil.copyfile(sys_ukai, dest)
        (LICENSES_DIR / "Arphic-License.txt").write_text("Arphic Public License (Free Open Source Chinese Font)\n")

def download_lxgw_wenkai():
    """Download LXGW WenKai Lite TTF for web preview."""
    target = FONTS_DIR / "LXGWWenKai-Regular.ttf"
    if target.exists():
        print(f"[SKIP] {target.name} already exists.")
        return
    url = "https://github.com/lxgw/LxgwWenKai-Lite/releases/download/v1.515/LXGWWenKaiLite-Regular.ttf"
    try:
        download_file(url, target)
        license_url = "https://raw.githubusercontent.com/lxgw/LxgwWenKai/main/LICENSE"
        download_file(license_url, LICENSES_DIR / "LXGWWenKai-OFL.txt")
    except Exception as e:
        print(f"[ERROR] Failed LXGW WenKai download: {e}")

if __name__ == "__main__":
    print("=== Starting Font Downloads ===")
    setup_arphic_ukai()
    download_google_fonts()
    download_wangfonts()
    download_coqubeli()
    download_lxgw_wenkai()
    print("=== All Font Downloads Completed ===")
    print("Downloaded fonts in", FONTS_DIR)
    for f in sorted(FONTS_DIR.glob("*.*")):
        print(f"  {f.name:30} {f.stat().st_size / 1024 / 1024:6.2f} MB")
