/**
 * app.js - Calligraphy Font Studio Application
 * Comprehensive Traditional vs Simplified support and Usability filtering.
 */

// Downloaded font mappings to @font-face families
const LOCAL_FONTS_MAP = {
  "hanwang-yan-kai": { family: "HanWangYanKai", file: "fonts/HanWangYanKai.ttf", charSupport: "trad" },
  "mashanzheng-kai": { family: "MaShanZheng", file: "fonts/MaShanZheng.ttf", charSupport: "simp" },
  "hanwang-medium-kai": { family: "HanWangMediumKai", file: "fonts/HanWangMediumKai.ttf", charSupport: "trad" },
  "hanwang-pen-kai": { family: "HanWangPenKai", file: "fonts/HanWangPenKai.ttf", charSupport: "trad" },
  "lxgw-wenkai": { family: "LXGWWenKai", file: "fonts/LXGWWenKai-Regular.ttf", charSupport: "both" },
  "klee-one": { family: "KleeOne", file: "fonts/KleeOne.ttf", charSupport: "trad" },
  "coqubeli-rubbing": { family: "CoQuBeLi", file: "fonts/CoQuBeLi.ttf", charSupport: "trad" },
  "hanwang-lisu-medium": { family: "HanWangLiSuMedium", file: "fonts/HanWangLiSuMedium.ttf", charSupport: "trad" },
  "hanwang-lisu-bold": { family: "HanWangLiSuBold", file: "fonts/HanWangLiSuBold.ttf", charSupport: "trad" },
  "zhimang-xingshu": { family: "ZhiMangXing", file: "fonts/ZhiMangXing.ttf", charSupport: "simp" },
  "liujian-maocao": { family: "LiuJianMaoCao", file: "fonts/LiuJianMaoCao.ttf", charSupport: "simp" },
  "longcang-xingshu": { family: "LongCang", file: "fonts/LongCang.ttf", charSupport: "simp" },
  "hanwang-xing-shu": { family: "HanWangXingShu", file: "fonts/HanWangXingShu.ttf", charSupport: "trad" },
  "hanwang-wei-bei": { family: "HanWangWeiBei", file: "fonts/HanWangWeiBei.ttf", charSupport: "trad" },
  "hanwang-pen-xing-kai": { family: "HanWangPenXingKai", file: "fonts/HanWangPenXingKai.ttf", charSupport: "trad" },
  "yuji-boku": { family: "YujiBoku", file: "fonts/YujiBoku.ttf", charSupport: "trad" },
  "arphic-ukai": { family: "ArphicUKai", file: "fonts/ArphicUKai.ttc", charSupport: "both" }
};

// Preset examples in Traditional and Simplified Chinese
const PRESET_EXAMPLES = [
  { id: "yong", name: "永字八法", trad: "永", simp: "永" },
  { id: "river", name: "春江花月夜", trad: "春江花月夜", simp: "春江花月夜" },
  { id: "wangwei", name: "王維對聯", trad: "明月松間照\n清泉石上流", simp: "明月松间照\n清泉石上流" },
  { id: "lanting", name: "蘭亭集序", trad: "永和九年\n歲在癸丑\n暮春之初\n會於會稽山陰之蘭亭\n修禊事也", simp: "永和九年\n岁在癸丑\n暮春之初\n会于会稽山阴之兰亭\n修禊事也" },
  { id: "redcliff", name: "赤壁懷古", trad: "大江東去\n浪淘盡\n千古風流人物\n故壘西邊\n人道是三國周郎赤壁", simp: "大江东去\n浪淘尽\n千古风流人物\n故垒西边\n人道是三国周郎赤壁" },
  { id: "huifeng", name: "惠風和暢", trad: "天朗氣清\n惠風和暢", simp: "天朗气清\n惠风和畅" },
  { id: "houde", name: "厚德寧靜", trad: "厚德載物\n寧靜致遠", simp: "厚德载物\n宁静致远" },
  { id: "gong", name: "天下為公", trad: "大道之行也\n天下為公\n選賢與能\n講信修睦", simp: "大道之行也\n天下为公\n选贤与能\n讲信修睦" },
  { id: "luoxia", name: "滕王閣序", trad: "落霞與孤鶩齊飛\n秋水共長天一色", simp: "落霞与孤鹜齐飞\n秋水共长天一色" }
];

