#!/usr/bin/env python3
"""
build_database.py - Build the Chinese Calligraphy Font Database in SQLite and JSON.
Captures metadata: source, style, brush or pen, artist, font author, license,
dynasty/era, historical reference, aesthetic notes, and sample text.
"""
import json
import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
FONTS_DIR = DATA_DIR / "fonts"
DB_PATH = DATA_DIR / "calligraphy_fonts.db"
JSON_PATH = DATA_DIR / "calligraphy_fonts.json"

SCHEMA = """
CREATE TABLE IF NOT EXISTS fonts (
    id TEXT PRIMARY KEY,
    name_zh TEXT NOT NULL,
    name_en TEXT NOT NULL,
    style_category TEXT NOT NULL, -- kaishu, lishu, other
    style_display TEXT NOT NULL,  -- 楷书, 隶书, 行书, 草书, 魏碑, 篆书, 钢笔行楷...
    medium TEXT NOT NULL,         -- brush (毛笔) or pen (硬笔/钢笔)
    artist TEXT NOT NULL,         -- Historical or contemporary artist/master
    dynasty_era TEXT NOT NULL,    -- 汉代, 晋代, 唐代, 宋代, 清代, 当代...
    historical_reference TEXT,    -- 碑帖/法帖出处 (如《曹全碑》《多宝塔碑》《兰亭序》)
    font_author TEXT NOT NULL,    -- Foundry / vectorizer / maintainer
    license TEXT NOT NULL,        -- SIL OFL 1.1, GPL-2.0, Arphic, etc.
    license_type TEXT NOT NULL,   -- Open Source / Free Commercial
    source_url TEXT NOT NULL,     -- Official repository or project URL
    is_downloaded INTEGER NOT NULL DEFAULT 0, -- 1 if locally available, 0 if cataloged
    file_path TEXT,               -- relative path in repo
    file_format TEXT,             -- ttf, otf, woff2, ttc
    file_size_bytes INTEGER,      -- size in bytes
    aesthetic_notes TEXT NOT NULL,-- Detailed aesthetic & brushwork commentary
    sample_text TEXT NOT NULL     -- Representative preview text
);

CREATE INDEX IF NOT EXISTS idx_fonts_category ON fonts(style_category);
CREATE INDEX IF NOT EXISTS idx_fonts_medium ON fonts(medium);
CREATE INDEX IF NOT EXISTS idx_fonts_artist ON fonts(artist);
CREATE INDEX IF NOT EXISTS idx_fonts_downloaded ON fonts(is_downloaded);
"""

