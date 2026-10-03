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
  "hanwang-pen-kai": { family: "HanWangPenKai", file: "fonts/HanWangPenKai.ttf", charSupport: "trad" },
  "chill-qiuhong-kai": { family: "QiuHongKai", file: "fonts/QiuHongKai.ttf", charSupport: "simp" },
  "cwtex-q-kai": { family: "cwTeXQKai", file: "fonts/cwTeXQKai.ttf", charSupport: "trad" },
  "yanshu-chunfeng-kai": { family: "ChunFengKai", file: "fonts/ChunFengKai.ttf", charSupport: "simp" },
  "yanshu-youran-xiaokai": { family: "YouRanXiaoKai", file: "fonts/YouRanXiaoKai.ttf", charSupport: "simp" },
  "maoken-yingbi-kai": { family: "MaokenYingBiKai", file: "fonts/MaokenYingBiKai.ttf", charSupport: "simp" },
  "icrane-pen-kai": { family: "ICranePenKai", file: "fonts/ICranePenKai.ttf", charSupport: "trad" },
  "bpmf-zihi-kai": { family: "BpmfZihiKaiStd", file: "fonts/BpmfZihiKaiStd.ttf", charSupport: "trad" },
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
  "hanwang-boldpen-xingkai": { family: "HanWangBoldPenXingKai", file: "fonts/HanWangBoldPenXingKai.ttf", charSupport: "trad" },
  "hanwang-wave-kai": { family: "HanWangWaveKai", file: "fonts/HanWangWaveKai.ttf", charSupport: "trad" },

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
  "hanwang-kandayan": { family: "HanWangKanDaYan", file: "fonts/HanWangKanDaYan.ttf", charSupport: "trad" }
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
  { id: "yong", name: "永字八法", trad: "永", simp: "永" },
  { id: "river", name: "春江花月夜", trad: "春江花月夜", simp: "春江花月夜" },
  { id: "lanting", name: "兰亭集序", trad: "永和九年\n歲在癸丑\n暮春之初\n會於會稽山陰之蘭亭\n修禊事也", simp: "永和九年\n岁在癸丑\n暮春之初\n会于会稽山阴之兰亭\n修禊事也" },
  { id: "redcliff", name: "赤壁怀古", trad: "大江東去\n浪淘盡\n千古風流人物\n故壘西邊\n人道是三國周郎赤壁", simp: "大江东去\n浪淘尽\n千古风流人物\n故垒西边\n人道是三国周郎赤壁" },
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
  char_support: "all",
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
  const videoContainer = document.getElementById('video-container');
  const resultVideo = document.getElementById('result-video');
  const jobsList = document.getElementById('jobs-list');

  const charCountEl = document.getElementById('char-count');
  const charCounterEl = document.getElementById('char-counter');
  const charLimitWarning = document.getElementById('char-limit-warning');
  const MAX_CHARS = 256;

  // Trad vs Simp toggle buttons
  const btnTrad = document.getElementById('btn-trad');
  const btnSimp = document.getElementById('btn-simp');
  const btnConvertCurrent = document.getElementById('btn-convert-current');

  // Sync text input with live calligraphy stage
  function updateText() {
    const text = textInput.value;
    const len = text.length;
    if (charCountEl) charCountEl.textContent = len;

    // Update real-time calligraphy stage text
    if (calligraphyText) {
      calligraphyText.textContent = text || '永';
    }

    if (len > MAX_CHARS) {
      if (charCounterEl) charCounterEl.classList.add('exceeded');
      textInput.classList.add('exceeded');
      if (charLimitWarning) {
        charLimitWarning.classList.remove('hidden');
        charLimitWarning.textContent = `⚠️ 文本长度已达 ${len} 字符，超出 ${MAX_CHARS} 字符上限（超出 ${len - MAX_CHARS} 字），请删减后再生成`;
      }
      return false;
    } else {
      if (charCounterEl) charCounterEl.classList.remove('exceeded');
      textInput.classList.remove('exceeded');
      if (charLimitWarning) charLimitWarning.classList.add('hidden');
      return true;
    }
  }

  textInput.addEventListener('input', updateText);
  textInput.addEventListener('paste', () => setTimeout(updateText, 20));

  // High-precision Trad/Simp conversion with server-side zhconv + client fallback
  async function performScriptConversion(targetScript) {
    const originalText = textInput.value;
    if (!originalText.trim()) {
      currentScript = targetScript;
      updateScriptButtons();
      renderPresets();
      return;
    }

    showStatus(`正在转换文本为${targetScript === 'trad' ? '繁体' : '简体'}...`, 'info');
    try {
      const res = await fetch('/api/convert-script', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: originalText, target: targetScript })
      });
      if (res.ok) {
        const data = await res.json();
        textInput.value = data.text;
      } else {
        textInput.value = fallbackConvert(originalText, targetScript);
      }
    } catch (e) {
      textInput.value = fallbackConvert(originalText, targetScript);
    }

    currentScript = targetScript;
    updateScriptButtons();
    updateText();
    renderPresets();
    showStatus(`已转换为${targetScript === 'trad' ? '繁体中文' : '简体中文'}`, 'success');
    setTimeout(hideStatus, 2500);
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
    const container = document.getElementById('preset-buttons-container');
    if (!container) return;
    container.innerHTML = '';
    const activeSupport = getActiveFontCharSupport();
    PRESET_EXAMPLES.forEach(p => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'preset-btn';
      // Prioritize font-supported character form
      let textToShow = currentScript === 'trad' ? p.trad : p.simp;
      if (activeSupport === 'trad') {
        textToShow = p.trad;
      } else if (activeSupport === 'simp') {
        textToShow = p.simp;
      }
      btn.textContent = p.name;
      btn.addEventListener('click', () => {
        textInput.value = textToShow;
        updateText();
      });
      container.appendChild(btn);
    });
  }
  renderPresets();

  // Layout direction toggle (Vertical vs Horizontal)
  if (btnVertical && btnHorizontal && calligraphyStage) {
    btnVertical.addEventListener('click', () => {
      btnVertical.classList.add('active');
      btnHorizontal.classList.remove('active');
      calligraphyStage.classList.remove('horizontal');
      calligraphyStage.classList.add('vertical');
    });

    btnHorizontal.addEventListener('click', () => {
      btnHorizontal.classList.add('active');
      btnVertical.classList.remove('active');
      calligraphyStage.classList.remove('vertical');
      calligraphyStage.classList.add('horizontal');
    });
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
        <strong>当前临摹字库：</strong>${fontMeta.name_zh} (${fontMeta.name_en}) · 
        <strong>书法脉系：</strong>${fontMeta.style_display} · 
        <strong>名家宗师：</strong>${fontMeta.artist} (${fontMeta.dynasty_era}) · 
        <strong>经典出处：</strong>${fontMeta.historical_reference || "传世名作"}
      `;
    } else if (activeFontBadge) {
      activeFontBadge.innerHTML = `<strong>当前书法风格：</strong>${styleId}`;
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
    const val = styleSelect.value;
    const activeSupport = getActiveFontCharSupport();
    if (val === 'i-yan-kai') {
      styleHint.innerHTML = '💡 <strong>刻石录颜体</strong>：唐代颜真卿多宝塔碑真迹风骨，横轻竖重，<strong>已自动切换为繁体法帖示例</strong>。';
    } else if (val === 'tw-kai') {
      styleHint.innerHTML = '💡 <strong>全字库正楷体</strong>：CNS11643 标准正体，完全覆盖唐诗三百首无一缺字，<strong>已自动切换为繁体法帖示例</strong>。';
    } else if (val === 'edukai') {
      styleHint.innerHTML = '💡 <strong>教育部标准楷书</strong>：国字标准楷体法度，笔意清挺中正，<strong>已自动切换为繁体法帖示例</strong>。';
    } else if (val === 'lxgw-wenkai-tc') {
      styleHint.innerHTML = '💡 <strong>霞鹜文楷繁体版</strong>：文人手书清雅风骨，全字库完备覆盖，<strong>已自动切换为繁体法帖示例</strong>。';
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
    } else if (val === 'hanwang-kandayan') {
      styleHint.innerHTML = '💡 <strong>王漢宗堪亭大字</strong>：傳統招幌牌匾榜書大字，筆勢盤旋，雄渾厚重，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'mashanzheng' || val === 'mashanzheng-kai') {
      styleHint.innerHTML = '💡 <strong>钟齐马善政毛笔楷书</strong>：当代书法家马善政先生原笔手写真迹，刚劲有力，<strong>已自动切换为简体法帖示例</strong>。';
    } else if (val === 'chill-qiuhong-kai') {
      styleHint.innerHTML = '💡 <strong>寒蝉秋鸿楷书</strong>：行意文人楷书风格，结体舒展清朗，<strong>已自动切换为简体法帖示例</strong>。';
    } else if (val === 'lishu hanwang' || val === 'hanwang-lisu-medium') {
      styleHint.innerHTML = '💡 <strong>王汉宗中隶书</strong>：蚕头燕尾、一波三折，汉隶典范，<strong>已自动切换为繁体法帖示例</strong>。';
    } else if (activeSupport === 'trad') {
      styleHint.innerHTML = '💡 <strong>繁体字库</strong>：当前选定传统正体书法字库，示例文本与挥毫已自动切换为繁体中文。';
    } else if (activeSupport === 'simp') {
      styleHint.innerHTML = '💡 <strong>简体字库</strong>：当前选定规范汉字字库，示例文本与挥毫已自动切换为简体中文。';
    } else {
      styleHint.innerHTML = '💡 <strong>繁简兼备</strong>：当前字库繁简字形完备支持，可自由切换繁体与简体挥毫创作。';
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
    previewImg.classList.remove('hidden');
    previewImg.src = url;
    const existingSvg = previewImageContainer.querySelector('svg');
    if (existingSvg) existingSvg.remove();
    previewImageContainer.classList.remove('hidden');
    exportOutputBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showPreviewSvg(svgContent) {
    if (exportOutputBox) exportOutputBox.classList.remove('hidden');
    videoContainer.classList.add('hidden');
    previewImg.classList.add('hidden');
    previewImageContainer.innerHTML = svgContent;
    const svgEl = previewImageContainer.querySelector('svg');
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
      showStatus('请输入要书写的文本', 'error');
      return;
    }
    if (!updateText()) {
      showStatus(`输入字符数量已超出 ${MAX_CHARS} 字符限制，请删减后再预览`, 'error');
      return;
    }

    const style = styleSelect.value;
    btnPreview.disabled = true;
    showStatus('正在生成高精度静图预览...', 'info');

    try {
      const spacing = spacingSlider ? parseFloat(spacingSlider.value) : 0.18;
      const res = await fetch('/api/previews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, style, format: 'auto', spacing })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '预览失败');
      }

      const data = await res.json();
      if (data.svg) {
        showPreviewSvg(data.svg);
      } else if (data.preview_url) {
        showPreviewImage(data.preview_url);
      }
      showStatus('矢量静图生成完毕', 'success');
      setTimeout(hideStatus, 3000);
    } catch (e) {
      showStatus(`预览失败: ${e.message}`, 'error');
    } finally {
      btnPreview.disabled = false;
    }
  });

  // Render video action
  btnRender.addEventListener('click', async () => {
    const text = textInput.value.trim();
    if (!text) {
      showStatus('请输入要书写的文本', 'error');
      return;
    }
    if (!updateText()) {
      showStatus(`输入字符数量已超出 ${MAX_CHARS} 字符限制，请删减后再生成`, 'error');
      return;
    }

    const style = styleSelect.value;
    const speed = parseFloat(speedSelect.value);
    const fps = parseInt(fpsSelect.value, 10);

    btnRender.disabled = true;
    showStatus('正在提交书写视频渲染任务...', 'info');

    try {
      const spacing = spacingSlider ? parseFloat(spacingSlider.value) : 0.18;
      const res = await fetch('/api/renders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, style, speed, fps, spacing })
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || '任务创建失败');
      }

      const data = await res.json();
      const jobId = data.job_id;
      showStatus('任务已入队，正在逐笔拓扑重构与编码视频...', 'info');

      pollJob(jobId);
    } catch (e) {
      showStatus(`提交失败: ${e.message}`, 'error');
      btnRender.disabled = false;
    }
  });

  // Poll job status
  async function pollJob(jobId) {
    const pollInterval = 1000;
    const maxAttempts = 180;
    let attempts = 0;

    const timer = setInterval(async () => {
      attempts++;
      try {
        const res = await fetch(`/api/jobs/${jobId}`);
        if (!res.ok) throw new Error('查询任务状态失败');

        const job = await res.json();
        if (job.status === 'succeeded') {
          clearInterval(timer);
          btnRender.disabled = false;
          showStatus('书写视频生成完成！已就绪', 'success');
          const videoSrc = job.video_url || job.download_url;
          showVideo(videoSrc, job.download_url);
          loadJobs();
          setTimeout(hideStatus, 4000);
        } else if (job.status === 'failed') {
          clearInterval(timer);
          btnRender.disabled = false;
          showStatus(`渲染失败: ${job.error_message || '未知错误'}`, 'error');
        } else {
          const pct = Math.round((job.progress || 0) * 100);
          showStatus(`书写视频渲染中 (${pct}%)...`, 'info');
        }
      } catch (e) {
        console.error(e);
      }

      if (attempts >= maxAttempts) {
        clearInterval(timer);
        btnRender.disabled = false;
        showStatus('渲染超时，请检查控制台或重新尝试', 'error');
      }
    }, pollInterval);
  }

  // Load session job history
  async function loadJobs() {
    try {
      const res = await fetch('/api/jobs');
      if (res.ok) {
        const data = await res.json();
        if (!data.jobs || data.jobs.length === 0) {
          jobsList.innerHTML = '<p class="empty-jobs">暂无生成任务</p>';
          return;
        }

        jobsList.innerHTML = '';
        data.jobs.forEach(j => {
          const item = document.createElement('div');
          item.className = 'job-item';

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

          const action = document.createElement('div');
          action.className = 'job-action';

          if (j.status === 'succeeded' && j.job_type === 'render') {
            const videoSrc = j.video_url || `/api/jobs/${j.job_id}/video`;
            const dlSrc = j.download_url || `/api/jobs/${j.job_id}/download`;

            const playBtn = document.createElement('button');
            playBtn.type = 'button';
            playBtn.className = 'btn-play-mini';
            playBtn.textContent = '▶ 播放';
            playBtn.title = '在上方视窗播放视频';
            playBtn.addEventListener('click', (e) => {
              e.stopPropagation();
              showVideo(videoSrc, dlSrc);
            });
            action.appendChild(playBtn);

            const dl = document.createElement('a');
            dl.href = dlSrc;
            dl.className = 'btn-download';
            dl.textContent = '下载 MP4';
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
          } else {
            const badge = document.createElement('span');
            badge.className = `job-status-badge ${j.status}`;
            badge.textContent = j.status === 'succeeded' ? '完成' : (j.status === 'failed' ? '失败' : '处理中');
            action.appendChild(badge);
          }

          item.appendChild(meta);
          item.appendChild(action);
          jobsList.appendChild(item);
        });
      }
    } catch (e) {
      console.warn('Failed to load session jobs:', e);
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
          未找到符合筛选条件的书法字库。您可点击「全部收录」查看历代名家法帖。
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

      // Sample preview text adapted for Trad vs Simp
      let previewText = font.sample_text || "永和九年，天朗气清";
      if (font.char_support === "trad") {
        previewText = fallbackConvert(font.sample_text, "trad");
      } else if (font.char_support === "simp") {
        previewText = fallbackConvert(font.sample_text, "simp");
      } else {
        previewText = currentScript === "trad" ? fallbackConvert(font.sample_text, "trad") : fallbackConvert(font.sample_text, "simp");
      }

      const charBadgeClass = font.char_support === "trad" ? "badge-trad" : (font.char_support === "simp" ? "badge-simp" : "badge-both");
      const charBadgeText = font.char_support === "trad" ? "繁体支持" : (font.char_support === "simp" ? "简体优先" : "繁简兼备");

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
              ${font.medium === 'brush' ? '毛笔' : '硬笔'}
            </span>
            ${isDl ? '<span class="badge badge-dl">✓ 离线可用</span>' : '<span class="badge badge-unavailable">典藏未载</span>'}
          </div>
        </div>

        <div class="card-glyph-preview" style="font-family: ${previewFontFamily};">
          ${previewText.substring(0, 5)}
        </div>

        <div class="card-metadata-table">
          <div class="meta-row">
            <span class="meta-label">宗师名家：</span>
            <span class="meta-value"><strong>${font.artist}</strong> (${font.dynasty_era})</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">经典法帖：</span>
            <span class="meta-value">${font.historical_reference || "历代名家书道真迹"}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">开源造字：</span>
            <span class="meta-value">${font.font_author}</span>
          </div>
          <div class="meta-row">
            <span class="meta-label">开源协议：</span>
            <span class="meta-value">${font.license}</span>
          </div>
        </div>

        <div class="card-aesthetic-box">
          ${font.aesthetic_notes}
        </div>

        <div class="card-actions">
          ${isDl ? `
            <button type="button" class="card-btn btn-try" data-id="${font.id}">
              ✍️ 选用此字体创作
            </button>
          ` : `
            <span class="card-btn" style="background:var(--paper-bg); color:var(--text-muted); cursor:not-allowed;">
              📜 典藏收录
            </span>
          `}
          <a href="${font.source_url}" target="_blank" rel="noopener noreferrer" class="card-btn btn-source">
            🔗 查阅源项目
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
          showStatus(`已选用【${font.name_zh}】，临摹台已实时呈现，点击「生成视频」即可生成书写动画`, 'info');
        });
      }

      grid.appendChild(card);
    });
  }

  // Initial loads
  updateText();
  loadStyles();
  loadJobs();
  loadFontDatabase();
});