// Common Traditional <-> Simplified bidirectional dictionary
const TRAD_CHARS = "萬與醜專業叢東絲丟兩嚴喪個豐臨為麗舉麼義樂喬習鄉書買亂爭於虧雲亞產畝親倫倉儀們價眾優偉傳傷倫儉僕優兒元兄充兆先光克免黨全八公六共興兵其具典冊再冒冕冠冬冰冶冷凍凝幾凡鳳凶出函刀刃分切刊刑列初判券刷刺刮制刹刻剃削前剔剖剛割創剷劇劈劉劍劑力功加劣動助勇勉勒勤動勘勝勞勢勤募勳勵勸勻勾包匈化北匙匹區十千午半華卑協卒卓單賣南博占卡盧印即危卵卷卸卻卿歷厥厲壓厭去參又叉反發叔取受叛台弁叛友雙反發變敘口古句叫可史右司台吃各合吉同名后吏向君吝吞吟吳告吹味呼命咆和咎咐咒呱咕咀咄咆咐咸咱咳哆哈哉哥員哦咧哪哼哭哮哲哽唆唇哺唉唆唐唔唑啼唯唱唾唸啃唬商啊問啟啡啜啞啟啡啄喋啼喧喃喊喙喋喚喝喘喧啾單喘喚啼啼喜喬喃單喋啼啾嗅喳嗆嗚嗜嗟嗡嗣嗤嗷嚎嗦嗝嗦嗔嗅嗖啼嗡嗣嗑嗟嗅嗆嗚嗜嗷嘎嘔嗽嘶嘈嘎嘲嘶嘹嘻嘮嘰嘻嘹嘰嘶噓嘲嘩嘶嘰嘯嘲嘹嘴嘻嘶嘹嘰嘶嘈嘶嘰囑嚕囌回因囡困囤囪囲図固國圖團圖圃圓圈國園圖圍圍圈團圓圈圓圍園圓圏團圇國圍團園圏圈圍圓圍團圖圍圏圓團土在地均坊坎坂坐坑塊堅壇壢培基堂堅堆堡堪堯報場塢塊塑塔塚塞填塵塹墊墒增墟墨墮墳墾壁壇壕壤壑士壯聲壹壺壽處備夕外夙多夜夠夢大天太夫央失頭夷夸夾奄奇奈奉奮奎奏契奔奕獎套奧奪奮女奴奶奸她好如妃妄妝婦媽妊妍妒妓妖妙妻妥妹妻妾姊始姓委姍娘姊姚姨姻姜姪姬娉娃娜娟娠娥娩娛娶媧婚婆婦媒媚媛婷媽媲嫁嫉嫌嫋嬪嬰嬸孀孃子字存孚孝季孤孟學孩孫孳孰孱孳學孺它宇守安宋完宏宗定宜官宙定宛宜寶實客宣室宥宦宮宰害宴家宵容宸寂寄寅密寇宿富寐寒寞察寡寢寤寥實寧寨審寫寬寮寵寶寸寺封射將專尋對導小少爾尖尚嘗尤就屍尺尼尾局屁居屆屋屎屏屑展屬屠履屬屯山屹屾嶼歲歲豐盡點筆畫經國書";
const SIMP_CHARS = "万与丑专业丛东丝丢两严丧个丰临为丽举么义乐乔习乡书买乱争于亏云亚产亩亲伦仓仪们价众优伟传伤伦俭仆优儿元兄充兆先光克免党全八公六共兴兵其具典册再冒冕冠冬冰冶冷冻凝几凡凤凶出函刀刃分切刊刑列初判券刷刺刮制刹刻剃削前剔剖刚割创铲剧劈刘剑剂力功加劣动助勇勉勒勤动勘胜劳势勤募勋励劝匀勾包匈化北匙匹区十千午半华卑协卒卓单卖南博占卡卢印即危卵卷卸却卿历厥厉压厌去参又叉反发叔取受叛台弁叛友双反发变叙口古句叫可史右司台吃各合吉同名后吏向君吝吞吟吴告吹味呼命咆和咎咐咒呱咕咀咄咆咐咸咱咳哆哈哉哥员哦咧哪哼哭哮哲哽唆唇哺唉唆唐唔唑啼唯唱唾念啃唬商啊问启啡啜哑启啡啄喋啼喧喃喊喙喋唤喝喘喧啾单喘唤啼啼喜乔喃单喋啼啾嗅喳呛呜嗜嗟嗡嗣嗤嗷嚎嗦嗝嗦嗔嗅嗖啼嗡嗣嗑嗟嗅呛呜嗜嗷嘎呕嗽嘶嘈嘎嘲嘶嘹嘻唠叽嘻嘹叽嘶嘘嘲哗嘶叽啸嘲嘹嘴嘻嘶嘹叽嘶嘈嘶叽瞩噜苏回因囡困囤囱围图固国图团图圃圆圈国园图围围圈团圆圈圆围园圆圈团囵国围团园圈圈围圆围团图围圈圆团土在地均坊坎坂坐坑块坚坛坜培基堂坚堆堡堪尧报场坞块塑塔冢塞填尘堑垫墒增墟墨堕坟垦壁坛壕壤壑士壮声壹壶寿处备夕外夙多夜够梦大天太夫央失头夷夸夹奄奇奈奉奋奎奏契奔奕奖套奥夺奋女奴奶奸她好如妃妄妆妇妈妊妍妒妓妖妙妻妥妹妻妾姊始姓委姗娘姊姚姨姻姜侄姬娉娃娜娟娠娥娩娱娶娲婚婆妇媒媚媛婷妈媲嫁嫉嫌袅嫔婴婶孀娘子字存孚孝季孤孟学孩孙孳孰孱孳学孺它宇守安宋完宏宗定宜官宙定宛宜宝实客宣室宥宦宫宰害宴家宵容宸寂寄寅密寇宿富寐寒寞察寡寝寤寥实宁寨审写宽寮宠宝寸寺封射将专寻对导小少尔尖尚尝尤就尸尺尼尾局屁居届屋屎屏屑展属屠履属屯山屹屾屿岁岁丰尽点笔画经国书";

