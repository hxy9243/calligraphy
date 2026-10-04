/**
 * app.js - Calligraphy Studio & Font Database Interactive Application
 * Real-time font display on live calligraphy stage, full metadata browser,
 * instant Trad <-> Simp conversion via zhconv engine, and video/still generation.
 */

// Downloaded font mappings to @font-face families
const LOCAL_FONTS_MAP = {
  // Key Fonts & Kai Shu (楷书)
  "mashanzheng-kai": { family: "MaShanZheng", file: "fonts/MaShanZheng.ttf", charSupport: "simp" },
  "mashanzheng": { family: "MaShanZheng", file: "fonts/MaShanZheng.ttf", charSupport: "simp" },
  "i-yan-kai": { family: "IYanKai", file: "fonts/IYanKai.ttf", charSupport: "trad" },
  "tw-kai": { family: "TWKai", file: "fonts/TW-Kai.ttf", charSupport: "trad" },
  "edukai": { family: "EduKai", file: "fonts/EduKai.ttf", charSupport: "trad" },
  "lxgw-wenkai-tc": { family: "LXGWWenKaiTC", file: "fonts/LXGWWenKaiTC-Regular.ttf", charSupport: "trad" },
  "xiaolai-kai": { family: "Xiaolai", file: "fonts/Xiaolai.ttf", charSupport: "trad" },

  // Kai Shu (楷书)
  "hanwang-yan-kai": { family: "HanWangYanKai", file: "fonts/HanWangYanKai.ttf", charSupport: "trad" },
  "hanwang-medium-kai": { family: "HanWangMediumKai", file: "fonts/HanWangMediumKai.ttf", charSupport: "trad" },
  "arphic-ukai": { family: "ArphicUKai", file: "fonts/ArphicUKai.ttc", charSupport: "both" },
  "lxgw-wenkai": { family: "LXGWWenKai", file: "fonts/LXGWWenKai-Regular.ttf", charSupport: "both" },
  "chill-qiuhong-kai": { family: "QiuHongKai", file: "fonts/QiuHongKai.ttf", charSupport: "simp" },
  "cwtex-q-kai": { family: "cwTeXQKai", file: "fonts/cwTeXQKai.ttf", charSupport: "trad" },
  "yanshu-chunfeng-kai": { family: "ChunFengKai", file: "fonts/ChunFengKai.ttf", charSupport: "simp" },
  "yanshu-youran-xiaokai": { family: "YouRanXiaoKai", file: "fonts/YouRanXiaoKai.ttf", charSupport: "simp" },
  "maoken-yingbi-kai": { family: "MaokenYingBiKai", file: "fonts/MaokenYingBiKai.ttf", charSupport: "simp" },
  "icrane-pen-kai": { family: "ICranePenKai", file: "fonts/ICranePenKai.ttf", charSupport: "trad" },
  "lxgw-zhenkai": { family: "LXGWZhenKai", file: "fonts/LXGWZhenKai.ttf", charSupport: "simp" },
  "yozai-kai": { family: "YozaiKai", file: "fonts/YozaiKai.ttf", charSupport: "simp" },
  "chill-longcang-kai": { family: "ChillLongCangKai", file: "fonts/ChillLongCangKai.otf", charSupport: "simp" },
  "chill-longcang-kai-bold": { family: "ChillLongCangKaiBold", file: "fonts/ChillLongCangKaiBold.otf", charSupport: "simp" },
  "lxgw-wenkai-bold": { family: "LXGWWenKaiBold", file: "fonts/LXGWWenKaiBold.ttf", charSupport: "both" },
  "lxgw-wenkai-mono": { family: "LXGWWenKaiMono", file: "fonts/LXGWWenKaiMono.ttf", charSupport: "both" },
  "hanwang-standard-kai": { family: "HanWangStandardKai", file: "fonts/HanWangStandardKai.ttf", charSupport: "trad" },
  "hanwang-simplified-kai": { family: "HanWangSimplifiedKai", file: "fonts/HanWangSimplifiedKai.ttf", charSupport: "simp" },
  "hanwang-phonetic-kai": { family: "HanWangPhoneticKai", file: "fonts/HanWangPhoneticKai.ttf", charSupport: "trad" },
  "hanwang-hollow-kai": { family: "HanWangHollowKai", file: "fonts/HanWangHollowKai.ttf", charSupport: "trad" },

  // Li Shu (隶书)
  "hanwang-lisu-medium": { family: "HanWangLiSuMedium", file: "fonts/HanWangLiSuMedium.ttf", charSupport: "trad" },
  "lishu hanwang": { family: "HanWangLiSuMedium", file: "fonts/HanWangLiSuMedium.ttf", charSupport: "trad" },
  "hanwang-lisu-bold": { family: "HanWangLiSuBold", file: "fonts/HanWangLiSuBold.ttf", charSupport: "trad" },

  // Other Styles (行书/草书/魏碑)
  "zhimang-xingshu": { family: "ZhiMangXing", file: "fonts/ZhiMangXing.ttf", charSupport: "simp" },
  "liujian-maocao": { family: "LiuJianMaoCao", file: "fonts/LiuJianMaoCao.ttf", charSupport: "simp" },
  "longcang-xingshu": { family: "LongCang", file: "fonts/LongCang.ttf", charSupport: "simp" },
  "longcang": { family: "LongCang", file: "fonts/LongCang.ttf", charSupport: "simp" },
  "hanwang-xing-shu": { family: "HanWangXingShu", file: "fonts/HanWangXingShu.ttf", charSupport: "trad" },
  "hanwang-wei-bei": { family: "HanWangWeiBei", file: "fonts/HanWangWeiBei.ttf", charSupport: "trad" },
  "hanwang-pen-xing-kai": { family: "HanWangPenXingKai", file: "fonts/HanWangPenXingKai.ttf", charSupport: "trad" },

  // Song Ti & Woodblock (宋体 / 雕版刻本)
  "tw-sung": { family: "TWSung", file: "fonts/TW-Sung.ttf", charSupport: "trad" },
  "genryu-min": { family: "GenRyuMin", file: "fonts/GenRyuMin-Regular.otf", charSupport: "trad" },
  "genwan-min": { family: "GenWanMin", file: "fonts/GenWanMin-Regular.otf", charSupport: "trad" },

  // Fang Song (仿宋体)
  "cwtex-fangsong": { family: "cwTeXFangSong", file: "fonts/cwTeXFangSong.ttf", charSupport: "trad" },

  // Running, ShinSu & Monumental Styles (行书 / 新书体 / 榜书匾额)
  "hanwang-shinsu": { family: "HanWangShinSuMedium", file: "fonts/HanWangShinSuMedium.ttf", charSupport: "trad" },

  // Artist Fonts & New Traditional Wordset Additions (名家新收录字库)
  "bakudai-kai": { family: "Bakudai", file: "fonts/Bakudai-Regular.ttf", charSupport: "trad" },
  "masafont-xing": { family: "MasaFont", file: "fonts/MasaFont-Regular.ttf", charSupport: "trad" },
  "qiji-woodblock-kai": { family: "QijiWoodblock", file: "fonts/qiji-combo.ttf", charSupport: "trad" },
  "qiji-combo": { family: "QijiWoodblock", file: "fonts/qiji-combo.ttf", charSupport: "trad" },
  "iansui-kai": { family: "Iansui", file: "fonts/Iansui-Regular.ttf", charSupport: "trad" },
  "yuji-boku": { family: "YujiBoku", file: "fonts/YujiBoku-Regular.ttf", charSupport: "trad" },
  "yuji-mai": { family: "YujiMai", file: "fonts/YujiMai-Regular.ttf", charSupport: "trad" },
  "yuji-syuku": { family: "YujiSyuku", file: "fonts/YujiSyuku-Regular.ttf", charSupport: "trad" },
  "klee-one": { family: "KleeOne", file: "fonts/KleeOne-Regular.ttf", charSupport: "both" },
  "klee-one-semibold": { family: "KleeOneSemiBold", file: "fonts/KleeOne-SemiBold.ttf", charSupport: "both" },
  "cwtex-q-ming": { family: "cwTeXQMing", file: "fonts/cwTeXQMing-Medium.ttf", charSupport: "trad" },
  "cwtex-q-yuan": { family: "cwTeXQYuan", file: "fonts/cwTeXQYuan-Medium.ttf", charSupport: "trad" },
  "jason-handwriting1": { family: "JasonHandwriting1", file: "fonts/JasonHandwriting1-Regular.ttf", charSupport: "trad" },
  "jason-handwriting2": { family: "JasonHandwriting2", file: "fonts/JasonHandwriting2-Regular.ttf", charSupport: "trad" },
  "jason-handwriting3": { family: "JasonHandwriting3", file: "fonts/JasonHandwriting3-Regular.ttf", charSupport: "trad" },
  "jason-handwriting4": { family: "JasonHandwriting4", file: "fonts/JasonHandwriting4-Regular.ttf", charSupport: "trad" },
  "hanwang-kantan": { family: "HanWangKanTan", file: "fonts/HanWangKanTan.ttf", charSupport: "trad" }
};