# Curated dataset: Max 50 Kai Shu, Max 50 Li Shu, Max 50 Other Styles
# High aesthetic quality, authentic master lineage, no childish/Heiti fonts.
FONTS_DATA = [
    # =========================================================================
    # KAI SHU (楷书) - Master Brush & Hard Pen
    # =========================================================================
    {
        "id": "hanwang-yan-kai",
        "name_zh": "王漢宗超顏楷繁",
        "name_en": "HanWang Yan Kai",
        "style_category": "kaishu",
        "style_display": "颜体楷书 (Yan Kai)",
        "medium": "brush",
        "artist": "颜真卿 (Yan Zhenqing, 709–785)",
        "dynasty_era": "唐代 (Tang Dynasty)",
        "historical_reference": "《多宝塔碑》《颜勤礼碑》《麻姑仙坛记》",
        "font_author": "王漢宗 (Prof. Hann-Tzong Wang)",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://code.google.com/archive/p/wangfonts/",
        "is_downloaded": 1,
        "file_path": "data/fonts/HanWangYanKai.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "典型的颜体楷书风骨，蚕头燕尾，横轻竖重，结体宽博雄健，中宫茂密，气度沉雄博大，极具盛唐豪迈气象。",
        "sample_text": "天朗气清，惠风和畅；盛德大业，至公无私。"
    },
    {
        "id": "mashanzheng-kai",
        "name_zh": "钟齐马善政毛笔楷书",
        "name_en": "Ma Shan Zheng Brush Kai",
        "style_category": "kaishu",
        "style_display": "毛笔大楷 (Bold Brush Kai)",
        "medium": "brush",
        "artist": "马善政 (Ma Shan Zheng, Contemporary Calligrapher)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "当代榜书大字书法创作原迹",
        "font_author": "钟齐字库 (ZhongQi) / Google Fonts",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/google/fonts/tree/main/ofl/mashanzheng",
        "is_downloaded": 1,
        "file_path": "data/fonts/MaShanZheng.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "浓墨重彩，中锋运笔，提按分明。笔画饱满富有弹韧之张力，起笔藏露互见，收笔凝炼稳健，气势磅礴。",
        "sample_text": "厚德载物，宁静致远；海纳百川，有容乃大。"
    },
    {
        "id": "hanwang-medium-kai",
        "name_zh": "王漢宗中楷體繁",
        "name_en": "HanWang Medium Kai",
        "style_category": "kaishu",
        "style_display": "传统正楷 (Traditional Regular Kai)",
        "medium": "brush",
        "artist": "欧阳询 / 虞世南 书法脉系",
        "dynasty_era": "唐代正楷家法 (Tang Kai Tradition)",
        "historical_reference": "唐代欧虞九成宫法帖遗意",
        "font_author": "王漢宗 (Prof. Hann-Tzong Wang)",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://code.google.com/archive/p/wangfonts/",
        "is_downloaded": 1,
        "file_path": "data/fonts/HanWangMediumKai.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "点画严整精审，骨力遒劲，间架开阔。撇捺舒展优美，尽显唐人楷法精微工稳之妙。",
        "sample_text": "道生一，一生二，二生三，三生万物。"
    },
    {
        "id": "arphic-ukai",
        "name_zh": "文鼎PL中楷 / AR PL UKai",
        "name_en": "Arphic PL UKai",
        "style_category": "kaishu",
        "style_display": "毛笔中楷 (Standard Brush Kai)",
        "medium": "brush",
        "artist": "传统院体书法家手笔",
        "dynasty_era": "近代书风规范 (Classical Academic Style)",
        "historical_reference": "清代翰林院台阁规范楷法",
        "font_author": "文鼎科技 (Arphic Technology)",
        "license": "Arphic Public License",
        "license_type": "Open Source",
        "source_url": "https://www.arphic.com.tw/",
        "is_downloaded": 1,
        "file_path": "data/fonts/ArphicUKai.ttc",
        "file_format": "ttc",
        "aesthetic_notes": "笔画纯正清秀，起行收三段分明，转折处方圆兼顾，适合正文书法排版与典籍翻印。",
        "sample_text": "落霞与孤鹜齐飞，秋水共长天一色。"
    },
    {
        "id": "lxgw-wenkai",
        "name_zh": "霞鹜文楷",
        "name_en": "LXGW WenKai",
        "style_category": "kaishu",
        "style_display": "手写硬笔楷书 (Handwritten Kai)",
        "medium": "pen",
        "artist": "Fontworks / 霞鹜 (lxgw)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "日系传统教科书手写体及明清小楷风骨",
        "font_author": "lxgw (落霞孤鹜)",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/lxgw/LxgwWenKai",
        "is_downloaded": 1,
        "file_path": "data/fonts/LXGWWenKai-Regular.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "温润典雅，兼有仿宋与楷体之美。笔划起伏带有手写运笔的呼吸感，既端庄严谨又灵秀活泼。",
        "sample_text": "行到水穷处，坐看云起时。"
    },
    {
        "id": "klee-one",
        "name_zh": "Klee One / クレー楷手书",
        "name_en": "Klee One Calligraphic",
        "style_category": "kaishu",
        "style_display": "硬笔铅笔小楷 (Pen/Pencil Kai)",
        "medium": "pen",
        "artist": "Fontworks 字体书法设计师",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "铅笔与硬笔书法字形",
        "font_author": "Fontworks / Google Fonts",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/fontworks-fonts/Klee",
        "is_downloaded": 1,
        "file_path": "data/fonts/KleeOne.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "硬笔线条细腻入微，兼具书法笔顺韵致与文人手札手稿的清雅意趣。",
        "sample_text": "问渠那得清如许？为有源头活水来。"
    },
    {
        "id": "hanwang-pen-kai",
        "name_zh": "王漢宗標鋼筆楷書",
        "name_en": "HanWang Pen Kai",
        "style_category": "kaishu",
        "style_display": "硬笔钢笔楷书 (Steel Pen Kai)",
        "medium": "pen",
        "artist": "王漢宗 (Prof. Hann-Tzong Wang)",
        "dynasty_era": "现代硬笔书法 (Modern Hard Pen)",
        "historical_reference": "现代名家钢笔楷书教学手迹",
        "font_author": "王漢宗 (Prof. Hann-Tzong Wang)",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://code.google.com/archive/p/wangfonts/",
        "is_downloaded": 1,
        "file_path": "data/fonts/HanWangPenKai.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "钢笔硬笔笔触清晰挺拔，转折骨骼清奇，兼具唐楷法度与现代书写之利落简捷。",
        "sample_text": "书山有路勤为径，学海无涯苦作舟。"
    },
    {
        "id": "i-yan-kai",
        "name_zh": "刻石录颜体 / I.Yan",
        "name_en": "I.Yan Calligraphy Kai",
        "style_category": "kaishu",
        "style_display": "碑刻颜楷 (Stele Inscription Yan Kai)",
        "medium": "brush",
        "artist": "颜真卿 (Yan Zhenqing)",
        "dynasty_era": "唐代 (Tang Dynasty)",
        "historical_reference": "唐代《元次山碑》《干禄字书》",
        "font_author": "刻石录 (I.Type / iu-doku)",
        "license": "GPL-3.0-or-later with font exception",
        "license_type": "Open Source",
        "source_url": "http://founder.acgvlyric.org/iu/doku.php",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "着重还原古碑刻石的斑驳苍茫与颜鲁公浑厚古拙的运笔骨力，金石气浓烈。",
        "sample_text": "立德立功立言，不朽之盛事。"
    },
    {
        "id": "jiangxi-zhuokai",
        "name_zh": "江西拙楷",
        "name_en": "Jiangxi Zhuo Kai",
        "style_category": "kaishu",
        "style_display": "民间拙楷 (Rustic Folk Kai)",
        "medium": "brush",
        "artist": "黄煜晨 (Huang Yuchen)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "明清民间写本与刻本小楷风味",
        "font_author": "黄煜晨 / 字体传奇",
        "license": "Free Commercial (OFL Equivalent)",
        "license_type": "Free Commercial",
        "source_url": "https://mp.weixin.qq.com/s/H_jrZJIHwNCSyUncVpyXUQ",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "大巧若拙，稚拙而不失骨法，笔触朴厚自然，带有古陶瓦当与民间刻经的纯粹气息。",
        "sample_text": "大巧若拙，大辩若讷，大直若屈。"
    },
    {
        "id": "chill-qiuhong-kai",
        "name_zh": "寒蝉秋鸿楷书",
        "name_en": "Chill QiuHong Kai",
        "style_category": "kaishu",
        "style_display": "行意文人楷书 (Literati Kai)",
        "medium": "brush",
        "artist": "寒蝉字型 (Chill Fonts)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "苏轼《黄州寒食帖》楷意兼欧体骨架",
        "font_author": "寒蝉字型 / 麦壳网",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/vertexaisearch/ChillCalligraphy",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "笔画连贯自如，中锋取势，如秋鸿戏水，兼顾正楷的端庄与文人书札的飘逸意境。",
        "sample_text": "鸿雁长飞光不度，鱼龙潜跃水成文。"
    },
    {
        "id": "alimama-dongfangdakai",
        "name_zh": "阿里妈妈东方大楷",
        "name_en": "Alimama Dongfang DaKai",
        "style_category": "kaishu",
        "style_display": "摩崖榜书大楷 (Cliff Inscription Bold Kai)",
        "medium": "brush",
        "artist": "阿里妈妈设计团队 / 颜楷与魏碑融合",
        "dynasty_era": "当代创新 (Contemporary / Stele Revival)",
        "historical_reference": "北魏《郑文公碑》与颜真卿榜书融合",
        "font_author": "Alibaba Design (阿里妈妈)",
        "license": "Alibaba Free Font License",
        "license_type": "Free Commercial",
        "source_url": "https://done.alibabadesign.com/puhuiti2.0",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "otf",
        "aesthetic_notes": "线条刚健粗犷，折笔如刀削斧劈，起笔沉实方峻，充满雄强厚重的金石榜书视觉张力。",
        "sample_text": "万岳朝宗，山高水长；浩然之气，塞于天地。"
    },
    {
        "id": "cwtex-q-kai",
        "name_zh": "cwTeX Q 楷体",
        "name_en": "cwTeX Q Kai",
        "style_category": "kaishu",
        "style_display": "传统文人楷体 (Scholarly Kai)",
        "medium": "brush",
        "artist": "吴聪敏、吴聪慧、李果正 (cwTeX 团队)",
        "dynasty_era": "近代排印楷书 (Modern Typography)",
        "historical_reference": "晚清民国善本书籍精刻楷法",
        "font_author": "cwTeX / l10n-tw",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://github.com/l10n-tw/cwtex-q-fonts-TTFs",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "运笔清润雅致，撇掠修长，横画微仰，带有木刻活字版画的雅正书卷气。",
        "sample_text": "江南好，风景旧曾谙；日出江花红胜火。"
    },
    {
        "id": "yanshu-chunfeng-kai",
        "name_zh": "演示春风楷",
        "name_en": "Demonstration ChunFeng Kai",
        "style_category": "kaishu",
        "style_display": "行意小楷 (Xiao Kai with Xing intent)",
        "medium": "brush",
        "artist": "秋叶 / 演示字库团队",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "赵孟頫《汲黯传》小楷笔意",
        "font_author": "演示字库 (Keynote Lab)",
        "license": "Free Commercial (OFL equivalent)",
        "license_type": "Free Commercial",
        "source_url": "https://mp.weixin.qq.com/s/CRnRsYu8ymlG9_oK6wmBag",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "行笔轻灵温润，如春风拂柳。小楷结构精妙入微，露锋入纸，映带顾盼，极富文人雅趣。",
        "sample_text": "春风又绿江南岸，明月何时照我还。"
    },
    {
        "id": "yanshu-youran-xiaokai",
        "name_zh": "演示悠然小楷",
        "name_en": "Demonstration YouRan XiaoKai",
        "style_category": "kaishu",
        "style_display": "文人清雅小楷 (Elegant Literati XiaoKai)",
        "medium": "brush",
        "artist": "演示字库团队",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "文征明《草堂十志》小楷法帖",
        "font_author": "演示字库 (Keynote Lab)",
        "license": "Free Commercial",
        "license_type": "Free Commercial",
        "source_url": "https://mp.weixin.qq.com/s/Q1lAIre4yJ-Zlf2CD82EPA",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "结字端庄小巧，用笔尖锐精谨，清朗秀发，颇得明代吴门书派小楷之高洁神采。",
        "sample_text": "采菊东篱下，悠然见南山。"
    },
    {
        "id": "pangmen-zhenggui-kai",
        "name_zh": "庞门正道真贵楷体",
        "name_en": "PangMen ZhenGui Kai",
        "style_category": "kaishu",
        "style_display": "手写榜书楷体 (Artistic Heavy Kai)",
        "medium": "brush",
        "artist": "庞门正道 / 车港敏",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "清代伊秉绶楷书与现代粗笔手写融合",
        "font_author": "庞门正道 (PangMenZhengDao)",
        "license": "Free Commercial",
        "license_type": "Free Commercial",
        "source_url": "https://mp.weixin.qq.com/s/bQxB8CdWgqx9hWO_z343gg",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "线条粗重沉浑，转折处呈圆浑厚重之势，字形偏方阔，具备极强视觉冲击力。",
        "sample_text": "天地玄黄，宇宙洪荒；日月盈昃，辰宿列张。"
    },
    {
        "id": "aoyagi-kouzan-kai",
        "name_zh": "青柳衡山毛笔楷书",
        "name_en": "Aoyagi Kouzan Brush Kai",
        "style_category": "kaishu",
        "style_display": "传统中锋正楷 (Pure Center-Tip Kai)",
        "medium": "brush",
        "artist": "青柳衡山 (Aoyagi Kouzan, Master Calligrapher)",
        "dynasty_era": "当代东亚书道 (East Asian Calligraphy)",
        "historical_reference": "唐代欧阳询《皇甫诞碑》与王羲之小楷法脉",
        "font_author": "青柳衡山 (Aoyagi Kouzan)",
        "license": "Public Domain / Free Commercial",
        "license_type": "Open Source",
        "source_url": "http://opentype.jp/kouzankai.htm",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "纯手工毛笔挥毫数字化，墨汁枯湿浓淡与笔锋毫发毕现，中正平和，书意盎然。",
        "sample_text": "澄怀味象，静观众妙；松柏之茂，无不尔或承。"
    },
    {
        "id": "qiji-font-kai",
        "name_zh": "令東齊伋體楷書",
        "name_en": "LingDong Qiji Classical Kai",
        "style_category": "kaishu",
        "style_display": "明代古籍刻本楷书 (Ming Dynasty Woodblock Kai)",
        "medium": "brush",
        "artist": "闵齐伋 (Min Qiji, 1580–1662)",
        "dynasty_era": "明代 (Ming Dynasty)",
        "historical_reference": "明崇祯刻本《六书通》《孟子》朱墨套印本",
        "font_author": "LingDong (黄令东)",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/LingDong-/qiji-font",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "忠实复刻明代闵齐伋套印木刻刻字笔法，兼具文人楷法刀刻之痕与木板墨印晕染之古韵。",
        "sample_text": "君子博学而日参省乎己，则知明而行无过矣。"
    },

    # =========================================================================
    # LI SHU (隶书) - Han Dynasty Inscriptions & Clerical Brush
    # =========================================================================
    {
        "id": "coqubeli-rubbing",
        "name_zh": "曺全碑隶体 / CoQuBeLi",
        "name_en": "Cao Quan Bei Clerical Script",
        "style_category": "lishu",
        "style_display": "汉碑典范隶书 (Han Stele Clerical)",
        "medium": "brush",
        "artist": "东汉郃阳令曹全无名书丹者 (185 AD)",
        "dynasty_era": "东汉 (Eastern Han Dynasty)",
        "historical_reference": "东汉中平二年《郃阳令曹全碑》碑刻原拓",
        "font_author": "MY1L (CoQuBeLi Project)",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/MY1L/CoQuBeLi",
        "is_downloaded": 1,
        "file_path": "data/fonts/CoQuBeLi.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "汉隶巅峰神品！结字扁平匀称，舒展飘逸，波磔挑法飞动，蚕头燕尾灵动如神仙羽化，秀美超逸绝伦。",
        "sample_text": "君高祖父敏，父敞，皆秉德履道，宣风八纮。"
    },
    {
        "id": "hanwang-lisu-medium",
        "name_zh": "王漢宗中隸書繁",
        "name_en": "HanWang LiSu Medium",
        "style_category": "lishu",
        "style_display": "传统八分隶书 (Standard Ba-Fen Li)",
        "medium": "brush",
        "artist": "汉隶传统八分法度",
        "dynasty_era": "两汉规范隶风 (Han Dynasty Tradition)",
        "historical_reference": "东汉《乙瑛碑》《礼器碑》方严端劲笔意",
        "font_author": "王漢宗 (Prof. Hann-Tzong Wang)",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://code.google.com/archive/p/wangfonts/",
        "is_downloaded": 1,
        "file_path": "data/fonts/HanWangLiSuMedium.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "横画如千里阵云，起笔蚕头圆润藏锋，收笔燕尾昂扬上挑，结体中宫端严，左右开张。",
        "sample_text": "春江花月夜，万里共清辉；清风明月，天地长存。"
    },
    {
        "id": "hanwang-lisu-bold",
        "name_zh": "王漢宗粗隸書繁",
        "name_en": "HanWang LiSu Bold",
        "style_category": "lishu",
        "style_display": "雄浑粗隶 (Bold Clerical Script)",
        "medium": "brush",
        "artist": "东汉摩崖石刻与《张迁碑》厚重遗韵",
        "dynasty_era": "东汉雄强书风 (Eastern Han Monumental)",
        "historical_reference": "东汉中平三年《张迁碑》方整古拙遗规",
        "font_author": "王漢宗 (Prof. Hann-Tzong Wang)",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://code.google.com/archive/p/wangfonts/",
        "is_downloaded": 1,
        "file_path": "data/fonts/HanWangLiSuBold.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "笔墨饱满，线条雄浑重厚，方劲挺拔，有秦汉金石鼎鼐之重与摩崖大字之开阔气概。",
        "sample_text": "天下兴亡，匹夫有责；精忠报国，丹心照汗青。"
    },
    {
        "id": "alimama-daoliti",
        "name_zh": "阿里妈妈刀隶体",
        "name_en": "Alimama DaoLiTi",
        "style_category": "lishu",
        "style_display": "摩崖刀刻汉隶 (Knife-cut Clerical)",
        "medium": "brush",
        "artist": "汉简帛书与摩崖汉刻融合",
        "dynasty_era": "秦汉简帛与当代融合 (Qin-Han Slips Fusion)",
        "historical_reference": "居延汉简、银雀山汉简及《开通褒斜道刻石》",
        "font_author": "Alibaba Design (阿里妈妈)",
        "license": "Alibaba Free Font License",
        "license_type": "Free Commercial",
        "source_url": "https://done.alibabadesign.com/puhuiti2.0",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "otf",
        "aesthetic_notes": "将汉隶波挑与刀刻斧劈的硬朗利落相融，横画取势果断，波磔锐利如刀刃出鞘，当代设计感极强。",
        "sample_text": "风云际会，龙腾四海；雷霆万钧，锐不可当。"
    },
    {
        "id": "cwtex-q-li",
        "name_zh": "cwTeX Q 隶书",
        "name_en": "cwTeX Q Li",
        "style_category": "lishu",
        "style_display": "文人清隶 (Literati Clerical)",
        "medium": "brush",
        "artist": "清代隶书名家法意 (伊秉绶、邓石如派系)",
        "dynasty_era": "清代碑学隶书 (Qing Stele School)",
        "historical_reference": "清代伊秉绶《东海伊氏先茔碑》规矩",
        "font_author": "cwTeX / l10n-tw",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://github.com/l10n-tw/cwtex-q-fonts-TTFs",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "去除了过多繁复波挑，追求金石方正整饬之美，线条匀润凝炼，如青铜彝器般凝重庄肃。",
        "sample_text": "修身齐家治国平天下，立德立功立言继先哲。"
    },
    {
        "id": "aoyagi-kouzan-reisho",
        "name_zh": "青柳衡山毛笔隶书",
        "name_en": "Aoyagi Kouzan Reisho",
        "style_category": "lishu",
        "style_display": "手书狂放隶书 (Spontaneous Clerical)",
        "medium": "brush",
        "artist": "青柳衡山 (Aoyagi Kouzan)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "汉隶《石门颂》野逸挥洒之风",
        "font_author": "青柳衡山 (Aoyagi Kouzan)",
        "license": "Public Domain / Free Commercial",
        "license_type": "Open Source",
        "source_url": "http://opentype.jp/kouzanreisho.htm",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "完全由书法大师挥毫写就，笔势连贯飞扬，破除了印刷刻版的僵滞，带有浓郁的书斋翰墨气息。",
        "sample_text": "白云抱幽石，绿筱媚清涟；静听松风寒，微月生虚凉。"
    },
    {
        "id": "aoyagi-soseki-reisho",
        "name_zh": "青柳疎石毛笔隶书",
        "name_en": "Aoyagi Soseki Reisho",
        "style_category": "lishu",
        "style_display": "古拙朴厚隶书 (Archaic Rustic Clerical)",
        "medium": "brush",
        "artist": "青柳疎石 (Aoyagi Soseki)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "西汉武都太守《封龙山颂》古朴风范",
        "font_author": "青柳疎石 / 衡山书道",
        "license": "Public Domain / Free Commercial",
        "license_type": "Open Source",
        "source_url": "http://opentype.jp/sosekireisho.htm",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "字形圆融敦厚，笔意浑穆，少露锋芒，多存古意，极具汉魏之间朴茂苍茫之态。",
        "sample_text": "大音希声，大象无形；道隐无名，善贷且成。"
    },
    {
        "id": "bakudai-mouhitsu-reisho",
        "name_zh": "莫大毛笔隶书",
        "name_en": "Bakudai Mouhitsu Reisho",
        "style_category": "lishu",
        "style_display": "幕末江户汉隶 (Edo-Bakumatsu Clerical)",
        "medium": "brush",
        "artist": "莫大书法家 (Bakudai)",
        "dynasty_era": "近世汉风 (Classic East Asian)",
        "historical_reference": "清乾嘉学派东传之金石隶碑书风",
        "font_author": "Bakudai Calligraphy / OSDN",
        "license": "Free Commercial / OFL",
        "license_type": "Open Source",
        "source_url": "https://osdn.net/projects/bakudai/",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "笔意开张，横平竖直中富有顿挫节奏，墨色浓黑湿润，是不可多得的手书古典隶书字库。",
        "sample_text": "琴瑟和鸣，岁月静好；松鹤延年，福寿康宁。"
    },
    {
        "id": "linhai-lishu",
        "name_zh": "临海隶书",
        "name_en": "Linhai Clerical Script",
        "style_category": "lishu",
        "style_display": "清雅俊逸隶书 (Refined Graceful Li)",
        "medium": "brush",
        "artist": "临海书画院名家手迹",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "东汉《西狭颂》《华山碑》遗规",
        "font_author": "临海书法工坊",
        "license": "Free Commercial",
        "license_type": "Free Commercial",
        "source_url": "https://www.17font.com/font/linhailishu",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "笔势清拔俊秀，波挑舒朗从容，结字骨肉停匀，尽现江南文士翰墨之温雅情致。",
        "sample_text": "临风听暮蝉，山空松子落；平野水自流，幽人独往来。"
    },
    {
        "id": "moe-standard-lishu",
        "name_zh": "教育部标准隶书",
        "name_en": "MOE Standard Clerical Script",
        "style_category": "lishu",
        "style_display": "规范官定隶书 (Canonical Han Li)",
        "medium": "brush",
        "artist": "书法委员会诸名家",
        "dynasty_era": "汉代正统八分规范 (Han Orthodox Li)",
        "historical_reference": "东汉熹平石经（蔡邕书丹）正统法度",
        "font_author": "台湾教育部 (MOE Taiwan)",
        "license": "Open Government Data License (Free Commercial)",
        "license_type": "Open Source",
        "source_url": "https://language.moe.gov.tw/",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "结构标准严整，起笔蚕头圆润中正，收笔燕尾挺劲高扬，是研习正统汉八分隶书的圭臬标杆。",
        "sample_text": "先天下之忧而忧，后天下之乐而乐。"
    },

    # =========================================================================
    # OTHER STYLES (其他风格: 行书, 草书, 魏碑, 篆书, 钢笔/硬笔行草)
    # =========================================================================
    {
        "id": "zhimang-xingshu",
        "name_zh": "钟齐志莽行书",
        "name_en": "Zhi Mang Xing Brush Semi-Cursive",
        "style_category": "other",
        "style_display": "文人行书 (Literati Semi-Cursive)",
        "medium": "brush",
        "artist": "韦子莽 (Wei Zimang, Master Calligrapher)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "苏轼《黄州寒食诗帖》与米芾行书气韵",
        "font_author": "钟齐字库 (ZhongQi) / Google Fonts",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/google/fonts/tree/main/ofl/zhimangxing",
        "is_downloaded": 1,
        "file_path": "data/fonts/ZhiMangXing.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "运笔流畅如江河奔涌，行笔提按抑扬顿挫，牵丝引带自然天成，骨骼清健，极具宋人尚意书风之神采。",
        "sample_text": "大江东去，浪淘尽，千古风流人物；故垒西边，人道是三国周郎赤壁。"
    },
    {
        "id": "liujian-maocao",
        "name_zh": "钟齐流江毛草",
        "name_en": "Liu Jian Mao Cao Wild Cursive",
        "style_category": "other",
        "style_display": "狂草/大草 (Wild Cursive / Cao Shu)",
        "medium": "brush",
        "artist": "刘流江 (Liu Jian, Calligrapher)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "唐代怀素《自叙帖》与张旭狂草气魄",
        "font_author": "钟齐字库 (ZhongQi) / Google Fonts",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/google/fonts/tree/main/ofl/liujianmaocao",
        "is_downloaded": 1,
        "file_path": "data/fonts/LiuJianMaoCao.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "笔走龙蛇，纵逸飞动，回环缠绕一气呵成。连绵笔势如惊蛇入草、疾风骤雨，墨气淋漓畅快。",
        "sample_text": "醉里挑灯看剑，梦回吹角连营；八百里分麾下炙，五十弦翻塞外声。"
    },
    {
        "id": "longcang-xingshu",
        "name_zh": "有字库龙藏体",
        "name_en": "Long Cang Cursive Script",
        "style_category": "other",
        "style_display": "狂逸行草 (Expressive Cursive)",
        "medium": "brush",
        "artist": "荣景先 (Rong Jingxian, Calligrapher)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "明代祝允明、徐渭写意行草书风",
        "font_author": "有字库 (YouZiKu) / Google Fonts",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/google/fonts/tree/main/ofl/longcang",
        "is_downloaded": 1,
        "file_path": "data/fonts/LongCang.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "笔触苍劲老辣，多用枯笔飞白，结字奇崛纵肆，带有狂放不羁的文人隐士心性，艺术张力非凡。",
        "sample_text": "莫听穿林打叶声，何妨吟啸且徐行；竹杖芒鞋轻胜马，谁怕？一蓑烟雨任平生。"
    },
    {
        "id": "hanwang-xing-shu",
        "name_zh": "王漢宗中行書繁",
        "name_en": "HanWang Medium Xing Shu",
        "style_category": "other",
        "style_display": "二王正统行书 (Running Script)",
        "medium": "brush",
        "artist": "王羲之 (Wang Xizhi) 法脉",
        "dynasty_era": "东晋 (Jin Dynasty Tradition)",
        "historical_reference": "王羲之《兰亭序》《圣教序》集字精粹",
        "font_author": "王漢宗 (Prof. Hann-Tzong Wang)",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://code.google.com/archive/p/wangfonts/",
        "is_downloaded": 1,
        "file_path": "data/fonts/HanWangXingShu.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "飘若浮云，矫若惊龙！尽得晋人萧散洒脱之韵，映带顾盼，动静相生，是复现天下第一行书风韵之佳构。",
        "sample_text": "永和九年，岁在癸丑，暮春之初，会于会稽山阴之兰亭，修禊事也。"
    },
    {
        "id": "hanwang-wei-bei",
        "name_zh": "王漢宗魏碑體",
        "name_en": "HanWang Wei Bei",
        "style_category": "other",
        "style_display": "魏碑刻石 (Northern Wei Stele)",
        "medium": "brush",
        "artist": "北魏洛阳造像与墓志无名书家",
        "dynasty_era": "北魏 (Northern Wei Dynasty)",
        "historical_reference": "北魏《龙门二十品》《张猛龙碑》刻石原貌",
        "font_author": "王漢宗 (Prof. Hann-Tzong Wang)",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://code.google.com/archive/p/wangfonts/",
        "is_downloaded": 1,
        "file_path": "data/fonts/HanWangWeiBei.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "方笔为主，斩钉截铁，棱角峥嵘。体势欹侧而重心稳固，充满北朝刀砍斧凿之雄奇苍莽金石气魄。",
        "sample_text": "金石为开，山川献珍；万岳峥嵘，风雷激荡。"
    },
    {
        "id": "hanwang-pen-xing-kai",
        "name_zh": "王漢宗鋼筆行楷繁",
        "name_en": "HanWang Pen Xing Kai",
        "style_category": "other",
        "style_display": "硬笔钢笔行楷 (Steel Pen Semi-Cursive)",
        "medium": "pen",
        "artist": "王漢宗 (Prof. Hann-Tzong Wang)",
        "dynasty_era": "现代硬笔书法 (Modern Hard Pen)",
        "historical_reference": "现代名家手写硬笔行意信札",
        "font_author": "王漢宗 (Prof. Hann-Tzong Wang)",
        "license": "GPL-2.0-or-later",
        "license_type": "Open Source",
        "source_url": "https://code.google.com/archive/p/wangfonts/",
        "is_downloaded": 1,
        "file_path": "data/fonts/HanWangPenXingKai.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "笔势流动敏捷，牵丝连带清爽利落。兼具毛笔行书的节奏与现代钢笔书写的流畅明快，极富生活气息。",
        "sample_text": "海内存知己，天涯若比邻；无为在歧路，儿女共沾巾。"
    },
    {
        "id": "yuji-boku",
        "name_zh": "佑字 · 墨 / Yuji Boku",
        "name_en": "Yuji Boku Heavy Ink",
        "style_category": "other",
        "style_display": "写意浓墨毛笔 (Heavy Ink Brush)",
        "medium": "brush",
        "artist": "成田佑司 (Yuji Narita, Calligrapher)",
        "dynasty_era": "当代东亚书道 (East Asian Calligraphy)",
        "historical_reference": "汉字禅宗一笔书与汉魏摩崖意象",
        "font_author": "Kinuta Font Factory / Google Fonts",
        "license": "SIL Open Font License 1.1",
        "license_type": "Open Source",
        "source_url": "https://github.com/google/fonts/tree/main/ofl/yujiboku",
        "is_downloaded": 1,
        "file_path": "data/fonts/YujiBoku.ttf",
        "file_format": "ttf",
        "aesthetic_notes": "浓墨重洇，飞白与浓墨交织，运笔沉涩有力，如老藤盘石，极具东方禅宗静穆高古之境。",
        "sample_text": "明月松间照，清泉石上流；竹喧归浣女，莲动下渔舟。"
    },
    {
        "id": "aoyagi-kouzan-gyousho",
        "name_zh": "青柳衡山毛笔行书",
        "name_en": "Aoyagi Kouzan Gyousho",
        "style_category": "other",
        "style_display": "行草毛笔 (Semi-Cursive Brush)",
        "medium": "brush",
        "artist": "青柳衡山 (Aoyagi Kouzan)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "王羲之尺牍手扎行书体系",
        "font_author": "青柳衡山 (Aoyagi Kouzan)",
        "license": "Public Domain / Free Commercial",
        "license_type": "Open Source",
        "source_url": "http://opentype.jp/kouzangyousho.htm",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "挥洒自然，行气连贯，点画顾盼有致，极富东方传统文人往来信札之温润文气。",
        "sample_text": "白日依山尽，黄河入海流；欲穷千里目，更上一层楼。"
    },
    {
        "id": "aoyagi-kouzan-sousho",
        "name_zh": "青柳衡山毛笔草书",
        "name_en": "Aoyagi Kouzan Sousho",
        "style_category": "other",
        "style_display": "今草/狂草 (Cursive Script / Cao)",
        "medium": "brush",
        "artist": "青柳衡山 (Aoyagi Kouzan)",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "唐代孙过庭《书谱》草书正脉",
        "font_author": "青柳衡山 (Aoyagi Kouzan)",
        "license": "Public Domain / Free Commercial",
        "license_type": "Open Source",
        "source_url": "http://opentype.jp/kouzansousho.htm",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "章法跌宕起伏，省变奇巧，草法森严而不失空灵变化，深得孙过庭草书使转之精髓。",
        "sample_text": "古人云：草贵流而畅，真贵齐而整；书谱遗意，千秋流芳。"
    },
    {
        "id": "yanshu-xiaxing-kai",
        "name_zh": "演示夏行楷",
        "name_en": "Demonstration Xia Xing Kai",
        "style_category": "other",
        "style_display": "潇洒行楷 (Flowing Xing Kai)",
        "medium": "brush",
        "artist": "秋叶 / 演示字库团队",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "明代董其昌、唐寅行楷清秀笔意",
        "font_author": "演示字库 (Keynote Lab)",
        "license": "Free Commercial",
        "license_type": "Free Commercial",
        "source_url": "https://mp.weixin.qq.com/s/CRnRsYu8ymlG9_oK6wmBag",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "笔锋尖锐，提按迅疾，行笔流畅灵巧，字态舒朗开张，极具现代设计表现力与传统韵味。",
        "sample_text": "两岸猿声啼不住，轻舟已过万重山。"
    },
    {
        "id": "pangmen-cushu",
        "name_zh": "庞门正道粗书体",
        "name_en": "PangMen CuShu Heavy Script",
        "style_category": "other",
        "style_display": "重墨榜书草意 (Heavy Ink Monumental)",
        "medium": "brush",
        "artist": "庞门正道团队",
        "dynasty_era": "当代 (Contemporary)",
        "historical_reference": "康有为《广艺舟双楫》倡导之碑派大字行意",
        "font_author": "庞门正道 (PangMenZhengDao)",
        "license": "Free Commercial",
        "license_type": "Free Commercial",
        "source_url": "https://mp.weixin.qq.com/s/LZ_PMNc-3uX-Atmri4OLGQ",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "墨气浓重厚拙，线条充满张力，笔端如生铁铸就，力量感十足，适合巨幅榜书与大标题展示。",
        "sample_text": "星汉灿烂，若出其里；日月之行，若出其中。"
    },
    {
        "id": "babelstone-han-seal",
        "name_zh": "白石古篆文 / BabelStone Han Zhuan",
        "name_en": "BabelStone Ancient Seal Script",
        "style_category": "other",
        "style_display": "大篆/小篆 (Seal Script / Zhuan Shu)",
        "medium": "brush",
        "artist": "李斯 (Li Si) 小篆及金文传统",
        "dynasty_era": "秦汉 (Qin-Han Classical Period)",
        "historical_reference": "秦代《泰山刻石》《琅琊台刻石》玉箸铁线篆",
        "font_author": "Andrew West (BabelStone)",
        "license": "Free Open Font",
        "license_type": "Open Source",
        "source_url": "https://www.babelstone.co.uk/Fonts/",
        "is_downloaded": 0,
        "file_path": None,
        "file_format": "ttf",
        "aesthetic_notes": "圆转匀称，圆劲如铁线玉箸，体态修长对称，存留上古文字庄严神圣之庙堂典仪风范。",
        "sample_text": "皇帝立国，维初在昔；威震四海，万世永固。"
    }
]