// Direct character translation maps
const T2S_MAP = {
  "間": "间", "歲": "岁", "初": "初", "會": "会", "國": "国", "風": "风", "盡": "尽", "東": "东",
  "蘭": "兰", "亭": "亭", "詠": "咏", "經": "经", "書": "书", "畫": "画", "筆": "笔", "墨": "墨",
  "氣": "气", "暢": "畅", "載": "载", "寧": "宁", "靜": "静", "遠": "远", "為": "为", "選": "选",
  "賢": "贤", "與": "与", "講": "讲", "信": "信", "修": "修", "睦": "睦", "飛": "飞", "長": "长",
  "鶩": "鹜", "齊": "齐", "秋": "秋", "水": "水", "閣": "阁", "樂": "乐", "禮": "礼", "義": "义",
  "學": "学", "聖": "圣", "萬": "万", "興": "兴", "發": "发", "點": "点", "體": "体", "漢": "汉",
  "唐": "唐", "宋": "宋", "晉": "晋", "陰": "阴", "陽": "阳", "處": "处", "觀": "观", "廣": "广"
};

const S2T_MAP = {
  "间": "間", "岁": "歲", "初": "初", "会": "會", "国": "國", "风": "風", "尽": "盡", "东": "東",
  "兰": "蘭", "亭": "亭", "咏": "詠", "经": "經", "书": "書", "画": "畫", "笔": "筆", "墨": "墨",
  "气": "氣", "畅": "暢", "载": "載", "宁": "寧", "静": "靜", "远": "遠", "为": "為", "选": "選",
  "贤": "賢", "与": "與", "讲": "講", "信": "信", "修": "修", "睦": "睦", "飞": "飛", "长": "長",
  "鹜": "鶩", "齐": "齊", "秋": "秋", "水": "水", "阁": "閣", "乐": "樂", "礼": "禮", "义": "義",
  "学": "學", "圣": "聖", "万": "萬", "兴": "興", "发": "發", "点": "點", "体": "體", "汉": "漢",
  "唐": "唐", "宋": "宋", "晋": "晉", "阴": "陰", "阳": "陽", "处": "處", "观": "觀", "广": "廣"
};