// Preset classical calligraphy examples (no punctuation, returns for line breaks, 10+ Tang poems added)
const PRESET_EXAMPLES = [
  { id: "wangwei", name: "王维联句", trad: "明月松間照\n清泉石上流", simp: "明月松间照\n清泉石上流" },
  { id: "chunxiao", name: "春晓 (孟浩然)", trad: "春眠不覺曉\n處處聞啼鳥\n夜來風雨聲\n花落知多少", simp: "春眠不觉晓\n处处闻啼鸟\n夜来风雨声\n花落知多少" },
  { id: "jingye", name: "静夜思 (李白)", trad: "床前明月光\n疑是地上霜\n舉頭望明月\n低頭思故鄉", simp: "床前明月光\n疑是地上霜\n举头望明月\n低头思故乡" },
  { id: "guanque", name: "登鹳雀楼 (王之涣)", trad: "白日依山盡\n黃河入海流\n欲窮千里目\n更上一層樓", simp: "白日依山尽\n黄河入海流\n欲穷千里目\n更上一层楼" },
  { id: "jiangxue", name: "江雪 (柳宗元)", trad: "千山鳥飛絕\n萬徑人蹤滅\n孤舟蓑笠翁\n獨釣寒江雪", simp: "千山鸟飞绝\n万径人踪灭\n孤舟蓑笠翁\n独钓寒江雪" },
  { id: "xiangsi", name: "相思 (王维)", trad: "紅豆生南國\n春來發幾枝\n願君多采擷\n此物最相思", simp: "红豆生南国\n春来发几枝\n愿君多采撷\n此物最相思" },
  { id: "luchai", name: "鹿柴 (王维)", trad: "空山不見人\n但聞人語響\n返景入深林\n復照青苔上", simp: "空山不见人\n但闻人语响\n返景入深林\n复照青苔上" },
  { id: "lushan", name: "望庐山瀑布 (李白)", trad: "日照香爐生紫煙\n遙看瀑布挂前川\n飛流直下三千尺\n疑是銀河落九天", simp: "日照香炉生紫烟\n遥看瀑布挂前川\n飞流直下三千尺\n疑是银河落九天" },
  { id: "baidi", name: "早发白帝城 (李白)", trad: "朝辭白帝彩雲間\n千里江陵一日還\n兩岸猿聲啼不住\n輕舟已過萬重山", simp: "朝辞白帝彩云间\n千里江陵一日还\n两岸猿声啼不住\n轻舟已过万重山" },
  { id: "fengqiao", name: "枫桥夜泊 (张继)", trad: "月落烏啼霜滿天\n江楓漁火對愁眠\n姑蘇城外寒山寺\n夜半鐘聲到客船", simp: "月落乌啼霜满天\n江枫渔火对愁眠\n姑苏城外寒山寺\n夜半钟声到客船" },
  { id: "liangzhou", name: "凉州词 (王翰)", trad: "葡萄美酒夜光杯\n欲飲琵琶馬上催\n醉臥沙場君莫笑\n古來征戰幾人回", simp: "葡萄美酒夜光杯\n欲饮琵琶马上催\n醉卧沙场君莫笑\n古来征战几人回" },
  { id: "guyuan", name: "赋得古原草送别 (白居易)", trad: "離離原上草\n一歲一枯榮\n野火燒不盡\n春風吹又生", simp: "离离原上草\n一岁一枯荣\n野火烧不尽\n春风吹又生" },
  { id: "songdu", name: "送杜少府之任蜀州 (王勃)", trad: "城闕輔三秦\n風煙望五津\n與君離別意\n同是宦遊人\n海內存知己\n天涯若比鄰\n無為在岐路\n兒女共霑巾", simp: "城阙辅三秦\n风烟望五津\n与君离别意\n同是宦游人\n海内存知己\n天涯若比邻\n无为在歧路\n儿女共沾巾" },
  { id: "yong", name: "永字八法", trad: "永", simp: "永" },
  { id: "river", name: "春江花月夜", trad: "春江花月夜", simp: "春江花月夜" },
  { id: "lanting", name: "兰亭集序", trad: "永和九年\n歲在癸丑\n暮春之初\n會於會稽山陰之蘭亭\n修禊事也", simp: "永和九年\n岁在癸丑\n暮春之初\n会于会稽山阴之兰亭\n修禊事也" },
  { id: "redcliff", name: "赤壁怀古", trad: "大江東去\n浪淘盡\n千古風流人物\n故壘西邊\n人道是\n三國周郎赤壁", simp: "大江东去\n浪淘尽\n千古风流人物\n故垒西边\n人道是\n三国周郎赤壁" },
  { id: "houde", name: "厚德自强", trad: "厚德載物\n自強不息", simp: "厚德载物\n自强不息" }
];

// Fallback character dictionary for client-side offline conversion
const TRAD_FALLBACK = "萬與醜專業叢東絲丟兩嚴喪個豐臨為麗舉麼義樂喬習鄉書買亂爭於虧雲亞產畝親倫倉儀們價眾優偉傳傷倫儉僕優兒元兄充兆先光克免黨全八公六共興兵其具典冊再冒冕冠冬冰冶冷凍凝幾凡鳳凶出函刀刃分切刊刑列初判券刷刺刮制刹刻剃削前剔剖剛割創剷劇劈劉劍劑力功加劣動助勇勉勒勤動勘勝勞勢勤募勳勵勸勻勾包匈化北匙匹區十千午半華卑協卒卓單賣南博占卡盧印即危卵卷卸卻卿歷厥厲壓厭去參又叉反發叔取受叛台弁叛友雙反發變敘口古句叫可史右司台吃各合吉同名后吏向君吝吞吟吳告吹味呼命咆和咎咐咒呱咕咀咄咆咐咸咱咳哆哈哉哥員哦咧哪哼哭哮哲哽唆唇哺唉唆唐唔唑啼唯唱唾唸啃唬商啊問啟啡啜啞啟啡啄喋啼喧喃喊喙喋喚喝喘喧啾單喘喚啼啼喜喬喃單喋啼啾嗅喳嗆嗚嗜嗟嗡嗣嗤嗷嚎嗦嗝嗦嗔嗅嗖啼嗡嗣嗑嗟嗅嗆嗚嗜嗷嘎嘔嗽嘶嘈嘎嘲嘶嘹嘻嘮嘰嘻嘹嘰嘶噓嘲嘩嘶嘰嘯嘲嘹嘴嘻嘶嘹嘰嘶嘈嘶嘰囑嚕囌回因囡困囤囪囲図固國圖團圖圃圓圈國園圖圍圍圈團圓圈圓圍園圓圏團圇國圍團園圏圈圍圓圍團圖圍圏圓團土在地均坊坎坂坐坑塊堅壇壢培基堂堅堆堡堪堯報場塢塊塑塔塚塞填塵塹墊墒增墟墨墮墳墾壁壇壕壤壑士壯聲壹壺壽處備夕外夙多夜夠夢大天太夫央失頭夷夸夾奄奇奈奉奮奎奏契奔奕獎套奧奪奮女奴奶奸她好如妃妄妝婦媽妊妍妒妓妖妙妻妥妹妻妾姊始姓委姍娘姊姚姨姻姜姪姬娉娃娜娟娠娥娩娛娶媧婚婆婦媒媚媛婷媽媲嫁嫉嫌嫋嬪嬰嬸孀孃子字存孚孝季孤孟學孩孫孳孰孱孳學孺它宇守安宋完宏宗定宜官宙定宛宜寶實客宣室宥宦宮宰害宴家宵容宸寂寄寅密寇宿富寐寒寞察寡寢寤寥實寧寨審寫寬寮寵寶寸寺封射將專尋對導小少爾尖尚嘗尤就屍尺尼尾局屁居屆屋屎屏屑展屬屠履屬屯山屹屾嶼歲歲豐盡點筆畫經國書曉歸尋夢鳥詩語見難歡獨幽琴嘯深林知覺聞來隨無時過傳門開馬鍾顏錄鑑賞紙灑車貝計邊龍選擇齊東";
const SIMP_FALLBACK = "万与丑专业丛东丝丢两严丧个丰临为丽举么义乐乔习乡书买乱争于亏云亚产亩亲伦仓仪们价众优伟传伤伦俭仆优儿元兄充兆先光克免党全八公六共兴兵其具典册再冒冕冠冬冰冶冷冻凝几凡凤凶出函刀刃分切刊刑列初判券刷刺刮制刹刻剃削前剔剖刚割创铲剧劈刘剑剂力功加劣动助勇勉勒勤动勘胜劳势勤募勋励劝匀勾包匈化北匙匹区十千午半华卑协卒卓单卖南博占卡卢印即危卵卷卸却卿历厥厉压厌去参又叉反发叔取受叛台弁叛友双反发变叙口古句叫可史右司台吃各合吉同名后吏向君吝吞吟吴告吹味呼命咆和咎咐咒呱咕咀咄咆咐咸咱咳哆哈哉哥员哦咧哪哼哭哮哲哽唆唇哺唉唆唐唔唑啼唯唱唾念啃唬商啊问启啡啜哑启啡啄喋啼喧喃喊喙喋唤喝喘喧啾单喘唤啼啼喜乔喃单喋啼啾嗅喳呛呜嗜嗟嗡嗣嗤嗷嚎嗦嗝嗦嗔嗅嗖啼嗡嗣嗑嗟嗅呛呜嗜嗷嘎呕嗽嘶嘈嘎嘲嘶嘹嘻唠叽嘻嘹叽嘶嘘嘲哗嘶叽啸嘲嘹嘴嘻嘶嘹叽嘶嘈嘶叽瞩噜苏回因囡困囤囱围图固国图团图圃圆圈国园图围围圈团圆圈圆围园圆圈团囵国围团园圈圈围圆围团图围圈圆团土在地均坊坎坂坐坑块坚坛坜培基堂坚堆堡堪尧报场坞块塑塔冢塞填尘堑垫墒增墟墨堕坟垦壁坛壕壤壑士壮声壹壶寿处备夕外夙多夜够梦大天太夫央失头夷夸夹奄奇奈奉奋奎奏契奔奕奖套奥夺奋女奴奶奸她好如妃妄妆妇妈妊妍妒妓妖妙妻妥妹妻妾姊始姓委姗娘姊姚姨姻姜侄姬娉娃娜娟娠娥娩娱娶娲婚婆妇媒媚媛婷妈媲嫁嫉嫌袅嫔婴婶孀娘子字存孚孝季孤孟学孩孙孳孰孱孳学孺它宇守安宋完宏宗定宜官宙定宛宜宝实客宣室宥宦宫宰害宴家宵容宸寂寄寅密寇宿富寐寒寞察寡寝寤寥实宁寨审写宽寮宠宝寸寺封射将专寻对导小少尔尖尚尝尤就尸尺尼尾局屁居届屋屎屏屑展属屠履属屯山屹屾屿岁岁丰尽点笔画经国书晓归寻梦鸟诗语见难欢独幽琴啸深林知觉闻来随无时过传门开马钟颜录鉴赏纸洒车贝计边龙选择齐东";