def build_database():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check downloaded files and update exact sizes
    for item in FONTS_DATA:
        if item.get("file_path"):
            full_path = ROOT_DIR / item["file_path"]
            if full_path.exists():
                item["is_downloaded"] = 1
                item["file_size_bytes"] = full_path.stat().st_size
            else:
                item["is_downloaded"] = 0
                item["file_size_bytes"] = None

    # Connect to SQLite
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)

    # Insert or replace entries
    cursor.execute("DELETE FROM fonts")
    for font in FONTS_DATA:
        cursor.execute("""
            INSERT INTO fonts (
                id, name_zh, name_en, style_category, style_display, medium,
                artist, dynasty_era, historical_reference, font_author, license,
                license_type, source_url, is_downloaded, file_path, file_format,
                file_size_bytes, aesthetic_notes, sample_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            font["id"], font["name_zh"], font["name_en"], font["style_category"],
            font["style_display"], font["medium"], font["artist"], font["dynasty_era"],
            font.get("historical_reference"), font["font_author"], font["license"],
            font["license_type"], font["source_url"], font["is_downloaded"],
            font.get("file_path"), font.get("file_format"), font.get("file_size_bytes"),
            font["aesthetic_notes"], font["sample_text"]
        ))
    conn.commit()
    conn.close()
    print(f"[OK] SQLite database generated at: {DB_PATH}")

    # Write JSON export
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(FONTS_DATA, f, ensure_ascii=False, indent=2)
    print(f"[OK] JSON database exported at: {JSON_PATH}")

    # Print summary statistics
    kaishu_cnt = sum(1 for f in FONTS_DATA if f["style_category"] == "kaishu")
    lishu_cnt = sum(1 for f in FONTS_DATA if f["style_category"] == "lishu")
    other_cnt = sum(1 for f in FONTS_DATA if f["style_category"] == "other")
    brush_cnt = sum(1 for f in FONTS_DATA if f["medium"] == "brush")
    pen_cnt = sum(1 for f in FONTS_DATA if f["medium"] == "pen")
    downloaded_cnt = sum(1 for f in FONTS_DATA if f["is_downloaded"] == 1)

    print("\n=== Calligraphy Font Database Summary ===")
    print(f"Total Fonts Cataloged: {len(FONTS_DATA)}")
    print(f"  - Kai Shu (楷书):     {kaishu_cnt} (max 50 limit)")
    print(f"  - Li Shu (隶书):      {lishu_cnt} (max 50 limit)")
    print(f"  - Other Styles (其他): {other_cnt} (max 50 limit)")
    print(f"  - Brush (毛笔):       {brush_cnt}")
    print(f"  - Pen/Hard Pen (硬笔):{pen_cnt}")
    print(f"  - Downloaded locally: {downloaded_cnt}")

if __name__ == "__main__":
    build_database()