function convertText(text, targetScript) {
  if (!text) return "";
  let result = "";
  if (targetScript === "trad") {
    for (const ch of text) {
      if (S2T_MAP[ch]) {
        result += S2T_MAP[ch];
      } else {
        const idx = SIMP_CHARS.indexOf(ch);
        result += (idx !== -1 && TRAD_CHARS[idx]) ? TRAD_CHARS[idx] : ch;
      }
    }
  } else {
    for (const ch of text) {
      if (T2S_MAP[ch]) {
        result += T2S_MAP[ch];
      } else {
        const idx = TRAD_CHARS.indexOf(ch);
        result += (idx !== -1 && SIMP_CHARS[idx]) ? SIMP_CHARS[idx] : ch;
      }
    }
  }
  return result;
}

let allFonts = [];
let activeFilters = {
  availability: "usable", // DEFAULT: Filter out ones that cannot be used and displayed!
  category: "all",
  char_support: "all",
  medium: "all",
  search: ""
};

let currentScript = "trad"; // "trad" or "simp"

// Register @font-face rules dynamically for all local fonts
function registerFontFaces() {
  let cssRules = "";
  for (const [id, info] of Object.entries(LOCAL_FONTS_MAP)) {
    cssRules += `
      @font-face {
        font-family: '${info.family}';
        src: url('${info.file}') format('truetype');
        font-display: swap;
      }
    `;
  }
  const styleEl = document.createElement("style");
  styleEl.textContent = cssRules;
  document.head.appendChild(styleEl);
}

// Fetch database json
async function loadFontDatabase() {
  try {
    const resp = await fetch("fonts.json");
    if (!resp.ok) throw new Error("Network response not ok");
    allFonts = await resp.json();
  } catch (err) {
    console.warn("Could not fetch fonts.json directly:", err);
  }
  initApp();
}

function initApp() {
  registerFontFaces();
  updateHeaderCounts();
  populateFontSelect();
  renderPresetButtons();
  setupEventListeners();
  renderGrid();

  // Set default initial font
  const defaultFontId = "hanwang-yan-kai";
  const fontSelect = document.getElementById("font-select");
  if (fontSelect) {
    fontSelect.value = defaultFontId;
    applySelectedFont(defaultFontId);
  }

  // Load initial preset text
  const initialPreset = PRESET_EXAMPLES[3]; // Lanting
  const textInput = document.getElementById("custom-text-input");
  const stageText = document.getElementById("calligraphy-text");
  const initialText = currentScript === "trad" ? initialPreset.trad : initialPreset.simp;
  textInput.value = initialText;
  stageText.textContent = initialText;
}

function updateHeaderCounts() {
  const kaiCnt = allFonts.filter(f => f.style_category === "kaishu").length;
  const liCnt = allFonts.filter(f => f.style_category === "lishu").length;
  const otherCnt = allFonts.filter(f => f.style_category === "other").length;
  const dlCnt = allFonts.filter(f => f.is_downloaded === 1).length;

  document.getElementById("stat-total").textContent = allFonts.length;
  document.getElementById("stat-kai").textContent = kaiCnt;
  document.getElementById("stat-li").textContent = liCnt;
  document.getElementById("stat-other").textContent = otherCnt;
  document.getElementById("stat-dl").textContent = dlCnt;

  document.getElementById("cnt-usable").textContent = dlCnt;
  document.getElementById("cnt-all").textContent = allFonts.length;
}

function populateFontSelect() {
  const select = document.getElementById("font-select");
  select.innerHTML = "";

  // Only populate downloaded/usable fonts in the studio selector
  const downloaded = allFonts.filter(f => f.is_downloaded === 1);
  downloaded.forEach(f => {
    const opt = document.createElement("option");
    opt.value = f.id;
    const tag = f.char_support === "trad" ? "繁" : (f.char_support === "simp" ? "简" : "繁简");
    opt.textContent = `[${tag}·${f.style_display}] ${f.name_zh} (${f.artist})`;
    select.appendChild(opt);
  });
}

