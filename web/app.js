/**
 * app.js - Calligraphy Font Studio Application
 */

// Downloaded font mappings to @font-face families
const LOCAL_FONTS_MAP = {
  "hanwang-yan-kai": { family: "HanWangYanKai", file: "fonts/HanWangYanKai.ttf" },
  "mashanzheng-kai": { family: "MaShanZheng", file: "fonts/MaShanZheng.ttf" },
  "hanwang-medium-kai": { family: "HanWangMediumKai", file: "fonts/HanWangMediumKai.ttf" },
  "hanwang-pen-kai": { family: "HanWangPenKai", file: "fonts/HanWangPenKai.ttf" },
  "lxgw-wenkai": { family: "LXGWWenKai", file: "fonts/LXGWWenKai-Regular.ttf" },
  "klee-one": { family: "KleeOne", file: "fonts/KleeOne.ttf" },
  "coqubeli-rubbing": { family: "CoQuBeLi", file: "fonts/CoQuBeLi.ttf" },
  "hanwang-lisu-medium": { family: "HanWangLiSuMedium", file: "fonts/HanWangLiSuMedium.ttf" },
  "hanwang-lisu-bold": { family: "HanWangLiSuBold", file: "fonts/HanWangLiSuBold.ttf" },
  "zhimang-xingshu": { family: "ZhiMangXing", file: "fonts/ZhiMangXing.ttf" },
  "liujian-maocao": { family: "LiuJianMaoCao", file: "fonts/LiuJianMaoCao.ttf" },
  "longcang-xingshu": { family: "LongCang", file: "fonts/LongCang.ttf" },
  "hanwang-xing-shu": { family: "HanWangXingShu", file: "fonts/HanWangXingShu.ttf" },
  "hanwang-wei-bei": { family: "HanWangWeiBei", file: "fonts/HanWangWeiBei.ttf" },
  "hanwang-pen-xing-kai": { family: "HanWangPenXingKai", file: "fonts/HanWangPenXingKai.ttf" },
  "yuji-boku": { family: "YujiBoku", file: "fonts/YujiBoku.ttf" },
  "arphic-ukai": { family: "ArphicUKai", file: "fonts/ArphicUKai.ttc" }
};

let allFonts = [];
let activeFilters = {
  category: "all",
  medium: "all",
  download: "all",
  search: ""
};

// Register @font-face rules dynamically
function registerFontFaces() {
  let cssRules = "";
  for (const [id, info] of Object.entries(LOCAL_FONTS_MAP)) {
    const ext = info.file.endsWith(".ttc") ? "truetype" : "truetype";
    cssRules += `
      @font-face {
        font-family: '${info.family}';
        src: url('${info.file}') format('${ext}');
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
    console.warn("Could not fetch fonts.json directly, falling back to embedded data or retry:", err);
  }
  initApp();
}

function initApp() {
  registerFontFaces();
  updateHeaderCounts();
  populateFontSelect();
  setupEventListeners();
  renderGrid();

  // Set default active font to MaShanZheng or HanWang Yan Kai
  const defaultFontId = "hanwang-yan-kai";
  const fontSelect = document.getElementById("font-select");
  if (fontSelect) {
    fontSelect.value = defaultFontId;
    applySelectedFont(defaultFontId);
  }
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

  document.getElementById("cnt-all").textContent = allFonts.length;
  document.getElementById("cnt-kai").textContent = kaiCnt;
  document.getElementById("cnt-li").textContent = liCnt;
  document.getElementById("cnt-other").textContent = otherCnt;
}

function populateFontSelect() {
  const select = document.getElementById("font-select");
  select.innerHTML = "";

  const downloaded = allFonts.filter(f => f.is_downloaded === 1);
  downloaded.forEach(f => {
    const opt = document.createElement("option");
    opt.value = f.id;
    opt.textContent = `[${f.style_display}] ${f.name_zh} (${f.artist})`;
    select.appendChild(opt);
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

  badgeEl.innerHTML = `
    <strong>当前使用字库：</strong>${font.name_zh} (${font.name_en}) · 
    <strong>书法风骨：</strong>${font.style_display} · 
    <strong>名家脉系：</strong>${font.artist} (${font.dynasty_era}) · 
    <strong>底蕴来源：</strong>${font.historical_reference || "名家传世墨迹"} · 
    <strong>授权协议：</strong>${font.license}
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

  // Preset buttons
  document.querySelectorAll(".preset-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const text = btn.getAttribute("data-text");
      textInput.value = text;
      stageText.textContent = text;
    });
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

      // Set active within same filter group
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
    // Category filter
    if (activeFilters.category !== "all" && f.style_category !== activeFilters.category) {
      return false;
    }
    // Medium filter
    if (activeFilters.medium !== "all" && f.medium !== activeFilters.medium) {
      return false;
    }
    // Download filter
    if (activeFilters.download === "1" && f.is_downloaded !== 1) {
      return false;
    }
    // Search filter
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
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 48px; color: #888;">未找到符合筛选条件的书法字库</div>`;
    return;
  }

  filtered.forEach(font => {
    const card = document.createElement("div");
    card.className = "font-card";

    const isDl = font.is_downloaded === 1;
    const local = LOCAL_FONTS_MAP[font.id];
    const previewFontFamily = (isDl && local) ? `'${local.family}', var(--font-serif)` : "var(--font-serif)";

    card.innerHTML = `
      <div class="card-header">
        <div class="card-title-group">
          <h3>${font.name_zh}</h3>
          <div class="pinyin-en">${font.name_en}</div>
        </div>
        <div class="badge-row">
          <span class="badge badge-style">${font.style_display}</span>
          <span class="badge ${font.medium === 'brush' ? 'badge-brush' : 'badge-pen'}">
            ${font.medium === 'brush' ? '毛笔' : '硬笔'}
          </span>
          ${isDl ? '<span class="badge badge-dl">可试写</span>' : ''}
        </div>
      </div>

      <div class="card-glyph-preview" style="font-family: ${previewFontFamily};">
        ${font.sample_text.substring(0, 5)}
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
          <span class="card-btn" style="background:#eee; color:#888; cursor:default;">
            📜 典藏字库收录
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
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    }

    grid.appendChild(card);
  });
}

// Start on DOM ready
document.addEventListener("DOMContentLoaded", loadFontDatabase);