function fallbackConvert(text, target) {
  if (!text) return "";
  let out = "";
  if (target === "trad") {
    for (const c of text) {
      const idx = SIMP_FALLBACK.indexOf(c);
      out += (idx !== -1 && TRAD_FALLBACK[idx]) ? TRAD_FALLBACK[idx] : c;
    }
  } else {
    for (const c of text) {
      const idx = TRAD_FALLBACK.indexOf(c);
      out += (idx !== -1 && SIMP_FALLBACK[idx]) ? SIMP_FALLBACK[idx] : c;
    }
  }
  return out;
}

let allFonts = [];
let activeFilters = {
  category: "all",
  char_support: "trad",
  medium: "all",
  search: ""
};

let currentScript = "simp"; // default simplified

// Dynamic @font-face injection
function registerFontFaces() {
  let cssRules = "";
  for (const [id, info] of Object.entries(LOCAL_FONTS_MAP)) {
    const filename = info.file.replace(/^fonts\//, "");
    const format = filename.endsWith(".otf") ? "opentype" : (filename.endsWith(".ttc") ? "collection" : "truetype");
    cssRules += `
      @font-face {
        font-family: '${info.family}';
        src: url('/fonts/${filename}') format('${format}');
        font-display: swap;
      }
    `;
  }
  const styleEl = document.createElement("style");
  styleEl.id = "dynamic-font-faces";
  styleEl.textContent = cssRules;
  document.head.appendChild(styleEl);
}

document.addEventListener('DOMContentLoaded', () => {
  registerFontFaces();

  const textInput = document.getElementById('text-input');
  const styleSelect = document.getElementById('style-select');
  const speedSelect = document.getElementById('speed-select');
  const fpsSelect = document.getElementById('fps-select');
  const punctuationSelect = document.getElementById('punctuation-select');
  const btnPreview = document.getElementById('btn-preview');
  const btnRender = document.getElementById('btn-render');
  const statusMessage = document.getElementById('status-message');
  const styleHint = document.getElementById('style-hint');

  // Live Stage Elements
  const calligraphyStage = document.getElementById('calligraphy-stage');
  const calligraphyText = document.getElementById('calligraphy-text');
  const activeFontBadge = document.getElementById('active-font-badge');
  const btnVertical = document.getElementById('btn-vertical');
  const btnHorizontal = document.getElementById('btn-horizontal');
  const fontSizeSlider = document.getElementById('font-size-slider');
  const fontSizeVal = document.getElementById('font-size-val');
  const spacingSlider = document.getElementById('spacing-slider');
  const spacingVal = document.getElementById('spacing-val');

  // Export elements
  const exportOutputBox = document.getElementById('export-output-box');
  const btnCloseExport = document.getElementById('btn-close-export');
  const previewImageContainer = document.getElementById('preview-image-container');
  const previewImg = document.getElementById('preview-img');
  const previewSvgContainer = document.getElementById('preview-svg-container');
  const videoContainer = document.getElementById('video-container');
  const resultVideo = document.getElementById('result-video');
  const jobsList = document.getElementById('jobs-list');

  const charCountEl = document.getElementById('char-count');
  const charCounterEl = document.getElementById('char-counter');
  const charLimitWarning = document.getElementById('char-warning') || document.getElementById('char-limit-warning');
  const MAX_CHARS = 256;
  const MAX_LINE_CHARS = 20;

  // Trad vs Simp toggle buttons
  const btnTrad = document.getElementById('btn-trad');
  const btnSimp = document.getElementById('btn-simp');
  const btnConvertCurrent = document.getElementById('btn-convert-current');

  // Strip punctuation for live stage preview when punctuation mode is 'omit'
  function stripPunctuationForStage(str) {
    if (!str) return '';
    return str.replace(/[，。！？、；：,.!?;:「」『』（）()“”‘’《》〈〉…—·【】〔〕［］｛｝～~—\-'"\s]/g, (match) => {
      // Preserve newlines for deliberate line breaks
      return match === '\n' ? '\n' : '';
    });
  }

  // Sync text input with live calligraphy stage
  function updateText() {
    const rawText = textInput.value;
    const len = rawText.length;
    if (charCountEl) charCountEl.textContent = len;

    const ignorePunct = !punctuationSelect || punctuationSelect.value === 'omit';
    const displayText = ignorePunct ? stripPunctuationForStage(rawText) : rawText;

    // Update real-time calligraphy stage text
    if (calligraphyText) {
      calligraphyText.textContent = displayText || '永';
    }

    const lines = textInput.value.split('\n');
    const longLines = lines
      .map((l, idx) => ({ num: idx + 1, len: [...l].length }))
      .filter(x => x.len > MAX_LINE_CHARS);
    const overLen = len > MAX_CHARS;
    const overLine = longLines.length > 0;
    const invalid = overLen || overLine;

    if (invalid) {
      if (charCounterEl) charCounterEl.classList.add('exceeded');
      textInput.classList.add('exceeded');
      if (charLimitWarning) {
        charLimitWarning.classList.remove('hidden');
        charLimitWarning.hidden = false;
        if (overLine) {
          const first = longLines[0];
          charLimitWarning.textContent = `第 ${first.num} 行含 ${first.len} 字，超出单行 ${MAX_LINE_CHARS} 字限制，请按回车换行分列`;
        } else {
          charLimitWarning.textContent = `总字数达 ${len} 字，超出 ${MAX_CHARS} 字上限，请删减`;
        }
      }
      if (typeof updateCanvasDimDisplay === 'function') updateCanvasDimDisplay();
      return false;
    } else {
      if (charCounterEl) charCounterEl.classList.remove('exceeded');
      textInput.classList.remove('exceeded');
      if (charLimitWarning) {
        charLimitWarning.classList.add('hidden');
        charLimitWarning.hidden = true;
      }
      if (typeof updateCanvasDimDisplay === 'function') updateCanvasDimDisplay();
      return true;
    }
  }

  // A conversion owns only the text revision and script choice it started with.
  let scriptConversionVersion = 0;
  let scriptConversionStatus = '';

  function invalidateScriptConversion() {
    scriptConversionVersion += 1;
    if (scriptConversionStatus && statusMessage.textContent === scriptConversionStatus) {
      hideStatus();
    }
    scriptConversionStatus = '';
  }

  textInput.addEventListener('input', () => {
    invalidateScriptConversion();
    updateText();
  });
  textInput.addEventListener('paste', () => setTimeout(updateText, 20));
  if (punctuationSelect) {
    punctuationSelect.addEventListener('change', updateText);
  }

  // High-precision Trad/Simp conversion with server-side zhconv + client fallback
  async function performScriptConversion(targetScript) {
    invalidateScriptConversion();
    const requestVersion = scriptConversionVersion;
    const originalText = textInput.value;
    // Track the latest choice immediately, including repeated toggle/font clicks.
    currentScript = targetScript;
    updateScriptButtons();
    renderPresets();
    if (!originalText.trim()) {
      return;
    }

    scriptConversionStatus = `正在转换文本为${targetScript === 'trad' ? '繁体' : '简体'}...`;
    showStatus(scriptConversionStatus, 'info');
    let convertedText;
    let usedFallback = false;
    try {
      const res = await fetch('/api/convert-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: originalText, target: targetScript })
      });
      if (!res.ok) throw new Error('Script conversion service unavailable');
      const data = await res.json();
      if (typeof data.text !== 'string') {
        throw new Error('Invalid script conversion response');
      }
      convertedText = data.text;
    } catch (e) {
      convertedText = fallbackConvert(originalText, targetScript);
      usedFallback = true;
    }

    // Also check the value in case another UI component replaced it without input.
    if (requestVersion !== scriptConversionVersion || textInput.value !== originalText) return;
    textInput.value = convertedText;
    updateText();
    if (statusMessage.textContent === scriptConversionStatus) {
      const scriptLabel = targetScript === 'trad' ? '繁体中文' : '简体中文';
      scriptConversionStatus = usedFallback
        ? `转换服务不可用，已使用离线字表转换为${scriptLabel}；部分字词可能未转换，请检查文本`
        : `已转换为${scriptLabel}`;
      showStatus(scriptConversionStatus, usedFallback ? 'info' : 'success');
      if (!usedFallback) {
        setTimeout(() => {
          if (requestVersion === scriptConversionVersion && statusMessage.textContent === scriptConversionStatus) {
            hideStatus();
          }
        }, 2500);
      }
    }
  }

  function updateScriptButtons() {
    if (currentScript === 'trad') {
      btnTrad.classList.add('active');
      btnSimp.classList.remove('active');
    } else {
      btnSimp.classList.add('active');
      btnTrad.classList.remove('active');
    }
  }

  btnTrad.addEventListener('click', () => performScriptConversion('trad'));
  btnSimp.addEventListener('click', () => performScriptConversion('simp'));
  btnConvertCurrent.addEventListener('click', () => {
    const nextScript = currentScript === 'trad' ? 'simp' : 'trad';
    performScriptConversion(nextScript);
  });

  // Determine character support of active selected font
  function getActiveFontCharSupport() {
    const styleId = styleSelect ? styleSelect.value : '';
    const fontMeta = allFonts.find(f => f.id === styleId || (styleId === 'mashanzheng' && f.id === 'mashanzheng-kai'));
    if (fontMeta) return fontMeta.char_support;
    if (LOCAL_FONTS_MAP[styleId]) return LOCAL_FONTS_MAP[styleId].charSupport;
    return "both";
  }

  // Render presets based on active font and currentScript
  function renderPresets() {
    const container = document.getElementById('preset-buttons-container') || document.getElementById('preset-list');
    if (!container) return;
    container.innerHTML = '';
    const activeSupport = getActiveFontCharSupport();
    PRESET_EXAMPLES.forEach(p => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'chip preset-chip preset-btn';
      // Prioritize font-supported character form
      let textToShow = currentScript === 'trad' ? p.trad : p.simp;
      if (activeSupport === 'trad') {
        textToShow = p.trad;
      } else if (activeSupport === 'simp') {
        textToShow = p.simp;
      }
      btn.textContent = p.name;
      btn.addEventListener('click', () => {
        invalidateScriptConversion();
        textInput.value = textToShow;
        updateText();
      });
      container.appendChild(btn);
    });
  }
  renderPresets();

  // Use the same persisted direction for the live stage and both export requests.
  const directionStorageKey = 'calligraphy.direction';
  let currentDirection = 'vertical-rl';
  try {
    const savedDirection = localStorage.getItem(directionStorageKey);
    if (savedDirection === 'horizontal-lr' || savedDirection === 'vertical-rl') {
      currentDirection = savedDirection;
    }
  } catch (_) {
    // Storage can be unavailable in private or restricted browser contexts.
  }

  function updateDirectionControls() {
    const vertical = currentDirection === 'vertical-rl';
    if (calligraphyStage) {
      calligraphyStage.classList.toggle('vertical', vertical);
      calligraphyStage.classList.toggle('horizontal', !vertical);
    }
    if (btnVertical && btnHorizontal) {
      btnVertical.classList.toggle('active', vertical);
      btnHorizontal.classList.toggle('active', !vertical);
      btnVertical.setAttribute('aria-pressed', String(vertical));
      btnHorizontal.setAttribute('aria-pressed', String(!vertical));
    }
  }

  function selectDirection(direction) {
    currentDirection = direction;
    updateDirectionControls();
    try {
      localStorage.setItem(directionStorageKey, direction);
    } catch (_) {
      // Exports still honor the selection when persistence is unavailable.
    }
  }

  updateDirectionControls();
  if (btnVertical && btnHorizontal) {
    btnVertical.addEventListener('click', () => selectDirection('vertical-rl'));
    btnHorizontal.addEventListener('click', () => selectDirection('horizontal-lr'));
  }

  // Font size slider
  if (fontSizeSlider && fontSizeVal && calligraphyText) {
    fontSizeSlider.addEventListener('input', (e) => {
      const px = e.target.value + 'px';
      fontSizeVal.textContent = px;
      calligraphyText.style.fontSize = px;
    });
  }

  // Character spacing slider
  if (spacingSlider && spacingVal && calligraphyText) {
    spacingSlider.addEventListener('input', (e) => {
      const em = e.target.value + 'em';
      spacingVal.textContent = em;
      calligraphyText.style.letterSpacing = em;
    });
  }

  // Paper atmosphere theme buttons
  document.querySelectorAll('.theme-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.theme-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const theme = btn.dataset.theme;
      document.body.className = theme;
    });
  });

  // Apply selected font to live calligraphy stage and update badge
  function applySelectedFont(styleId) {
    if (!calligraphyText) return;

    // Check local font mapping
    const fontInfo = LOCAL_FONTS_MAP[styleId];
    if (fontInfo) {
      calligraphyText.style.fontFamily = `'${fontInfo.family}', var(--font-serif)`;
    } else {
      calligraphyText.style.fontFamily = "var(--font-serif)";
    }

    // Find font metadata in catalog if available
    const fontMeta = allFonts.find(f => f.id === styleId || (styleId === 'mashanzheng' && f.id === 'mashanzheng-kai'));
    if (fontMeta && activeFontBadge) {
      activeFontBadge.innerHTML = `
        <strong>當前臨摹字庫：</strong>${fontMeta.name_zh} (${fontMeta.name_en}) ·
        <strong>書法脈系：</strong>${fontMeta.style_display} ·
        <strong>名家宗師：</strong>${fontMeta.artist} (${fontMeta.dynasty_era}) ·
        <strong>經典出處：</strong>${fontMeta.historical_reference || "傳世名作"}
      `;
    } else if (activeFontBadge) {
      activeFontBadge.innerHTML = `<strong>當前書法風格：</strong>${styleId}`;
    }

    // Automatically adapt example section and script toggle to font's support
    const activeSupport = getActiveFontCharSupport();
    if (activeSupport === 'trad' && currentScript !== 'trad') {
      performScriptConversion('trad');
    } else if (activeSupport === 'simp' && currentScript !== 'simp') {
      performScriptConversion('simp');
    } else {
      renderPresets();
    }

    updateStyleHint();
  }

  function updateStyleHint() {
    if (!styleHint) return;
    const val = styleSelect ? styleSelect.value : '';
    const activeSupport = getActiveFontCharSupport();
    if (val === 'i-yan-kai') {
      styleHint.innerHTML = '💡 <strong>刻石錄顏體</strong>：唐代顏真卿多寶塔碑真跡風骨，橫輕豎重，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'tw-kai') {
      styleHint.innerHTML = '💡 <strong>全字庫正楷體</strong>：CNS11643 標準正體，完全覆蓋唐詩三百首無一缺字，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'edukai') {
      styleHint.innerHTML = '💡 <strong>教育部標準楷書</strong>：國字標準楷體法度，筆意清挺中正，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'lxgw-wenkai-tc') {
      styleHint.innerHTML = '💡 <strong>霞鹜文楷繁體版</strong>：文人手書清雅風骨，全字庫完備覆蓋，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'tw-sung') {
      styleHint.innerHTML = '💡 <strong>全字庫正宋體</strong>：CNS11643 官方正宋體，金石刀刻筆意，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'genryu-min') {
      styleHint.innerHTML = '💡 <strong>源流明體</strong>：古典文人雕版印刷書風，刀筆兼備，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'genwan-min') {
      styleHint.innerHTML = '💡 <strong>源雲明體</strong>：水墨文人明體，筆畫交匯微帶墨暈滲透意趣，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'cwtex-fangsong') {
      styleHint.innerHTML = '💡 <strong>cwTeX 中仿宋</strong>：文人聚珍仿宋書風，骨力清挺，秀麗挺拔，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'hanwang-shinsu') {
      styleHint.innerHTML = '💡 <strong>王漢宗中新書</strong>：行氣流暢，結字明朗灑脫，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'mashanzheng' || val === 'mashanzheng-kai') {
      styleHint.innerHTML = '💡 <strong>鐘齊馬善政毛筆楷書</strong>：當代書法家馬善政先生原筆手寫真跡，剛勁有力，<strong>已自動切換為簡體法帖示例</strong>。';
    } else if (val === 'chill-qiuhong-kai') {
      styleHint.innerHTML = '💡 <strong>寒蟬秋鴻楷書</strong>：行意文人楷書風格，結體舒展清朗，<strong>已自動切換為簡體法帖示例</strong>。';
    } else if (val === 'lishu hanwang' || val === 'hanwang-lisu-medium') {
      styleHint.innerHTML = '💡 <strong>王漢宗中隸書</strong>：蠶頭燕尾、一波三折，漢隸典範，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'bakudai-kai') {
      styleHint.innerHTML = '💡 <strong>莫大毛筆楷書</strong>：青柳衡山殿堂大楷真跡，氣勢磅礴，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'masafont-xing') {
      styleHint.innerHTML = '💡 <strong>衡山毛筆行書</strong>：青柳衡山行書墨寶，行雲流水、灑脫奔放，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'qiji-woodblock-kai' || val === 'qiji-combo') {
      styleHint.innerHTML = '💡 <strong>閔齊伋令東齊伋體楷書</strong>：明代套印刻本巔峰之作，古雅絕倫、刀筆兼融，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'iansui-kai') {
      styleHint.innerHTML = '💡 <strong>芫荽硬筆楷書</strong>：ButTaiwan 依據手寫楷體改造，清麗溫潤，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'yuji-boku') {
      styleHint.innerHTML = '💡 <strong>佑字 · 墨</strong>：成田佑司手寫真跡，筆酣墨飽、枯筆飛白，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'yuji-mai') {
      styleHint.innerHTML = '💡 <strong>佑字 · 舞</strong>：成田佑司手寫真跡，翩若驚鴻、富於律動，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'yuji-syuku') {
      styleHint.innerHTML = '💡 <strong>佑字 · 宿</strong>：成田佑司手寫真跡，端穆沉靜、內斂古拙，<strong>已自動切換为繁體法帖示例</strong>。';
    } else if (val === 'klee-one' || val === 'klee-one-semibold') {
      styleHint.innerHTML = '💡 <strong>Fontworks Klee 手寫楷體</strong>：日本頂級字廠典範，兼具正楷法度與日常手書靈韻。';
    } else if (val.startsWith('jason-handwriting')) {
      styleHint.innerHTML = '💡 <strong>游清松清松手寫體</strong>：當代書法名家游清松先生數年全字庫手寫真跡，溫潤清秀。';
    } else if (activeSupport === 'trad') {
      styleHint.innerHTML = '💡 <strong>繁體字庫</strong>：當前選定傳統正體書法字庫，示例文本與揮毫已自動切換為繁體中文。';
    } else if (activeSupport === 'simp') {
      styleHint.innerHTML = '💡 <strong>簡體字庫</strong>：當前選定規範漢字字庫，示例文本與揮毫已自動切換為簡體中文。';
    } else {
      styleHint.innerHTML = '💡 <strong>繁簡兼備</strong>：當前字庫繁簡字形完備支持，可自由切換繁體與簡體揮毫創作。';
    }
  }

  styleSelect.addEventListener('change', () => {
    applySelectedFont(styleSelect.value);
  });

  function showStatus(text, type = 'info') {
    statusMessage.textContent = text;
    statusMessage.className = `status-message ${type}`;
    statusMessage.classList.remove('hidden');
  }

  function hideStatus() {
    statusMessage.classList.add('hidden');
  }

  function showPreviewImage(url) {
    if (exportOutputBox) exportOutputBox.classList.remove('hidden');
    videoContainer.classList.add('hidden');
    resultVideo.pause();
    previewImg.classList.remove('hidden');
    previewImg.src = url;
    previewSvgContainer.replaceChildren();
    previewSvgContainer.classList.add('hidden');
    previewImageContainer.classList.remove('hidden');
    exportOutputBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showPreviewSvg(svgContent) {
    if (exportOutputBox) exportOutputBox.classList.remove('hidden');
    videoContainer.classList.add('hidden');
    resultVideo.pause();
    previewImg.classList.add('hidden');
    // Keep the image node mounted for later direct and history previews.
    previewSvgContainer.innerHTML = svgContent;
    previewSvgContainer.classList.remove('hidden');
    const svgEl = previewSvgContainer.querySelector('svg');
    if (svgEl) {
      svgEl.style.maxWidth = '100%';
      svgEl.style.maxHeight = '420px';
      svgEl.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.08)';
    }
    previewImageContainer.classList.remove('hidden');
    exportOutputBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showVideo(videoUrl, downloadUrl) {
    if (exportOutputBox) exportOutputBox.classList.remove('hidden');
    previewImageContainer.classList.add('hidden');
    const dlBtn = document.getElementById('btn-video-dl');
    if (dlBtn && (downloadUrl || videoUrl)) {
      dlBtn.href = downloadUrl || videoUrl;
    }
    if (resultVideo && videoUrl) {
      resultVideo.src = videoUrl;
      resultVideo.load();
      resultVideo.play().catch(e => console.log('Autoplay deferred by browser:', e));
    }
    videoContainer.classList.remove('hidden');
    exportOutputBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  if (btnCloseExport) {
    btnCloseExport.addEventListener('click', () => {
      exportOutputBox.classList.add('hidden');
      resultVideo.pause();
    });
  }

  // Load styles from API
  async function loadStyles() {
    try {
      const res = await fetch('/api/styles');
      if (res.ok) {
        const data = await res.json();
        if (data.styles && data.styles.length > 0) {
          const currentVal = styleSelect.value;
          styleSelect.innerHTML = '';
          data.styles.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = `${s.name} - ${s.description}`;
            styleSelect.appendChild(opt);
          });
          // Default to generic Kai; preserve an explicitly selected style.
          if (currentVal && Array.from(styleSelect.options).some(o => o.value === currentVal)) {
            styleSelect.value = currentVal;
          } else if (Array.from(styleSelect.options).some(o => o.value === 'kai')) {
            styleSelect.value = 'kai';
          }
          applySelectedFont(styleSelect.value);
        }
      }
    } catch (e) {
      console.warn('Failed to load dynamic styles:', e);
    }
  }

  // Preview action
  btnPreview.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) {
      showStatus('請輸入要書寫的文本', 'error');
      return;
    }
    if (!updateText()) {
      showStatus(`輸入字符數量已超出 ${MAX_CHARS} 字符限制，請刪減後再預覽`, 'error');
      return;
    }

    const style = styleSelect.value;
    btnPreview.disabled = true;
    showStatus('正在生成高精度靜圖預覽...', 'info');

    try {
      const spacing = spacingSlider ? parseFloat(spacingSlider.value) : 0.18;
      const punctuation = punctuationSelect ? punctuationSelect.value : 'omit';
      const res = await fetch('/api/previews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, style, format: 'auto', spacing, direction: currentDirection, punctuation })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '預覽失敗');
      }

      const data = await res.json();
      if (data.svg) {
        showPreviewSvg(data.svg);
      } else if (data.preview_url) {
        showPreviewImage(data.preview_url);
      }
      showStatus('矢量靜圖生成完畢', 'success');
      setTimeout(hideStatus, 3000);
    } catch (e) {
      showStatus(`預覽失敗: ${e.message}`, 'error');
    } finally {
      btnPreview.disabled = false;
    }
  });

  // Render video action
  btnRender.addEventListener('click', async () => {
    if (btnRender.disabled) return;
    const text = textInput.value.trim();
    if (!text) {
      showStatus('請輸入要書寫的文本', 'error');
      return;
    }
    if (!updateText()) {
      showStatus(`輸入字符數量已超出 ${MAX_CHARS} 字符限制，請刪減後再生成`, 'error');
      return;
    }

    const style = styleSelect.value;
    const speed = parseFloat(speedSelect.value);
    const fps = parseInt(fpsSelect.value, 10);

    btnRender.disabled = true;
    hideStatus();

    try {
      const spacing = spacingSlider ? parseFloat(spacingSlider.value) : 0.18;
      const punctuation = punctuationSelect ? punctuationSelect.value : 'omit';
      const res = await fetch('/api/renders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, style, speed, fps, spacing, direction: currentDirection, punctuation })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '任務創建失敗');
      }

      await res.json();
      // Only submission owns the button. Progress belongs to the job card,
      // and a repeated request can reuse the same active server-side job.
      hasActiveJobs = true;
      loadJobs();
    } catch (e) {
      showStatus(`提交失败: ${e.message}`, 'error');
    } finally {
      btnRender.disabled = false;
    }
  });

  let jobsRefreshTimer = null;
  let jobsLoadVersion = 0;
  let hasActiveJobs = false;
  const activeJobStatuses = new Set(['queued', 'rendering', 'running']);

  // Load session job history
  async function loadJobs() {
    const version = ++jobsLoadVersion;
    clearTimeout(jobsRefreshTimer);
    try {
      const res = await fetch('/api/jobs');
      if (!res.ok) throw new Error('查询任务状态失败');
      const data = await res.json();
      // Ignore an older refresh that finishes after a new submission/refresh.
      if (version !== jobsLoadVersion) return;
      {
        hasActiveJobs = (data.jobs || []).some(j => activeJobStatuses.has(j.status));
        if (!data.jobs || data.jobs.length === 0) {
          jobsList.innerHTML = '<p class="empty-jobs">暫無生成任務</p>';
          return;
        }

        jobsList.innerHTML = '';
        data.jobs.forEach(j => {
          const item = document.createElement('div');
          item.className = 'job-item';
          item.dataset.jobId = j.job_id;

          const meta = document.createElement('div');
          meta.className = 'job-meta';

          const textEl = document.createElement('span');
          textEl.className = 'job-text';
          textEl.textContent = j.text.length > 15 ? j.text.substring(0, 15) + '...' : j.text;

          const details = document.createElement('span');
          details.className = 'job-details';
          details.textContent = `${j.style} · ${j.created_at.split('T')[1].substring(0, 5)}`;

          meta.appendChild(textEl);
          meta.appendChild(details);
          if (j.status === 'failed' && j.error_message) {
            const error = document.createElement('span');
            error.className = 'job-details job-error';
            error.textContent = j.error_message;
            meta.appendChild(error);
          }

          const action = document.createElement('div');
          action.className = 'job-action';
          const badge = document.createElement('span');
          badge.className = `job-status-badge ${j.status}`;
          const pct = Math.round(Math.max(0, Math.min(1, j.progress || 0)) * 100);
          const statusLabels = {
            queued: '排队中',
            rendering: `渲染中 (${pct}%)`,
            running: `渲染中 (${pct}%)`,
            succeeded: '完成',
            failed: '失败',
          };
          badge.textContent = statusLabels[j.status] || j.status;
          action.appendChild(badge);

          if (j.status === 'succeeded' && j.job_type === 'render') {
            const videoSrc = j.video_url || `/api/jobs/${j.job_id}/video`;
            const dlSrc = j.download_url || `/api/jobs/${j.job_id}/download`;

            const playBtn = document.createElement('button');
            playBtn.type = 'button';
            playBtn.className = 'btn-play-mini';
            playBtn.textContent = '▶ 播放';
            playBtn.title = '在上方視窗播放視頻';
            playBtn.addEventListener('click', (e) => {
              e.stopPropagation();
              showVideo(videoSrc, dlSrc);
            });
            action.appendChild(playBtn);

            const dl = document.createElement('a');
            dl.href = dlSrc;
            dl.className = 'btn-download';
            dl.textContent = '下載 MP4';
            dl.setAttribute('download', `calligraphy_${j.job_id}.mp4`);
            action.appendChild(dl);
          } else if (j.status === 'succeeded' && j.job_type === 'preview') {
            const viewBtn = document.createElement('button');
            viewBtn.type = 'button';
            viewBtn.className = 'btn-play-mini';
            viewBtn.textContent = '👁 查看';
            viewBtn.addEventListener('click', (e) => {
              e.stopPropagation();
              showPreviewImage(j.download_url || `/api/jobs/${j.job_id}/image`);
            });
            action.appendChild(viewBtn);
          }

          item.appendChild(meta);
          item.appendChild(action);
          jobsList.appendChild(item);
        });
      }
    } catch (e) {
      console.warn('Failed to load session jobs:', e);
    } finally {
      // Resume active jobs after a reload, retry transient network errors, and
      // never overlap polls or impose a browser-side render timeout.
      if (version === jobsLoadVersion && hasActiveJobs) {
        jobsRefreshTimer = setTimeout(loadJobs, 1000);
      }
    }
  }

  // =========================================================================
  // Font Catalog Browser Implementation
  // =========================================================================

  async function loadFontDatabase() {
    try {
      const res = await fetch('/api/font-catalog');
      if (!res.ok) return;
      allFonts = await res.json();
      updateHeaderCounts();
      setupCatalogFilters();
      renderFontGrid();
      // Apply active font info for the initial style
      applySelectedFont(styleSelect.value);
    } catch (e) {
      console.warn('Failed to load font database:', e);
    }
  }

  function updateHeaderCounts() {
    const kaiCnt = allFonts.filter(f => f.style_category === "kaishu").length;
    const liCnt = allFonts.filter(f => f.style_category === "lishu").length;
    const songCnt = allFonts.filter(f => f.style_category === "songti").length;
    const fsCnt = allFonts.filter(f => f.style_category === "fangsong").length;
    const otherCnt = allFonts.length - kaiCnt - liCnt - songCnt - fsCnt;

    const elTotal = document.getElementById("stat-total");
    const elKai = document.getElementById("stat-kai");
    const elLi = document.getElementById("stat-li");
    const elSong = document.getElementById("stat-song");
    const elFs = document.getElementById("stat-fs");
    const elOther = document.getElementById("stat-other");

    if (elTotal) elTotal.textContent = allFonts.length;
    if (elKai) elKai.textContent = kaiCnt;
    if (elLi) elLi.textContent = liCnt;
    if (elSong) elSong.textContent = songCnt;
    if (elFs) elFs.textContent = fsCnt;
    if (elOther) elOther.textContent = otherCnt;
  }

  function setupCatalogFilters() {
    const searchInput = document.getElementById("search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        activeFilters.search = e.target.value.trim().toLowerCase();
        renderFontGrid();
      });
    }

    document.querySelectorAll(".filter-pill").forEach(pill => {
      pill.addEventListener("click", () => {
        const filterType = pill.getAttribute("data-filter");
        const val = pill.getAttribute("data-val");

        const parentGroup = pill.parentElement;
        parentGroup.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
        pill.classList.add("active");

        activeFilters[filterType] = val;
        renderFontGrid();
      });
    });
  }

  function renderFontGrid() {
    const grid = document.getElementById("font-grid");
    if (!grid) return;
    grid.innerHTML = "";

    const filtered = allFonts.filter(f => {
      // 1. Style Category filter
      if (activeFilters.category !== "all" && f.style_category !== activeFilters.category) {
        return false;
      }
      // 3. Char Support filter
      if (activeFilters.char_support !== "all") {
        if (activeFilters.char_support === "trad" && f.char_support !== "trad" && f.char_support !== "both") {
          return false;
        }
        if (activeFilters.char_support === "simp" && f.char_support !== "simp" && f.char_support !== "both") {
          return false;
        }
        if (activeFilters.char_support === "both" && f.char_support !== "both") {
          return false;
        }
      }
      // 4. Medium filter
      if (activeFilters.medium !== "all" && f.medium !== activeFilters.medium) {
        return false;
      }
      // 5. Search
      if (activeFilters.search) {
        const s = activeFilters.search;
        const match = f.name_zh.toLowerCase().includes(s) ||
                      f.name_en.toLowerCase().includes(s) ||
                      f.artist.toLowerCase().includes(s) ||
                      f.style_display.toLowerCase().includes(s) ||
                      (f.historical_reference && f.historical_reference.toLowerCase().includes(s)) ||
                      f.font_author.toLowerCase().includes(s);
        if (!match) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 48px; color: var(--text-muted);">
          未找到符合篩選條件的書法字庫。您可點擊「全部風格」或「全部繁簡」查看歷代名家法帖。
        </div>
      `;
      return;
    }

    filtered.forEach(font => {
      const card = document.createElement("div");
      const isDl = font.is_downloaded === 1;
      card.className = `font-card ${isDl ? 'usable' : 'unavailable'}`;

      const local = LOCAL_FONTS_MAP[font.id];
      const previewFontFamily = (isDl && local) ? `'${local.family}', var(--font-serif)` : "var(--font-serif)";

      // Sample preview text adapted for Trad vs Simp (defaults to Traditional)
      let previewText = font.sample_text || "永和九年，歲在癸丑";
      if (font.char_support === "simp") {
        previewText = fallbackConvert(font.sample_text, "simp");
      } else {
        previewText = fallbackConvert(font.sample_text || "永和九年，歲在癸丑", "trad");
      }

      const charBadgeClass = font.char_support === "trad" ? "badge-trad" : (font.char_support === "simp" ? "badge-simp" : "badge-both");
      const charBadgeText = font.char_support === "trad" ? "繁體支持" : (font.char_support === "simp" ? "簡體優先" : "繁簡兼備");

      card.innerHTML = `
        <div class="card-header">
          <div class="card-title-group">
            <h3>${font.name_zh}</h3>
            <div class="pinyin-en">${font.name_en}</div>
          </div>
          <div class="badge-row">
            <span class="badge badge-style">${font.style_display}</span>
            <span class="badge ${charBadgeClass}">${charBadgeText}</span>
            <span class="badge ${font.medium === 'brush' ? 'badge-brush' : 'badge-pen'}">
              ${font.medium === 'brush' ? '毛筆' : '硬筆'}
            </span>
            ${isDl ? '<span class="badge badge-dl">✓ 離線可用</span>' : '<span class="badge badge-unavailable">典藏未載</span>'}
          </div>
        </div>

        <div class="card-glyph-preview" style="font-family: ${previewFontFamily};">
          ${previewText.substring(0, 5)}
        </div>

        <div class="card-metadata-table">
          <div class="meta-row">
            <span class="meta-label">宗師名家：</span>
            <span class="meta-value"><strong>${font.artist}</strong> (${font.dynasty_era})</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">經典法帖：</span>
            <span class="meta-value">${font.historical_reference || "歷代名家書道真跡"}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">開源造字：</span>
            <span class="meta-value">${font.font_author}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">開源協議：</span>
            <span class="meta-value">${font.license}</span>
          </div>
        </div>

        <div class="card-aesthetic-box">
          ${font.aesthetic_notes}
        </div>

        <div class="card-actions">
          ${isDl ? `
            <button type="button" class="card-btn btn-try" data-id="${font.id}">
              ✍️ 選用此字體創作
            </button>
          ` : `
            <span class="card-btn" style="background:var(--paper-bg); color:var(--text-muted); cursor:not-allowed;">
              📜 典藏收錄
            </span>
          `}
          <a href="${font.source_url}" target="_blank" rel="noopener noreferrer" class="card-btn btn-source">
            🔗 查閱源項目
          </a>
        </div>
      `;

      // Select font into studio button
      const tryBtn = card.querySelector(".btn-try");
      if (tryBtn) {
        tryBtn.addEventListener("click", () => {
          const targetStyleId = font.id === 'mashanzheng-kai' ? 'mashanzheng' : (font.id === 'hanwang-lisu-medium' ? 'lishu hanwang' : (font.id === 'longcang-xingshu' ? 'longcang' : font.id));
          
          let optionExists = Array.from(styleSelect.options).some(o => o.value === targetStyleId || o.value === font.id);
          if (optionExists) {
            styleSelect.value = targetStyleId;
          } else {
            const newOpt = document.createElement('option');
            newOpt.value = targetStyleId;
            newOpt.textContent = `${font.name_zh} (${font.name_en})`;
            styleSelect.appendChild(newOpt);
            styleSelect.value = targetStyleId;
          }

          // Apply selected font to live calligraphy stage immediately
          applySelectedFont(targetStyleId);

          // Auto-convert script if font prefers it
          if (font.char_support === "trad" && currentScript !== "trad") {
            performScriptConversion('trad');
          } else if (font.char_support === "simp" && currentScript !== "simp") {
            performScriptConversion('simp');
          }

          calligraphyStage.scrollIntoView({ behavior: 'smooth', block: 'center' });
          showStatus(`已選用【${font.name_zh}】，臨摹台已實時呈現，點擊「生成視頻」即可生成書寫動畫`, 'info');
        });
      }

      grid.appendChild(card);
    });
  }


  // =========================================================================
  // Redesigned Workbench Controllers (Router, Canvas Dimension, Font Picker)
  // =========================================================================

  const canvasFormats = document.getElementById('canvas-formats');
  const canvasLenSlider = document.getElementById('canvas-len-slider');
  const canvasLenVal = document.getElementById('canvas-len-val');
  const canvasLenAxis = document.getElementById('canvas-len-axis');
  const canvasDimVal = document.getElementById('canvas-dim-val');

  let canvasAutoLen = true;
  let canvasFormat = 'auto';
  let canvasWidth = 720;
  let canvasHeight = 960;

  function calcAutoCanvasDim() {
    const val = (textInput ? textInput.value : '永').trim() || '永';
    const lines = val.split('\n');
    const lineLens = lines.map(l => [...l].length);
    const maxLine = Math.max(...lineLens, 1);
    const numLines = Math.max(lines.length, 1);

    const isVert = currentDirection === 'vertical-rl';
    const targetCell = 68;
    const spacingValNum = spacingSlider ? parseFloat(spacingSlider.value) : 0.18;

    if (isVert) {
      const contentH = maxLine * (targetCell * 1.15) + (maxLine - 1) * (targetCell * spacingValNum);
      const marginY = Math.max(160, contentH * 0.16);
      let autoH = Math.round((contentH + marginY * 2) / 40) * 40;
      autoH = Math.max(720, Math.min(2200, autoH));

      let autoW = 720;
      if (numLines === 1) autoW = 640;
      else if (numLines === 2) autoW = 720;
      else if (numLines <= 4) autoW = 800;
      else autoW = Math.min(1280, Math.round((numLines * targetCell * 1.5 + 240) / 40) * 40);

      canvasWidth = autoW;
      canvasHeight = autoH;
    } else {
      const contentW = maxLine * (targetCell * 1.15) + (maxLine - 1) * (targetCell * spacingValNum);
      const marginX = Math.max(160, contentW * 0.16);
      let autoW = Math.round((contentW + marginX * 2) / 40) * 40;
      autoW = Math.max(880, Math.min(2400, autoW));
      let autoH = Math.min(1200, Math.max(540, Math.round((numLines * targetCell * 1.5 + 200) / 40) * 40));

      canvasWidth = autoW;
      canvasHeight = autoH;
    }
  }

  function updateCanvasDimDisplay() {
    if (canvasAutoLen || canvasFormat === 'auto') {
      calcAutoCanvasDim();
    }
    const isAuto = canvasAutoLen || canvasFormat === 'auto';
    const isVert = currentDirection === 'vertical-rl';
    const axis = isVert ? '高度' : '宽度';
    const len = isVert ? canvasHeight : canvasWidth;

    if (canvasLenAxis) canvasLenAxis.textContent = axis;
    if (canvasLenSlider) canvasLenSlider.value = len;
    if (canvasDimVal) canvasDimVal.textContent = `${canvasWidth} × ${canvasHeight}`;
    if (canvasLenVal) canvasLenVal.textContent = `${len}px`;

    if (canvasFormats) {
      canvasFormats.querySelectorAll('.chip').forEach(c => {
        if (isAuto) {
          c.classList.toggle('active', c.dataset.cf === 'auto');
        } else {
          c.classList.toggle('active', c.dataset.cf === canvasFormat);
        }
      });
    }
    if (calligraphyStage) {
      calligraphyStage.style.width = `${canvasWidth}px`;
      calligraphyStage.style.minHeight = `${canvasHeight}px`;
    }
  }

  if (canvasFormats) {
    canvasFormats.addEventListener('click', (ev) => {
      const b = ev.target.closest('.chip');
      if (!b) return;
      const cf = b.dataset.cf;
      if (cf === 'auto') {
        canvasAutoLen = true;
        canvasFormat = 'auto';
        calcAutoCanvasDim();
      } else {
        canvasAutoLen = false;
        canvasFormat = cf;
        canvasWidth = parseInt(b.dataset.w, 10);
        canvasHeight = parseInt(b.dataset.h, 10);
      }
      updateCanvasDimDisplay();
    });
  }

  if (canvasLenSlider) {
    canvasLenSlider.addEventListener('input', () => {
      canvasAutoLen = false;
      canvasFormat = 'custom';
      const val = parseInt(canvasLenSlider.value, 10);
      if (currentDirection === 'vertical-rl') {
        canvasHeight = val;
      } else {
        canvasWidth = val;
      }
      updateCanvasDimDisplay();
    });
  }

  // Views & Routing
  function updateRoute() {
    const hash = (location.hash || '').replace('#', '') || 'create';
    const view = ['create', 'history', 'fonts'].includes(hash) ? hash : 'create';
    document.body.dataset.view = view;
    document.querySelectorAll('.view').forEach(v => {
      v.hidden = v.id !== `view-${view}`;
    });
    document.querySelectorAll('[data-nav]').forEach(a => {
      if (a.getAttribute('data-nav') === view) {
        a.setAttribute('aria-current', 'page');
      }
    });
    try { if (window.scrollTo && !navigator?.userAgent?.includes('jsdom')) window.scrollTo(0, 0); } catch (_) {}
    if (view === 'history') loadJobs();
    if (view === 'fonts') renderFontGrid();
  }
  window.addEventListener('hashchange', updateRoute);
  updateRoute();

  // Canvas result tab switching
  const tabLive = document.getElementById('tab-live');
  const tabResult = document.getElementById('tab-result');
  const paneLive = document.getElementById('pane-live');
  const paneResult = document.getElementById('pane-result');

  function setCanvasTab(tab) {
    const live = tab === 'live';
    if (paneLive) paneLive.hidden = !live;
    if (paneResult) paneResult.hidden = live;
    if (tabLive) {
      tabLive.classList.toggle('active', live);
      tabLive.setAttribute('aria-selected', String(live));
    }
    if (tabResult) {
      tabResult.classList.toggle('active', !live);
      tabResult.setAttribute('aria-selected', String(!live));
    }
  }
  if (tabLive) tabLive.addEventListener('click', () => setCanvasTab('live'));
  if (tabResult) tabResult.addEventListener('click', () => setCanvasTab('result'));

  // Theme selector
  const themeSelect = document.getElementById('theme-select');
  if (themeSelect) {
    themeSelect.addEventListener('change', () => {
      document.body.classList.remove('theme-xuan', 'theme-gold', 'theme-rubbing');
      document.body.classList.add(themeSelect.value);
    });
  }

  // Font picker modal
  const fontPicker = document.getElementById('font-picker');
  const fontCurrent = document.getElementById('font-current');
  const fontCurrentName = document.getElementById('font-current-name');
  const fontCurrentSub = document.getElementById('font-current-sub');
  const fontCurrentGlyph = document.getElementById('font-current-glyph');
  const fontNote = document.getElementById('font-note');
  const fontRecent = document.getElementById('font-recent');
  const pickerList = document.getElementById('picker-list');
  const pickerSearch = document.getElementById('picker-search');

  let pickerActiveCat = 'all';
  let pickerActiveSup = 'all';
  let recentFonts = ['kai'];

  function renderRecentFonts() {
    if (!fontRecent) return;
    fontRecent.innerHTML = '';
    recentFonts.slice(0, 5).forEach(id => {
      const f = allFonts.find(x => x.id === id || (id === 'mashanzheng' && x.id === 'mashanzheng-kai'));
      const name = f ? f.name_zh : id;
      const chip = document.createElement('button');
      chip.type = 'button';
      chip.className = 'chip';
      chip.textContent = name;
      chip.addEventListener('click', () => {
        if (styleSelect) {
          styleSelect.value = id;
          applySelectedFont(id);
        }
      });
      fontRecent.appendChild(chip);
    });
  }

  function renderPicker() {
    if (!pickerList) return;
    pickerList.innerHTML = '';
    const q = pickerSearch ? pickerSearch.value.trim().toLowerCase() : '';
    const filtered = allFonts.filter(f => {
      if (pickerActiveCat !== 'all' && f.style_category !== pickerActiveCat) return false;
      if (pickerActiveSup !== 'all') {
        if (pickerActiveSup === 'trad' && f.char_support !== 'trad' && f.char_support !== 'both') return false;
        if (pickerActiveSup === 'simp' && f.char_support !== 'simp' && f.char_support !== 'both') return false;
      }
      if (q) {
        const hay = [f.name_zh, f.name_en, f.artist, f.style_display, f.historical_reference, f.font_author].join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    filtered.forEach(f => {
      const li = document.createElement('li');
      li.className = 'picker-item';
      const targetStyleId = f.id === 'mashanzheng-kai' ? 'mashanzheng' : (f.id === 'hanwang-lisu-medium' ? 'lishu hanwang' : (f.id === 'longcang-xingshu' ? 'longcang' : f.id));
      const isSelected = styleSelect && styleSelect.value === targetStyleId;
      if (isSelected) li.classList.add('selected');
      const fontInfo = LOCAL_FONTS_MAP[f.id];
      const fontFam = fontInfo ? `'${fontInfo.family}', var(--font-serif)` : 'var(--font-serif)';

      li.innerHTML = `
        <div class="picker-item-sample" style="font-family:${fontFam}">永</div>
        <div class="picker-item-meta">
          <strong>${f.name_zh}</strong>
          <small>${f.style_display} · ${f.artist} (${f.dynasty_era})</small>
        </div>
        <span class="badge ${f.char_support === 'trad' ? 'badge-trad' : (f.char_support === 'simp' ? 'badge-simp' : 'badge-both')}">
          ${f.char_support === 'trad' ? '繁体' : (f.char_support === 'simp' ? '简体' : '繁简')}
        </span>
      `;
      li.addEventListener('click', () => {
        if (styleSelect) {
          let opt = Array.from(styleSelect.options).find(o => o.value === targetStyleId);
          if (!opt) {
            opt = document.createElement('option');
            opt.value = targetStyleId;
            opt.textContent = `${f.name_zh} (${f.name_en})`;
            styleSelect.appendChild(opt);
          }
          styleSelect.value = targetStyleId;
        }
        applySelectedFont(targetStyleId);
        if (fontPicker) fontPicker.close();
      });
      pickerList.appendChild(li);
    });
  }

  function openPicker() {
    if (fontPicker) {
      renderPicker();
      fontPicker.showModal();
    }
  }

  if (fontCurrent) fontCurrent.addEventListener('click', openPicker);

  if (pickerSearch) {
    pickerSearch.addEventListener('input', renderPicker);
  }

  const pickerCats = document.getElementById('picker-cats');
  if (pickerCats) {
    pickerCats.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      pickerCats.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      pickerActiveCat = chip.dataset.cat;
      renderPicker();
    });
  }

  const pickerSupport = document.getElementById('picker-support');
  if (pickerSupport) {
    pickerSupport.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      pickerSupport.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      pickerActiveSup = chip.dataset.sup;
      renderPicker();
    });
  }

  document.querySelectorAll('dialog [data-close]').forEach(b => {
    b.addEventListener('click', (e) => {
      const d = e.target.closest('dialog');
      if (d) d.close();
    });
  });

  // Hook applySelectedFont to update font card
  const origApplySelectedFont = applySelectedFont;
  applySelectedFont = function(styleId) {
    origApplySelectedFont(styleId);
    const fontMeta = allFonts.find(f => f.id === styleId || (styleId === 'mashanzheng' && f.id === 'mashanzheng-kai'));
    const fontInfo = LOCAL_FONTS_MAP[styleId];
    if (fontCurrentName) fontCurrentName.textContent = fontMeta ? fontMeta.name_zh : styleId;
    if (fontCurrentSub && fontMeta) fontCurrentSub.textContent = `${fontMeta.style_display} · ${fontMeta.artist}`;
    if (fontCurrentGlyph) fontCurrentGlyph.style.fontFamily = fontInfo ? `'${fontInfo.family}', var(--font-serif)` : 'var(--font-serif)';
    if (fontNote && fontMeta) fontNote.textContent = fontMeta.aesthetic_notes || '';
    if (!recentFonts.includes(styleId)) {
      recentFonts = [styleId, ...recentFonts].slice(0, 5);
      renderRecentFonts();
    }
  };

  // Initial loads
  updateText();
  loadStyles();
  loadJobs();
  loadFontDatabase();
});