function renderPresetButtons() {
  const container = document.getElementById("preset-buttons-container");
  container.innerHTML = "";

  PRESET_EXAMPLES.forEach(p => {
    const btn = document.createElement("button");
    btn.className = "preset-btn";
    const textToShow = currentScript === "trad" ? p.trad : p.simp;
    btn.textContent = p.name;
    btn.setAttribute("data-text", textToShow);
    btn.addEventListener("click", () => {
      const textInput = document.getElementById("custom-text-input");
      const stageText = document.getElementById("calligraphy-text");
      textInput.value = textToShow;
      stageText.textContent = textToShow;
    });
    container.appendChild(btn);
  });
}

function applySelectedFont(fontId) {
  const font = allFonts.find(f => f.id === fontId);
  const textStage = document.getElementById("calligraphy-text");
  const badgeEl = document.getElementById("active-font-badge");

  if (!font) return;

  const localInfo = LOCAL_FONTS_MAP[fontId];
  if (localInfo) {
    textStage.style.fontFamily = `'${localInfo.family}', var(--font-serif)`;
  } else {
    textStage.style.fontFamily = "var(--font-serif)";
  }

  // Check script preference advice
  let scriptHint = "";
  if (font.char_support === "trad") {
    scriptHint = `<span class="badge badge-trad">建议繁体</span>`;
  } else if (font.char_support === "simp") {
    scriptHint = `<span class="badge badge-simp">建议简体</span>`;
  } else {
    scriptHint = `<span class="badge badge-both">繁简兼备</span>`;
  }

  badgeEl.innerHTML = `
    <strong>当前使用字库：</strong>${font.name_zh} (${font.name_en}) ${scriptHint} · 
    <strong>书法风骨：</strong>${font.style_display} · 
    <strong>名家脉系：</strong>${font.artist} (${font.dynasty_era}) · 
    <strong>出处：</strong>${font.historical_reference || "传世真迹"} · 
    <strong>授权：</strong>${font.license}
  `;
}

function setupEventListeners() {
  const textInput = document.getElementById("custom-text-input");
  const stageText = document.getElementById("calligraphy-text");
  const fontSelect = document.getElementById("font-select");
  const sizeSlider = document.getElementById("font-size-slider");
  const sizeVal = document.getElementById("font-size-val");
  const btnVertical = document.getElementById("btn-vertical");
  const btnHorizontal = document.getElementById("btn-horizontal");
  const stage = document.getElementById("calligraphy-stage");

  // Traditional vs Simplified Toggle
  const btnTrad = document.getElementById("btn-trad");
  const btnSimp = document.getElementById("btn-simp");
  const btnConvertCurrent = document.getElementById("btn-convert-current");

  btnTrad.addEventListener("click", () => {
    if (currentScript === "trad") return;
    currentScript = "trad";
    btnTrad.classList.add("active");
    btnSimp.classList.remove("active");

    // Convert current textarea & stage text
    const converted = convertText(textInput.value, "trad");
    textInput.value = converted;
    stageText.textContent = converted;

    // Refresh preset buttons with Traditional labels & content
    renderPresetButtons();
  });

  btnSimp.addEventListener("click", () => {
    if (currentScript === "simp") return;
    currentScript = "simp";
    btnSimp.classList.add("active");
    btnTrad.classList.remove("active");

    // Convert current textarea & stage text
    const converted = convertText(textInput.value, "simp");
    textInput.value = converted;
    stageText.textContent = converted;

    // Refresh preset buttons with Simplified labels & content
    renderPresetButtons();
  });

  btnConvertCurrent.addEventListener("click", () => {
    const nextScript = currentScript === "trad" ? "simp" : "trad";
    if (nextScript === "trad") {
      btnTrad.click();
    } else {
      btnSimp.click();
    }
  });

  // Custom text input
  textInput.addEventListener("input", (e) => {
    stageText.textContent = e.target.value || "永";
  });

  // Font selection
  fontSelect.addEventListener("change", (e) => {
    applySelectedFont(e.target.value);
  });

  // Size slider
  sizeSlider.addEventListener("input", (e) => {
    const px = e.target.value + "px";
    sizeVal.textContent = px;
    stageText.style.fontSize = px;
  });

  // Layout direction
  btnVertical.addEventListener("click", () => {
    btnVertical.classList.add("active");
    btnHorizontal.classList.remove("active");
    stage.classList.remove("horizontal");
    stage.classList.add("vertical");
  });

  btnHorizontal.addEventListener("click", () => {
    btnHorizontal.classList.add("active");
    btnVertical.classList.remove("active");
    stage.classList.remove("vertical");
    stage.classList.add("horizontal");
  });

  // Paper theme controls
  document.querySelectorAll(".theme-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".theme-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const theme = btn.getAttribute("data-theme");
      document.body.className = theme;
    });
  });

  // Search input
  const searchInput = document.getElementById("search-input");
  searchInput.addEventListener("input", (e) => {
    activeFilters.search = e.target.value.trim().toLowerCase();
    renderGrid();
  });

  // Filter pills
  document.querySelectorAll(".filter-pill").forEach(pill => {
    pill.addEventListener("click", () => {
      const filterType = pill.getAttribute("data-filter");
      const val = pill.getAttribute("data-val");

      const parentGroup = pill.parentElement;
      parentGroup.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
      pill.classList.add("active");

      activeFilters[filterType] = val;
      renderGrid();
    });
  });
}

function renderGrid() {
  const grid = document.getElementById("font-grid");
  grid.innerHTML = "";

  const filtered = allFonts.filter(f => {
    // 1. Usability & Displayability filter:
    // If availability is "usable" (default), only show ones that CAN be used and displayed!
    if (activeFilters.availability === "usable" && f.is_downloaded !== 1) {
      return false;
    }

    // 2. Style Category filter
    if (activeFilters.category !== "all" && f.style_category !== activeFilters.category) {
      return false;
    }

    // 3. Character Support (Trad vs Simp) filter
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

    // 5. Text search filter
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
      <div style="grid-column: 1/-1; text-align: center; padding: 48px; color: #888;">
        未找到符合筛选条件的书法字库。您可点击“全部收录字库”查看历代名家法帖。
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
    let previewText = font.sample_text;
    if (font.char_support === "trad") {
      previewText = convertText(font.sample_text, "trad");
    } else if (font.char_support === "simp") {
      previewText = convertText(font.sample_text, "simp");
    } else {
      previewText = currentScript === "trad" ? convertText(font.sample_text, "trad") : convertText(font.sample_text, "simp");
    }

    // Badges
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
          ${isDl ? '<span class="badge badge-dl">✓ 可直接展示</span>' : '<span class="badge badge-unavailable">未下载</span>'}
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
          <span class="meta-value">${font.historical_reference || "历代名家书道精萃"}</span>
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
          <button class="card-btn btn-try" data-id="${font.id}">
            ✍️ 载入临摹台挥毫
          </button>
        ` : `
          <span class="card-btn" style="background:#f3f0e8; color:#999; cursor:not-allowed;">
            📜 典藏收录 (未下载不可试写)
          </span>
        `}
        <a href="${font.source_url}" target="_blank" rel="noopener noreferrer" class="card-btn btn-source">
          🔗 查阅源项目
        </a>
      </div>
    `;

    // Try in studio button
    const tryBtn = card.querySelector(".btn-try");
    if (tryBtn) {
      tryBtn.addEventListener("click", () => {
        const fontSelect = document.getElementById("font-select");
        fontSelect.value = font.id;
        applySelectedFont(font.id);

        // Auto-switch Trad/Simp according to font preference
        if (font.char_support === "trad" && currentScript !== "trad") {
          document.getElementById("btn-trad").click();
        } else if (font.char_support === "simp" && currentScript !== "simp") {
          document.getElementById("btn-simp").click();
        }

        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    grid.appendChild(card);
  });
}

// Start on DOM ready
document.addEventListener("DOMContentLoaded", loadFontDatabase);
