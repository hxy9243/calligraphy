/**
 * app.js - Calligraphy Studio & Font Database Interactive Application
 * Real-time font display on live calligraphy stage, full metadata browser,
 * instant Trad <-> Simp conversion via OpenCC engine, and video/still generation.
 */

// Font metadata for character compatibility; source font bytes stay on the server.
const LOCAL_FONTS_MAP = {
  // Built-in stroke writing & standard mappings
  "kai": { family: "MaShanZheng", charSupport: "both" },
  "yan": { family: "IYanKai", charSupport: "trad" },
  "aa shoujin": { family: "HanWangStandardKai", charSupport: "trad" },

  // Key Fonts & Kai Shu (楷書)
  "mashanzheng-kai": { family: "MaShanZheng", charSupport: "simp" },
  "mashanzheng": { family: "MaShanZheng", charSupport: "simp" },
  "i-yan-kai": { family: "IYanKai", charSupport: "trad" },
  "tw-kai": { family: "TWKai", charSupport: "trad" },
  "edukai": { family: "EduKai", charSupport: "trad" },
  "lxgw-wenkai-tc": { family: "LXGWWenKaiTC", charSupport: "trad" },
  "xiaolai-kai": { family: "Xiaolai", charSupport: "trad" },

  // Kai Shu (楷書)
  "hanwang-yan-kai": { family: "HanWangYanKai", charSupport: "trad" },
  "hanwang-medium-kai": { family: "HanWangMediumKai", charSupport: "trad" },
  "arphic-ukai": { family: "ArphicUKai", charSupport: "both" },
  "lxgw-wenkai": { family: "LXGWWenKai", charSupport: "both" },
  "chill-qiuhong-kai": { family: "QiuHongKai", charSupport: "simp" },
  "cwtex-q-kai": { family: "cwTeXQKai", charSupport: "trad" },
  "yanshu-chunfeng-kai": { family: "ChunFengKai", charSupport: "simp" },
  "yanshu-youran-xiaokai": { family: "YouRanXiaoKai", charSupport: "simp" },
  "maoken-yingbi-kai": { family: "MaokenYingBiKai", charSupport: "simp" },
  "icrane-pen-kai": { family: "ICranePenKai", charSupport: "trad" },
  "lxgw-zhenkai": { family: "LXGWZhenKai", charSupport: "simp" },
  "yozai-kai": { family: "YozaiKai", charSupport: "simp" },
  "chill-longcang-kai": { family: "ChillLongCangKai", charSupport: "simp" },
  "chill-longcang-kai-bold": { family: "ChillLongCangKaiBold", charSupport: "simp" },
  "lxgw-wenkai-bold": { family: "LXGWWenKaiBold", charSupport: "both" },
  "lxgw-wenkai-mono": { family: "LXGWWenKaiMono", charSupport: "both" },
  "hanwang-standard-kai": { family: "HanWangStandardKai", charSupport: "trad" },
  "hanwang-simplified-kai": { family: "HanWangSimplifiedKai", charSupport: "simp" },
  "hanwang-phonetic-kai": { family: "HanWangPhoneticKai", charSupport: "trad" },
  "hanwang-hollow-kai": { family: "HanWangHollowKai", charSupport: "trad" },
  "shutifang-liugongquan-kai": { family: "ShuTiFangLiuGongQuanKai", charSupport: "both" },

  // Li Shu (隸書)
  "hanwang-lisu-medium": { family: "HanWangLiSuMedium", charSupport: "trad" },
  "lishu hanwang": { family: "HanWangLiSuMedium", charSupport: "trad" },
  "hanwang-lisu-bold": { family: "HanWangLiSuBold", charSupport: "trad" },

  // Other Styles (行書/草書/魏碑)
  "zhimang-xingshu": { family: "ZhiMangXing", charSupport: "simp" },
  "longcang-xingshu": { family: "LongCang", charSupport: "simp" },
  "longcang": { family: "LongCang", charSupport: "simp" },
  "hanwang-xing-shu": { family: "HanWangXingShu", charSupport: "trad" },
  "hanwang-wei-bei": { family: "HanWangWeiBei", charSupport: "trad" },
  "hanwang-pen-xing-kai": { family: "HanWangPenXingKai", charSupport: "trad" },

  // Song Ti & Woodblock (宋體 / 雕版刻本)
  "tw-sung": { family: "TWSung", charSupport: "trad" },
  "genryu-min": { family: "GenRyuMin", charSupport: "trad" },
  "genwan-min": { family: "GenWanMin", charSupport: "trad" },

  // Fang Song (仿宋體)
  "cwtex-fangsong": { family: "cwTeXFangSong", charSupport: "trad" },

  // Running, ShinSu & Monumental Styles (行書 / 新書體 / 榜書匾額)
  "hanwang-shinsu": { family: "HanWangShinSuMedium", charSupport: "trad" },

  // Artist Fonts & New Traditional Wordset Additions (名家新收錄字庫)
  "bakudai-kai": { family: "Bakudai", charSupport: "trad" },
  "masafont-xing": { family: "MasaFont", charSupport: "trad" },
  "qiji-woodblock-kai": { family: "QijiWoodblock", charSupport: "trad" },
  "qiji-combo": { family: "QijiWoodblock", charSupport: "trad" },
  "iansui-kai": { family: "Iansui", charSupport: "trad" },
  "yuji-boku": { family: "YujiBoku", charSupport: "trad" },
  "yuji-mai": { family: "YujiMai", charSupport: "trad" },
  "yuji-syuku": { family: "YujiSyuku", charSupport: "trad" },
  "klee-one": { family: "KleeOne", charSupport: "both" },
  "klee-one-semibold": { family: "KleeOneSemiBold", charSupport: "both" },
  "cwtex-q-ming": { family: "cwTeXQMing", charSupport: "trad" },
  "cwtex-q-yuan": { family: "cwTeXQYuan", charSupport: "trad" },
  "jason-handwriting1": { family: "JasonHandwriting1", charSupport: "trad" },
  "jason-handwriting2": { family: "JasonHandwriting2", charSupport: "trad" },
  "jason-handwriting3": { family: "JasonHandwriting3", charSupport: "trad" },
  "jason-handwriting4": { family: "JasonHandwriting4", charSupport: "trad" },
  "hanwang-kantan": { family: "HanWangKanTan", charSupport: "trad" }
};

// Preset classical calligraphy examples (no punctuation, returns for line breaks, 10+ Tang poems added)
const PRESET_EXAMPLES = [
  { id: "wangwei", name: "王维联句", nameTrad: "王維聯句", trad: "明月松間照\n清泉石上流", simp: "明月松间照\n清泉石上流" },
  { id: "chunxiao", name: "春晓 (孟浩然)", nameTrad: "春曉 (孟浩然)", trad: "春眠不覺曉\n處處聞啼鳥\n夜來風雨聲\n花落知多少", simp: "春眠不觉晓\n处处闻啼鸟\n夜来风雨声\n花落知多少" },
  { id: "jingye", name: "静夜思 (李白)", nameTrad: "靜夜思 (李白)", trad: "床前明月光\n疑是地上霜\n舉頭望明月\n低頭思故鄉", simp: "床前明月光\n疑是地上霜\n举头望明月\n低头思故乡" },
  { id: "guanque", name: "登鹳雀楼 (王之涣)", nameTrad: "登鸛雀樓 (王之渙)", trad: "白日依山盡\n黃河入海流\n欲窮千里目\n更上一層樓", simp: "白日依山尽\n黄河入海流\n欲穷千里目\n更上一层楼" },
  { id: "jiangxue", name: "江雪 (柳宗元)", nameTrad: "江雪 (柳宗元)", trad: "千山鳥飛絕\n萬徑人蹤滅\n孤舟蓑笠翁\n獨釣寒江雪", simp: "千山鸟飞绝\n万径人踪灭\n孤舟蓑笠翁\n独钓寒江雪" },
  { id: "xiangsi", name: "相思 (王维)", nameTrad: "相思 (王維)", trad: "紅豆生南國\n春來發幾枝\n願君多采擷\n此物最相思", simp: "红豆生南国\n春来发几枝\n愿君多采撷\n此物最相思" },
  { id: "luchai", name: "鹿柴 (王维)", nameTrad: "鹿柴 (王維)", trad: "空山不見人\n但聞人語響\n返景入深林\n復照青苔上", simp: "空山不见人\n但闻人语响\n返景入深林\n复照青苔上" },
  { id: "lushan", name: "望庐山瀑布 (李白)", nameTrad: "望廬山瀑布 (李白)", trad: "日照香爐生紫煙\n遙看瀑布掛前川\n飛流直下三千尺\n疑是銀河落九天", simp: "日照香炉生紫烟\n遥看瀑布挂前川\n飞流直下三千尺\n疑是银河落九天" },
  { id: "baidi", name: "早发白帝城 (李白)", nameTrad: "早發白帝城 (李白)", trad: "朝辭白帝彩雲間\n千里江陵一日還\n兩岸猿聲啼不住\n輕舟已過萬重山", simp: "朝辞白帝彩云间\n千里江陵一日还\n两岸猿声啼不住\n轻舟已过万重山" },
  { id: "fengqiao", name: "枫桥夜泊 (张继)", nameTrad: "楓橋夜泊 (張繼)", trad: "月落烏啼霜滿天\n江楓漁火對愁眠\n姑蘇城外寒山寺\n夜半鐘聲到客船", simp: "月落乌啼霜满天\n江枫渔火对愁眠\n姑苏城外寒山寺\n夜半钟声到客船" },
  { id: "liangzhou", name: "凉州词 (王翰)", nameTrad: "涼州詞 (王翰)", trad: "葡萄美酒夜光杯\n欲飲琵琶馬上催\n醉臥沙場君莫笑\n古來征戰幾人回", simp: "葡萄美酒夜光杯\n欲饮琵琶马上催\n醉卧沙场君莫笑\n古来征战几人回" },
  { id: "guyuan", name: "赋得古原草送别 (白居易)", nameTrad: "賦得古原草送別 (白居易)", trad: "離離原上草\n一歲一枯榮\n野火燒不盡\n春風吹又生", simp: "离离原上草\n一岁一枯荣\n野火烧不尽\n春风吹又生" },
  { id: "songdu", name: "送杜少府之任蜀州 (王勃)", nameTrad: "送杜少府之任蜀州 (王勃)", trad: "城闕輔三秦\n風煙望五津\n與君離別意\n同是宦遊人\n海內存知己\n天涯若比鄰\n無為在岐路\n兒女共霑巾", simp: "城阙辅三秦\n风烟望五津\n与君离别意\n同是宦游人\n海内存知己\n天涯若比邻\n无为在歧路\n儿女共沾巾" },
  { id: "river", name: "春江花月夜", nameTrad: "春江花月夜", trad: "春江花月夜", simp: "春江花月夜" },
  { id: "lanting", name: "兰亭集序", nameTrad: "蘭亭集序", trad: "永和九年\n歲在癸丑\n暮春之初\n會於會稽山陰之蘭亭\n修禊事也", simp: "永和九年\n岁在癸丑\n暮春之初\n会于会稽山阴之兰亭\n修禊事也" },
  { id: "redcliff", name: "赤壁怀古", nameTrad: "赤壁懷古", trad: "大江東去\n浪淘盡\n千古風流人物\n故壘西邊\n人道是\n三國周郎赤壁", simp: "大江东去\n浪淘尽\n千古风流人物\n故垒西边\n人道是\n三国周郎赤壁" },
  { id: "houde", name: "厚德自强", nameTrad: "厚德自強", trad: "厚德載物\n自強不息", simp: "厚德载物\n自强不息" }
];

/// Fallback character dictionary for client-side offline conversion
const TRAD_FALLBACK = "萬與醜專業叢東絲丟兩嚴喪個豐臨為麗舉麼義樂喬習鄉書買亂爭於虧雲亞產畝親倫倉儀們價眾優偉傳傷儉僕兒元兄充兆先光克免黨全八公六共興兵其具典冊再冒冕冠冬冰冶冷凍凝幾凡鳳凶出函刀刃分切刊刑列初判券刷刺刮制刹刻剃削前剔剖剛割創剷劇劈劉劍劑力功加劣動助勇勉勒勤勘勝勞勢募勳勵勸勻勾包匈化北匙匹區十千午半華卑協卒卓單賣南博占卡盧印即危卵卷卸卻卿歷厥厲壓厭去參又叉反發叔取受叛台弁友雙變敘口古句叫可史右司吃各合吉同名后吏向君吝吞吟吳告吹味呼命咆和咎咐咒呱咕咀咄咸咱咳哆哈哉哥員哦咧哪哼哭哮哲哽唆唇哺唉唐唔唑啼唯唱唾唸啃唬商啊問啟啡啜啞啄喋喧喃喊喙喚喝喘啾喜嗅喳嗆嗚嗜嗟嗡嗣嗤嗷嚎嗦嗝嗔嗖嗑嘎嘔嗽嘶嘈嘲嘹嘻嘮嘰噓嘩嘯嘴囑嚕囌回因囡困囤囪圍圖固國團圃圓圏園圇土在地均坊坎坂坐坑塊堅壇壢培基堂堆堡堪堯報場塢塑塔塚塞填塵塹墊墒增墟墨墮墳墾壁壕壤壑士壯聲壹壺壽處備夕外夙多夜夠夢大天太夫央失頭夷夸夾奄奇奈奉奮奎奏契奔奕獎套奧奪女奴奶奸她好如妃妄妝婦媽妊妍妒妓妖妙妻妥妹妾姊始姓委姍孃姚姨姻姜姪姬娉娃娜娟娠娥娩娛娶媧婚婆媒媚媛婷媲嫁嫉嫌嫋嬪嬰嬸孀子字存孚孝季孤孟學孩孫孳孰孱孺它宇守安宋完宏宗定宜官宙宛寶實客宣室宥宦宮宰害宴家宵容宸寂寄寅密寇宿富寐寒寞察寡寢寤寥寧寨審寫寬寮寵寸寺封射將尋對導小少爾尖尚嘗尤就屍尺尼尾局屁居屆屋屎屏屑展屬屠履屯山屹屾嶼歲盡點筆畫經曉歸鳥詩語見難歡獨幽琴深林知覺聞來隨無時過門開馬鍾顏錄鑑賞紙灑車貝計邊龍選擇齊『』「」傌㑶偑㑳倲㑯儸劏劃劚噚喎㘚㜄媰㜏孋㠏嵾幓懧㥮憍懤慺掆㩳撝擥擓擽㩜棡椲樢樫殰殨瀇濧灡澾濄瀰潚鸂燶煱獱璯䁻瞜碽磾稏穇筴籔䊷紬縳絅䋙䋚綐綵䋻䋹繿繸䍦䎱膞薵薳藭罃螮䙡襬譼訢鿁䜀讌貙䝼賰躎釾鏺䥱䥇鐯鐥钁䦛䦟靦騧䯀䱽鮣鰆鰌鰧䱷鿐鳾鵁鴷鶄鶪鷉鸊龑烏亙褻嚲億僅從侖夥會傴傘俥俔倀傖僞佇體餘傭僉俠侶僥偵側僑儈儕儂儘俁儔儼倆儷倈債傾傯僂僨償儎儻儐儲儺兌兗蘭關茲養獸囅內岡軍農馮衝決況淨悽準涼減湊凜鳧憑凱擊鑿芻劃則刪別剗剄劊㓨劌剴剮剝辦務勱勁勩匭匱醫滷臥衛巹廠廳厙龎廁釐廂厴廈廚廄廝縣叄靉靆疊葉號嘆籲嚇呂嗎唚噸聽吶嘸囈嚦唄咼詠嚨嚀噝吒諮響噠嘵嗶噦噲嚌噥喲嘜嗊啢嗩嘖嗇囀齧嘓囉嘽餵噴嘍嚳囁噯嚶囑囂聖壙壞壩墜壟壠壚壘堊埡墶壋塏堖塒壎堝壪牆殼壼復奩奐嫵嫗嬀奼婁婭嬈嬌孌嫺嫿嬋媼嬃嬡嬙嬤孿憲賓尷層屓屜屢屨豈嶇崗峴嵐島巖嶺嶽崬巋嶨嶧峽嶢嶠崢巒峯嶗崍嶮嶄嶸嶔嶁巔鞏巰幣帥師幃帳簾幟帶幀幫幬幘幗冪幹並廣莊慶牀廬廡庫應廟龐廢廎廩異棄弒張彌弳彎彈強當彠彥彲徹徵徑徠憶懺憂愾懷態慫憮慪悵愴憐總懟懌戀恆懇惡慟懨愷惻惱惲悅愨懸慳悞憫驚懼慘懲憊愜慚憚慣慍憤憒願懾憖懣懶懍戇戔戲戧戰戩戱戶撲託執擴捫掃揚擾撫拋摶摳掄搶護擔擬攏揀擁攔擰撥掛摯攣掗撾撻挾撓擋撟掙擠揮撏挩撈損撿換搗據擄摑擲撣摻摜攬搵撳攙擱摟揯攪攜攝攄擺搖擯攤攖撐攆擷擼攛㩵擻攢敵敓斂斆數齋斕鬥斬斷舊曠暘曇暱晝曨顯晉曬曄暈暉暫曖術樸機殺雜權槓條楊榪傑極構樅樞棗櫪梘棖槍楓梟櫃檸檉梔柵標棧櫛櫳棟櫨櫟欄樹棲慄樣欒椏橈楨檔榿橋樺檜槳樁樳檮棶槤檢梲欞槨槼櫝槧槶欏樿橢槮樓欖榲櫬櫚櫸樧檟檻檳櫧橫檣櫻櫫櫥櫓櫞檁歟歐殲歿殤殘殞殮殫殯毆毀轂畢斃氈毿氌氣氫氬氳匯漢湯洶溝沒灃漚瀝淪滄渢潙滬濘淚澩瀧瀘濼瀉潑澤涇潔窪浹淺漿澆湞溮濁測澮濟瀏滻渾滸濃潯濜塗湧涗濤澇淶漣潿渦溳渙滌潤澗漲澀澱淵淥漬瀆漸澠漁瀋滲溫遊灣溼濚潰濺漵漊潷滾滯灩灄滿瀅濾濫灤濱灘澦灠瀠瀟瀲濰潛瀦瀂瀾瀨瀕灝滅燈靈竈災燦煬爐燉煒熗煉熾爍爛烴燭煙煩燒燁燴燙燼熱煥燜燾熅燻愛爺牘犛牽犧犢狀獷獁猶狽獮獰狹獅獪猙獄猻獫獵獼玀豬貓蝟獻獺璣璵瑒瑪瑋環現瑲璽琺瓏璫琿璡璉瑣瓊瑤璦璸瓔瓚甕甌電暢疇癤療瘧癘瘍癧瘲瘡瘋皰痾癰痙癢瘂癆瘓癇痲癡癉瘮瘞瘻癟癱癮癭癩癬癲皁皚皺皸盞鹽監蓋盜盤瞘眥矓睜睞瞼瞶瞞矯磯礬礦碭碼磚硨硯碸礪礱礫礎硜碩硤磽磑礄確磠礆礙磧磣鹼禮禡禕禰禎禱禍稟祿禪離禿稈種祕積稱穢穠穭稅穌穩穡穭窮竊竅窵窯竄窩窺竇窶豎競篤筍筧箋籠籩築篳篩簹箏籌篔籤篠簡籙簀篋籜籮簞簫簣簍籃籛籬籪籟糴類秈糶糲粵糞糧糉糝餱餈緊縶縕緪糹糾紆紅紂纖紇約級紈纊紀紉緯紜紘純紕紗綱納紝縱綸紛紋紡紵紖紐紓線紺紲紱練組紳細織終縐絆紼絀紹繹紿綁絨結絝繞絰絎繪給絢絳絡絕絞統綆綃絹繡綌綏絛繼綈績緒綾緓續綺緋綽鞝緄繩維綿綬繃綢綯綹綣綜綻綰綠綴緇緙緗緘緬纜緹緲緝縕繢緦綞緞緶線緱縋緩締縷編緡緣縉縛縟縝縫縗縞纏縭縊縑繽縹縵縲纓縮繆繅纈繚繕繒繮繾繰繯繳纘罌網羅罰罷羆羈羥羨羣翹翽翬耮耬聳恥聶聾職聹聯聵聰肅腸膚骯餚腎腫脹脅膽朧腖臚脛膠脈膾髒臍腦膿臠腳脫腡臉臘醃膕齶膩靦膃騰臏羶臢輿艤艦艙艫艱豔藝節羋薌蕪蘆蓯葦藶莧萇蒼薴薴蘋範莖蘢蔦塋煢繭荊薦薘莢蕘蓽萴蕎薈薺蕩榮葷滎犖熒蕁藎蓀蔭蕒葒葤藥蒞萊蓮蒔萵薟獲蕕瑩鶯蓴蘀蘿螢營縈蕭薩蔥蒕蕆蕢蔣蔞醟藍薊蘺蕷鎣驀虆薔蘞藺藹薀蘄蘊藪蘚蘊櫱虜慮虛蟲虯蟣蝨雖蝦蠆蝕蟻螞蠁蠶蠔蜆蠱蠣蟶蠻蟄蛺蟯螄蠐蛻蝸蠟蠅蟈蟬蠍螻蠑螿蟎蠨釁銜補襯袞襖褘襪襲襏裝襠褌褳襝褲襉褸襤襴觀覎規覓視覘覽覬覡覿覥覦覯覲覷觴觸觶誾讋譽謄訁訂訃認譏訐訌討讓訕訖託訓議訊記訒講諱謳詎訝訥許訛論訩訟諷設訪訣證詁訶評詛識詗詐訴診詆謅詞詘詔詖譯詒誆誄試詿詰詼誠誅詵話誕詬詮詭詢詣諍該詳詫諢詡譸誡誣誚誤誥誘誨誑說誦誒請諸諏諾讀諑誹課諉諛誰諗調諂諒諄誶談讅誼謀諶諜謊諫諧謔謁謂諤諭諼讒諮諳諺諦謎諞諝謨讜謖謝謠謗諡謙謐謹謾謫譾謬譚譖譙讕譜譎讞譴譫讖豶貞負貟貢財責賢敗賬貨質販貪貧貶購貯貫貳賤賁貰貼貴貺貸貿費賀貽賊贄賈賄貲賃賂贓資賅贐賕賑賚賒賦賭齎贖賜贔賙賡賠賧賴賵贅賻賺賽賾贗贊贇贈贍贏贛赬趙趕趨趲躉躍蹌蹠躒踐躂蹺蹕躚躋踴躊蹤躓躑躡蹣躕躥躪躦軀轀軋軌軒軑軔轉軛輪軟轟軲軻轤軸軹軼軤軫轢軺輕軾載輊轎輈輇輅較輒輔輛輦輩輝輥輞輬輟輜輳輻輯轀輸轡轅轄輾轆轍轔辭闢辯辮遼達遷邁運還這進遠違連遲邇逕跡適遜遞邐邏遺遙鄧鄺鄔郵鄒鄴鄰鬱郟鄶鄭鄆酈鄖鄲酇醞醱醬釅釃釀醞採釋里鑾鏨釒釓釔針釘釗釙釕釷釺釧釤鈒釩釣鍆釹鍚釵鈃鈣鈈鈦鉅鈍鈔鈉鋇鋼鈑鈐鑰欽鈞鎢鉤鈧鈁鈥鈄鈕鈀鈺錢鉦鉗鈷鉢鈳鉕鈽鈸鉞鑽鉬鉭鉀鈿鈾鐵鉑鈴鑠鉛鉚鉋鈰鉉鉈鉍鈮鈹鐸鉶銬銠鉺鋩錏銪鋮鋏鋣鐃銍鐺銅鋁銱銦鎧鍘銖銑鋌銩銛鏵銓鎩鉿銚鉻銘錚銫鉸銥銃鐋銨銀銣鑄鐒鋪鋙錸鋱鏈鏗銷鎖鋰鋥鋤鍋鋯鋨鏽銼鋝鋒鋅鋶鐦鐧銳銻鋃鋟鋦錒錆鍺鍩錯錨錛錡鍀錁錕錩錫錮鑼錘錐錦鑕鍁錈鍃錇錟錠鍵鋸錳錙鍥鍈鍇鏘鍶鍔鍤鍬鍾鍛鎪鍠鍰鎄鍍鎂鏤鎡鐨鎇鏌鎮鎛鎘鑷钂鐫鎳鎿鎦鎬鎊鎰鎵鑌鎔鏢鏜鏝鏍鏰鏞鏡鏑鏃鏇鏐鐔钁鐐鏷鑥鐓鑭鐠鑹鏹鐙鑊鐳鐶鐲鐮鐿鑔鑣鑞鑱鑲長閂閃閆閈閉闖閏闈閒閎間閔閌悶閘鬧閨闥閩閭闓閥閣閡閫鬮閱閬闍閾閹閶鬩閿閽閻閼闡闌闃闠闊闋闔闐闒闕闞闤隊陽陰陣階際陸隴陳陘陝隯隉隕險隱隸雋僱雛讎靂霧霽黴霢靄靚靝靜靨韃鞽韉韝韋韌韍韓韙韞韜韻頁頂頃頇項順須頊頑顧頓頎頒頌頏預顱領頗頸頡頰頲頜潁熲頦頤頻頮頹頷頴穎顆題顒顎顓額顳顢顛顙顥纇顫顬顰顴風颺颭颮颯颶颸颼颻飀飄飆飈飛饗饜飠飣飢飥餳飩餼飪飫飭飯飲餞飾飽飼飿飴餌饒餉餄餎餃餏餅餑餖餓餘餒餕餜餛餡館餷饋餶餿饞饁饃餺餾饈饉饅饊饌饢馭馱馴馳驅馹駁驢駔駛駟駙駒騶駐駝駑駕驛駘驍罵駰驕驊駱駭駢驫驪騁驗騂駸駿騏騎騍騅騌驌驂騙騭騤騷騖驁騮騫騸驃騾驄驏驟驥驦驤髏髖髕鬢鬹魘魎魚魛魢魷魨魯魴䰾魺鮁鮃鮎鱸鮋鮓鮒鮊鮑鱟鮍鮐鮭鮚鮳鮪鮞鮦鰂鮜鱠鱭鮫鮮鮺鯗鱘鯁鱺鰱鰹鯉鰣鰷鯀鯊鯇鮶鯽鯒鯖鯪鯕鯫鯡鯤鯧鯝鯢鯰鯛鯨鰺鯴鯔鱝鰈鰏鱨鯷鰮鰃鰓鱷鰍鰒鰉鰁鱂鯿鰠鰲鰭鰨鰥鰩鰟鰜鰳鰾鱈鱉鰻鰵鱅䲁鰼鱖鱔鱗鱒鱯鱤鱧鱣䲘鳩雞鳶鳴鳲鷗鴉鶬鴇鴆鴣鶇鸕鴨鴞鴦鴒鴟鴝鴛鷽鴕鷥鷙鴯鴰鵂鴴鵃鴿鸞鴻鵐鵓鸝鵑鵠鵝鵒鷳鵜鵡鵲鶓鵪鵾鵯鵬鵮鶉鶊鵷鷫鶘鶡鶚鶻鶖鷀鶥鶩鷊鷂鶲鶹鶺鷁鶼鶴鷖鸚鷓鷚鷯鷦鷲鷸鷺䴉鸇鷹鸌鸏鸛鸘鹺麥麩麴麪麼黃黌黶黷黲黽黿鼂鼉鞀鼴齏齒齔齕齗齟齡齙齠齜齦齬齪齲齷龔龕䃮䥑鿓鎶鉨裏裡";
const SIMP_FALLBACK = "万与丑专业丛东丝丢两严丧个丰临为丽举么义乐乔习乡书买乱争于亏云亚产亩亲伦仓仪们价众优伟传伤俭仆儿元兄充兆先光克免党全八公六共兴兵其具典册再冒冕冠冬冰冶冷冻凝几凡凤凶出函刀刃分切刊刑列初判券刷刺刮制刹刻剃削前剔剖刚割创铲剧劈刘剑剂力功加劣动助勇勉勒勤勘胜劳势募勋励劝匀勾包匈化北匙匹区十千午半华卑协卒卓单卖南博占卡卢印即危卵卷卸却卿历厥厉压厌去参又叉反发叔取受叛台弁友双变叙口古句叫可史右司吃各合吉同名后吏向君吝吞吟吴告吹味呼命咆和咎咐咒呱咕咀咄咸咱咳哆哈哉哥员哦咧哪哼哭哮哲哽唆唇哺唉唐唔唑啼唯唱唾念啃唬商啊问启啡啜哑啄喋喧喃喊喙唤喝喘啾喜嗅喳呛呜嗜嗟嗡嗣嗤嗷嚎嗦嗝嗔嗖嗑嘎呕嗽嘶嘈嘲嘹嘻唠叽嘘哗啸嘴瞩噜苏回因囡困囤囱围图固国团圃圆圈园囵土在地均坊坎坂坐坑块坚坛坜培基堂堆堡堪尧报场坞塑塔冢塞填尘堑垫墒增墟墨堕坟垦壁壕壤壑士壮声壹壶寿处备夕外夙多夜够梦大天太夫央失头夷夸夹奄奇奈奉奋奎奏契奔奕奖套奥夺女奴奶奸她好如妃妄妆妇妈妊妍妒妓妖妙妻妥妹妾姊始姓委姗娘姚姨姻姜侄姬娉娃娜娟娠娥娩娱娶娲婚婆媒媚媛婷媲嫁嫉嫌袅嫔婴婶孀子字存孚孝季孤孟学孩孙孳孰孱孺它宇守安宋完宏宗定宜官宙宛宝实客宣室宥宦宫宰害宴家宵容宸寂寄寅密寇宿富寐寒寞察寡寝寤寥宁寨审写宽寮宠寸寺封射将寻对导小少尔尖尚尝尤就尸尺尼尾局屁居届屋屎屏屑展属屠履屯山屹屾屿岁尽点笔画经晓归鸟诗语见难欢独幽琴深林知觉闻来随无时过门开马钟颜录鉴赏纸洒车贝计边龙选择齐‘’“”㐷㐹㐽㑇㑈㑔㑩㓥㓰㔉㖊㖞㘎㚯㛀㛣㛤㟆㟥㡎㤖㤘㤭㤽㥪㧏㧐㧑㧛㧟㧰㨫㭎㭏㭤㭴㱩㱮㲿㳔㳕㳠㳡㳽㴋㶉㶶㶽㺍㻅䀥䁖䂵䃅䅉䅟䇲䉤䌶䌷䌸䌹䌺䌻䌼䌽䌾䌿䍀䍁䍠䎬䏝䓓䓕䓖䓨䗖䙌䙓䛓䜣䜤䜧䜩䝙䞍䞐䟢䥺䥽䥾䦂䦃䦅䦆䦶䦷䩄䯄䯅䲝䲟䲠䲡䲢䲣䲤䴓䴔䴕䴖䴗䴘䴙䶮乌亘亵亸亿仅从仑伙会伛伞伡伣伥伧伪伫体余佣佥侠侣侥侦侧侨侩侪侬侭俣俦俨俩俪俫债倾偬偻偾偿傤傥傧储傩兑兖兰关兹养兽冁内冈军农冯冲决况净凄准凉减凑凛凫凭凯击凿刍划则删别刬刭刽刾刿剀剐剥办务劢劲勚匦匮医卤卧卫卺厂厅厍厐厕厘厢厣厦厨厩厮县叁叆叇叠叶号叹吁吓吕吗吣吨听呐呒呓呖呗呙咏咙咛咝咤咨响哒哓哔哕哙哜哝哟唛唝唡唢啧啬啭啮啯啰啴喂喷喽喾嗫嗳嘤嘱嚣圣圹坏坝坠垄垅垆垒垩垭垯垱垲垴埘埙埚塆墙壳壸复奁奂妩妪妫姹娄娅娆娇娈娴婳婵媪媭嫒嫱嬷孪宪宾尴层屃屉屡屦岂岖岗岘岚岛岩岭岳岽岿峃峄峡峣峤峥峦峰崂崃崄崭嵘嵚嵝巅巩巯币帅师帏帐帘帜带帧帮帱帻帼幂干并广庄庆床庐庑库应庙庞废庼廪异弃弑张弥弪弯弹强当彟彦彨彻征径徕忆忏忧忾怀态怂怃怄怅怆怜总怼怿恋恒恳恶恸恹恺恻恼恽悦悫悬悭悮悯惊惧惨惩惫惬惭惮惯愠愤愦愿慑慭懑懒懔戆戋戏戗战戬戯户扑托执扩扪扫扬扰抚抛抟抠抡抢护担拟拢拣拥拦拧拨挂挚挛挜挝挞挟挠挡挢挣挤挥挦捝捞损捡换捣据掳掴掷掸掺掼揽揾揿搀搁搂搄搅携摄摅摆摇摈摊撄撑撵撷撸撺擜擞攒敌敚敛敩数斋斓斗斩断旧旷旸昙昵昼昽显晋晒晔晕晖暂暧术朴机杀杂权杠条杨杩杰极构枞枢枣枥枧枨枪枫枭柜柠柽栀栅标栈栉栊栋栌栎栏树栖栗样栾桠桡桢档桤桥桦桧桨桩桪梼梾梿检棁棂椁椝椟椠椢椤椫椭椮楼榄榅榇榈榉榝槚槛槟槠横樯樱橥橱橹橼檩欤欧歼殁殇残殒殓殚殡殴毁毂毕毙毡毵氇气氢氩氲汇汉汤汹沟没沣沤沥沦沧沨沩沪泞泪泶泷泸泺泻泼泽泾洁洼浃浅浆浇浈浉浊测浍济浏浐浑浒浓浔浕涂涌涚涛涝涞涟涠涡涢涣涤润涧涨涩淀渊渌渍渎渐渑渔渖渗温游湾湿溁溃溅溆溇滗滚滞滟滠满滢滤滥滦滨滩滪漤潆潇潋潍潜潴澛澜濑濒灏灭灯灵灶灾灿炀炉炖炜炝炼炽烁烂烃烛烟烦烧烨烩烫烬热焕焖焘煴熏爱爷牍牦牵牺犊状犷犸犹狈狝狞狭狮狯狰狱狲猃猎猕猡猪猫猬献獭玑玙玚玛玮环现玱玺珐珑珰珲琎琏琐琼瑶瑷瑸璎瓒瓮瓯电畅畴疖疗疟疠疡疬疭疮疯疱疴痈痉痒痖痨痪痫痳痴瘅瘆瘗瘘瘪瘫瘾瘿癞癣癫皂皑皱皲盏盐监盖盗盘眍眦眬睁睐睑瞆瞒矫矶矾矿砀码砖砗砚砜砺砻砾础硁硕硖硗硙硚确硵硷碍碛碜碱礼祃祎祢祯祷祸禀禄禅离秃秆种秘积称秽秾稆税稣稳穑穞穷窃窍窎窑窜窝窥窦窭竖竞笃笋笕笺笼笾筑筚筛筜筝筹筼签筿简箓箦箧箨箩箪箫篑篓篮篯篱簖籁籴类籼粜粝粤粪粮粽糁糇糍紧絷緼縆纟纠纡红纣纤纥约级纨纩纪纫纬纭纮纯纰纱纲纳纴纵纶纷纹纺纻纼纽纾线绀绁绂练组绅细织终绉绊绋绌绍绎绐绑绒结绔绕绖绗绘给绚绛络绝绞统绠绡绢绣绤绥绦继绨绩绪绫绬续绮绯绰绱绲绳维绵绶绷绸绹绺绻综绽绾绿缀缁缂缃缄缅缆缇缈缉缊缋缌缍缎缏缐缑缒缓缔缕编缗缘缙缚缛缜缝缞缟缠缡缢缣缤缥缦缧缨缩缪缫缬缭缮缯缰缱缲缳缴缵罂网罗罚罢罴羁羟羡群翘翙翚耢耧耸耻聂聋职聍联聩聪肃肠肤肮肴肾肿胀胁胆胧胨胪胫胶脉脍脏脐脑脓脔脚脱脶脸腊腌腘腭腻腼腽腾膑膻臜舆舣舰舱舻艰艳艺节芈芗芜芦苁苇苈苋苌苍苎苧苹范茎茏茑茔茕茧荆荐荙荚荛荜荝荞荟荠荡荣荤荥荦荧荨荩荪荫荬荭荮药莅莱莲莳莴莶获莸莹莺莼萚萝萤营萦萧萨葱蒀蒇蒉蒋蒌蒏蓝蓟蓠蓣蓥蓦蔂蔷蔹蔺蔼蕰蕲蕴薮藓藴蘖虏虑虚虫虬虮虱虽虾虿蚀蚁蚂蚃蚕蚝蚬蛊蛎蛏蛮蛰蛱蛲蛳蛴蜕蜗蜡蝇蝈蝉蝎蝼蝾螀螨蟏衅衔补衬衮袄袆袜袭袯装裆裈裢裣裤裥褛褴襕观觃规觅视觇览觊觋觌觍觎觏觐觑觞触觯訚詟誉誊讠订讣认讥讦讧讨让讪讫讬训议讯记讱讲讳讴讵讶讷许讹论讻讼讽设访诀证诂诃评诅识诇诈诉诊诋诌词诎诏诐译诒诓诔试诖诘诙诚诛诜话诞诟诠诡询诣诤该详诧诨诩诪诫诬诮误诰诱诲诳说诵诶请诸诹诺读诼诽课诿谀谁谂调谄谅谆谇谈谉谊谋谌谍谎谏谐谑谒谓谔谕谖谗谘谙谚谛谜谝谞谟谠谡谢谣谤谥谦谧谨谩谪谫谬谭谮谯谰谱谲谳谴谵谶豮贞负贠贡财责贤败账货质贩贪贫贬购贮贯贰贱贲贳贴贵贶贷贸费贺贻贼贽贾贿赀赁赂赃资赅赆赇赈赉赊赋赌赍赎赐赑赒赓赔赕赖赗赘赙赚赛赜赝赞赟赠赡赢赣赪赵赶趋趱趸跃跄跖跞践跶跷跸跹跻踊踌踪踬踯蹑蹒蹰蹿躏躜躯輼轧轨轩轪轫转轭轮软轰轱轲轳轴轵轶轷轸轹轺轻轼载轾轿辀辁辂较辄辅辆辇辈辉辊辋辌辍辎辏辐辑辒输辔辕辖辗辘辙辚辞辟辩辫辽达迁迈运还这进远违连迟迩迳迹适逊递逦逻遗遥邓邝邬邮邹邺邻郁郏郐郑郓郦郧郸酂酝酦酱酽酾酿醖采释里銮錾钅钆钇针钉钊钋钌钍钎钏钐钑钒钓钔钕钖钗钘钙钚钛钜钝钞钠钡钢钣钤钥钦钧钨钩钪钫钬钭钮钯钰钱钲钳钴钵钶钷钸钹钺钻钼钽钾钿铀铁铂铃铄铅铆铇铈铉铊铋铌铍铎铏铐铑铒铓铔铕铖铗铘铙铚铛铜铝铞铟铠铡铢铣铤铥铦铧铨铩铪铫铬铭铮铯铰铱铳铴铵银铷铸铹铺铻铼铽链铿销锁锂锃锄锅锆锇锈锉锊锋锌锍锎锏锐锑锒锓锔锕锖锗锘错锚锛锜锝锞锟锠锡锢锣锤锥锦锧锨锩锪锫锬锭键锯锰锱锲锳锴锵锶锷锸锹锺锻锼锽锾锿镀镁镂镃镄镅镆镇镈镉镊镋镌镍镎镏镐镑镒镓镔镕镖镗镘镙镚镛镜镝镞镟镠镡镢镣镤镥镦镧镨镩镪镫镬镭镮镯镰镱镲镳镴镵镶长闩闪闫闬闭闯闰闱闲闳间闵闶闷闸闹闺闼闽闾闿阀阁阂阃阄阅阆阇阈阉阊阋阌阍阎阏阐阑阒阓阔阕阖阗阘阙阚阛队阳阴阵阶际陆陇陈陉陕陦陧陨险隐隶隽雇雏雠雳雾霁霉霡霭靓靔静靥鞑鞒鞯鞲韦韧韨韩韪韫韬韵页顶顷顸项顺须顼顽顾顿颀颁颂颃预颅领颇颈颉颊颋颌颍颎颏颐频颒颓颔颕颖颗题颙颚颛额颞颟颠颡颢颣颤颥颦颧风飏飐飑飒飓飔飕飖飗飘飙飚飞飨餍饣饤饥饦饧饨饩饪饫饬饭饮饯饰饱饲饳饴饵饶饷饸饹饺饻饼饽饾饿馀馁馂馃馄馅馆馇馈馉馊馋馌馍馎馏馐馑馒馓馔馕驭驮驯驰驱驲驳驴驵驶驷驸驹驺驻驼驽驾驿骀骁骂骃骄骅骆骇骈骉骊骋验骍骎骏骐骑骒骓骔骕骖骗骘骙骚骛骜骝骞骟骠骡骢骣骤骥骦骧髅髋髌鬓鬶魇魉鱼鱽鱾鱿鲀鲁鲂鲃鲄鲅鲆鲇鲈鲉鲊鲋鲌鲍鲎鲏鲐鲑鲒鲓鲔鲕鲖鲗鲘鲙鲚鲛鲜鲝鲞鲟鲠鲡鲢鲣鲤鲥鲦鲧鲨鲩鲪鲫鲬鲭鲮鲯鲰鲱鲲鲳鲴鲵鲶鲷鲸鲹鲺鲻鲼鲽鲾鲿鳀鳁鳂鳃鳄鳅鳆鳇鳈鳉鳊鳋鳌鳍鳎鳏鳐鳑鳒鳓鳔鳕鳖鳗鳘鳙鳚鳛鳜鳝鳞鳟鳠鳡鳢鳣鳤鸠鸡鸢鸣鸤鸥鸦鸧鸨鸩鸪鸫鸬鸭鸮鸯鸰鸱鸲鸳鸴鸵鸶鸷鸸鸹鸺鸻鸼鸽鸾鸿鹀鹁鹂鹃鹄鹅鹆鹇鹈鹉鹊鹋鹌鹍鹎鹏鹐鹑鹒鹓鹔鹕鹖鹗鹘鹙鹚鹛鹜鹝鹞鹟鹠鹡鹢鹣鹤鹥鹦鹧鹨鹩鹪鹫鹬鹭鹮鹯鹰鹱鹲鹳鹴鹾麦麸麹麺麽黄黉黡黩黪黾鼋鼌鼍鼗鼹齑齿龀龁龂龃龄龅龆龇龈龉龊龋龌龚龛鿎鿏鿒鿔鿭里里";

let _openccSimpToTrad = null;
let _openccTradToSimp = null;

function getOpenCCConverter(target) {
  const OpenCC = (typeof window !== "undefined" && window.OpenCC) || (typeof globalThis !== "undefined" && globalThis.OpenCC);
  if (!OpenCC || typeof OpenCC.Converter !== "function") return null;
  const isTrad = target === "trad" || target === "zh-hant";
  if (isTrad) {
    if (!_openccSimpToTrad) _openccSimpToTrad = OpenCC.Converter({ from: "cn", to: "t" });
    return _openccSimpToTrad;
  }
  if (!_openccTradToSimp) _openccTradToSimp = OpenCC.Converter({ from: "t", to: "cn" });
  return _openccTradToSimp;
}

function fallbackConvert(text, target) {
  if (!text) return "";
  const converter = getOpenCCConverter(target);
  if (converter) {
    try {
      return converter(text);
    } catch (_) {
      // Fall through to dictionary fallback
    }
  }
  let out = "";
  if (target === "trad" || target === "zh-hant") {
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
let availableStyleIds = new Set(["kai", "yan"]);

// Match either input script against Traditional display labels without changing
// stored font identities, source metadata or the user's draft text.
function normalizeFontSearch(text) {
  return fallbackConvert(text, 'trad').toLowerCase();
}

const BUILTIN_FONT_META = {
  "kai": {
    id: "kai",
    name_zh: "標準楷書",
    name_en: "Standard Kai (Stroke IR)",
    style_category: "kaishu",
    style_display: "楷書（擬合筆畫）",
    artist: "經典楷法",
    dynasty_era: "歷代法帖",
    font_author: "Calligraphy Engine",
    license: "開源引擎",
    char_support: "both",
    medium: "brush",
    is_downloaded: 1,
    aesthetic_notes: "基於歷代楷書傳世碑帖筆意擬合，起承轉合結構端正，筆畫骨力清健。",
    historical_reference: "歐顏柳趙傳世碑帖法度",
    sample_text: "永和九年歲在癸丑"
  },
  "yan": {
    id: "yan",
    name_zh: "顏體楷書",
    name_en: "Yan Style (Contact Strokes)",
    style_category: "kaishu",
    style_display: "顏體（接觸筆畫）",
    artist: "顏真卿",
    dynasty_era: "唐代",
    font_author: "Calligraphy Engine",
    license: "開源引擎",
    char_support: "trad",
    medium: "brush",
    is_downloaded: 1,
    aesthetic_notes: "顏真卿多寶塔碑真跡風骨，橫輕豎重，雄健端穆，氣勢磅礴。",
    historical_reference: "多寶塔碑真跡",
    sample_text: "人有悲歡離合月陰晴圓缺"
  },
  "aa shoujin": {
    id: "aa shoujin",
    name_zh: "瘦金體",
    name_en: "Shoujin (Slender Gold)",
    style_category: "kaishu",
    style_display: "瘦金體",
    artist: "宋徽宗趙佶",
    dynasty_era: "宋代",
    font_author: "HanMeiHutong",
    license: "非商業使用 / Noncommercial",
    char_support: "both",
    medium: "brush",
    is_downloaded: 1,
    aesthetic_notes: "宋徽宗趙佶獨創，天骨遒美，逸趣橫生，橫舒豎斂，骨肉兼備。",
    historical_reference: "穠芳詩帖、千字文",
    sample_text: "穠芳依翠萼，妄發讀幽尋"
  }
};

function getFontMeta(styleId) {
  if (!styleId) return undefined;
  if (styleId === 'mashanzheng') styleId = 'mashanzheng-kai';
  if (styleId === 'lishu hanwang') styleId = 'hanwang-lisu-medium';
  if (styleId === 'longcang') styleId = 'longcang-xingshu';
  return allFonts.find(f => f.id === styleId) || BUILTIN_FONT_META[styleId] || undefined;
}

let activeFilters = {
  category: "all",
  char_support: "trad",
  medium: "all",
  search: ""
};

let currentScript = "trad"; // First visits start in Traditional Chinese.

// Fonts remain private on the server; catalog samples are raster images.
function fontSampleMarkup(font) {
  if (!font) font = BUILTIN_FONT_META.kai;
  return `<img src="/api/font-samples/${encodeURIComponent(font.id)}" alt="${font.name_zh} 字樣" loading="lazy" class="font-raster-sample">`;
}

document.addEventListener('DOMContentLoaded', () => {

  const textInput = document.getElementById('text-input');
  const styleSelect = document.getElementById('style-select');
  // Persist only UI choices, never draft text, history, or share capabilities.
  // Font and calligraphy style are the same selection in this workbench.
  const preferencesStorageKey = 'calligraphy.preferences';
  const themeIds = ['theme-xuan', 'theme-gold', 'theme-rubbing'];
  let preferences = { version: 1 };
  try {
    const saved = JSON.parse(localStorage.getItem(preferencesStorageKey));
    if (saved && !Array.isArray(saved) && saved.version === 1) {
      if (typeof saved.style === 'string' && saved.style.trim() && saved.style.length <= 200) preferences.style = saved.style;
      if (themeIds.includes(saved.theme)) preferences.theme = saved.theme;
    }
  } catch (_) {
    // Malformed JSON or unavailable storage must not stop the editor.
  }
  let artworkPalette = preferences.theme === 'theme-rubbing' ? 'dark' : 'light';
  let pendingSavedStyle = preferences.style || null;
  let stylesLoaded = false, catalogLoaded = false;

  function savePreferences(changes) {
    preferences = { ...preferences, ...changes };
    try { localStorage.setItem(preferencesStorageKey, JSON.stringify(preferences)); }
    catch (_) { /* The current page still keeps choices when storage is blocked. */ }
  }

  function restoreSavedStyle() {
    if (!pendingSavedStyle) return;
    const meta = getFontMeta(pendingSavedStyle);
    const available = (stylesLoaded && availableStyleIds.has(pendingSavedStyle)) ||
      (catalogLoaded && meta && allFonts.some(font => font.id === meta.id));
    // A catalog-only font must survive the earlier /api/styles response. Failed
    // metadata requests cannot prove a font was removed: keep its saved ID.
    if (!available && !(stylesLoaded && catalogLoaded)) return;
    const styleId = available ? pendingSavedStyle :
      (availableStyleIds.has('kai') ? 'kai' : styleSelect.options[0]?.value || allFonts[0]?.id || 'kai');
    pendingSavedStyle = null;
    let option = Array.from(styleSelect.options).find(option => option.value === styleId);
    if (!option) {
      option = document.createElement('option');
      option.value = styleId;
      option.textContent = getFontMeta(styleId)?.name_zh || styleId;
      styleSelect.appendChild(option);
    }
    styleSelect.value = styleId;
    savePreferences({ style: styleId });
    applySelectedFont(styleId, { preserveText: true, persist: false });
  }
  const speedSelect = document.getElementById('speed-select');
  const fpsSelect = document.getElementById('fps-select');
  const punctuationSelect = document.getElementById('punctuation-select');
  const btnPreview = document.getElementById('btn-preview');
  const btnRender = document.getElementById('btn-render');
  const creationNotice = document.getElementById('creation-notice');
  let creationRedirectTimer = null;

  function openNotice(dialog) {
    if (dialog.open) return;
    dialog._returnFocus = document.activeElement;
    if (typeof dialog.showModal === 'function') dialog.showModal();
    else dialog.setAttribute('open', '');
  }

  function closeNotice(dialog) {
    if (typeof dialog.close === 'function') dialog.close();
    else {
      dialog.removeAttribute('open');
      dialog.dispatchEvent(new Event('close'));
    }
  }

  function cancelCreationRedirect() {
    clearTimeout(creationRedirectTimer);
    creationRedirectTimer = null;
  }

  function viewCreatedHistory() {
    cancelCreationRedirect();
    closeNotice(creationNotice);
    location.hash = '#history';
    updateRoute('history');
  }

  function acknowledgeCreation() {
    cancelCreationRedirect();
    openNotice(creationNotice);
    creationRedirectTimer = setTimeout(viewCreatedHistory, 3000);
  }

  creationNotice.addEventListener('close', cancelCreationRedirect);
  creationNotice.addEventListener('cancel', cancelCreationRedirect);
  document.getElementById('creation-view-history').addEventListener('click', viewCreatedHistory);
  const statusMessage = document.getElementById('status-message');
  const styleHint = document.getElementById('style-hint');

  // Live Stage Elements
  const calligraphyStage = document.getElementById('calligraphy-stage');
  const calligraphyText = document.getElementById('calligraphy-text');
  const activeFontBadge = document.getElementById('active-font-badge');
  const btnVertical = document.getElementById('btn-vertical');
  const btnHorizontal = document.getElementById('btn-horizontal');
  const fontSizeSlider = document.getElementById('size-slider') || document.getElementById('font-size-slider');
  const fontSizeVal = document.getElementById('size-val') || document.getElementById('font-size-val');
  const spacingSlider = document.getElementById('spacing-slider');
  const spacingVal = document.getElementById('spacing-val');
  const fitToggle = document.getElementById('fit-toggle');
  const stageViewport = document.getElementById('stage-viewport');
  const stageCaption = document.getElementById('stage-caption');
  const editorPreview = document.getElementById('editor-preview');
  const editorPreviewStatus = document.getElementById('editor-preview-status');
  const fontGlyphWarning = document.getElementById('font-glyph-warning');
  let verifiedMissingGlyphs = [];
  let verifiedGlyphKey = '';
  let editorTimer, editorRevision = 0, editorInFlight = false, editorURL = null;

  // One logical page contract for editor pixels, stills and videos. Display size
  // never changes composition; the editor endpoint only downsamples the image.
  function compositionSettings() {
    return { width: canvasWidth, height: canvasHeight, palette: artworkPalette,
      font_size: Number(fontSizeSlider?.value || 68),
      spacing: Number(spacingSlider?.value || 0.18), fit: fitToggle?.checked ?? true };
  }

  function scheduleEditorPreview() {
    editorRevision += 1;
    clearTimeout(editorTimer);
    if (verifiedGlyphKey !== JSON.stringify([textInput.value.trim(), styleSelect.value])) {
      verifiedMissingGlyphs = [];
      if (fontGlyphWarning) fontGlyphWarning.hidden = true;
    }
    if (editorPreview) editorPreview.hidden = true;
    if (editorPreviewStatus) {
      editorPreviewStatus.hidden = false;
      editorPreviewStatus.textContent = textInput.value.trim() ? '正在更新字體預覽…' : '請輸入要書寫的文字';
    }
    editorTimer = setTimeout(refreshEditorPreview, 800);
  }

  async function refreshEditorPreview() {
    if (editorInFlight || !textInput.value.trim()) return;
    const revision = editorRevision;
    editorInFlight = true;
    try {
      const res = await fetch('/api/editor-preview', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: textInput.value.trim(), style: styleSelect.value || 'kai',
          direction: currentDirection, punctuation: punctuationSelect?.value || 'omit',
          ...compositionSettings() }),
      });
      if (revision !== editorRevision) return;
      if (!res.ok) {
        const error = await res.json();
        if (revision !== editorRevision) return;
        const missing = String(error.detail || '').match(/Missing (?:font |prepared [^ ]* )?glyphs: ([^\.\n]+)/i);
        if (missing) {
          verifiedGlyphKey = JSON.stringify([textInput.value.trim(), styleSelect.value]);
          verifiedMissingGlyphs = [...new Set([...missing[1]].filter(c => /\p{Script=Han}/u.test(c)))];
          fontGlyphWarning.textContent = `此字體缺少【${verifiedMissingGlyphs.join('、')}】，請更換字體或修改文字。`;
          fontGlyphWarning.hidden = false;
        }
        if (res.status === 503) {
          editorTimer = setTimeout(refreshEditorPreview, 2000);
        }
        throw new Error(error.detail || '字體預覽暫時不可用');
      }
      const blob = await res.blob();
      if (revision !== editorRevision) return;
      verifiedMissingGlyphs = [];
      fontGlyphWarning.hidden = true;
      if (editorURL) URL.revokeObjectURL(editorURL);
      editorURL = URL.createObjectURL(blob);
      editorPreview.src = editorURL;
      editorPreview.hidden = false;
      editorPreviewStatus.hidden = true;
    } catch (error) {
      if (revision === editorRevision) editorPreviewStatus.textContent = verifiedMissingGlyphs.length
        ? '字體預覽無法更新：所選字體缺字。' : error.message;
    } finally {
      editorInFlight = false;
      if (revision !== editorRevision) editorTimer = setTimeout(refreshEditorPreview, 800);
    }
  }
  const canvasMeta = document.getElementById('canvas-meta');

  // Canvas elements and state
  const canvasFormats = document.getElementById('canvas-formats');
  const canvasLenSlider = document.getElementById('canvas-len-slider');
  const canvasLenVal = document.getElementById('canvas-len-val');
  const canvasLenAxis = document.getElementById('canvas-len-axis');
  const canvasDimVal = document.getElementById('canvas-dim-val');

  let canvasAutoLen = true;
  let canvasFormat = 'auto';
  let canvasWidth = 720;
  let canvasHeight = 960;

  // Export elements
  const exportOutputBox = document.getElementById('export-output-box');
  const btnCloseExport = document.getElementById('btn-close-export');
  const previewImageContainer = document.getElementById('preview-image-container');
  const previewImg = document.getElementById('preview-img');
  const previewSvgContainer = document.getElementById('preview-svg-container');
  const videoContainer = document.getElementById('video-container');
  const resultVideo = document.getElementById('result-video');
  const resultZoom = document.getElementById('result-zoom');
  const resultDownload = document.getElementById('result-download');
  const jobsList = document.getElementById('jobs-list');

  let previewPresentationVersion = 0;
  const resultDialog = document.getElementById('result-dialog');
  const resultBody = document.getElementById('result-body');
  const resultWarning = document.getElementById('result-warning');
  function clearResultWarning() {
    if (resultWarning) { resultWarning.textContent = ''; resultWarning.hidden = true; }
  }
  function revealResult() {
    clearResultWarning();
    if (jobDetail.open) closeNotice(jobDetail);
    resultBody.hidden = false;
    exportOutputBox.classList.remove('hidden');
    exportOutputBox.classList.remove('actual');
    openNotice(resultDialog);
  }
  resultDialog.addEventListener('close', () => {
    clearResultWarning();
    resultVideo.pause();
    resultVideo.removeAttribute('src');
    resultVideo.load();
    exportOutputBox.classList.add('hidden');
  });

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

    const styleId = styleSelect ? styleSelect.value : '';
    const missingChars = typeof getMissingCharacters === 'function' ? getMissingCharacters(rawText, styleId) : [];

    if (invalid) {
      if (charCounterEl) charCounterEl.classList.add('exceeded');
      textInput.classList.add('exceeded');
      if (charLimitWarning) {
        charLimitWarning.classList.remove('hidden');
        charLimitWarning.hidden = false;
        if (overLine) {
          const first = longLines[0];
          charLimitWarning.textContent = `第 ${first.num} 行含 ${first.len} 字，超出單行 ${MAX_LINE_CHARS} 字限制，請按回車換行分列`;
        } else {
          charLimitWarning.textContent = `總字數達 ${len} 字，超出 ${MAX_CHARS} 字上限，請刪減`;
        }
      }
      if (typeof updateCanvasDimDisplay === 'function') updateCanvasDimDisplay();
      return false;
    } else if (missingChars.length > 0) {
      if (charCounterEl) charCounterEl.classList.remove('exceeded');
      textInput.classList.remove('exceeded');
      if (charLimitWarning) {
        charLimitWarning.classList.remove('hidden');
        charLimitWarning.hidden = false;
        const fontName = typeof getActiveFontDisplayName === 'function' ? getActiveFontDisplayName(styleId) : styleId;
        const sample = missingChars.slice(0, 6).join(' ');
        const more = missingChars.length > 6 ? ` 等 ${missingChars.length} 字` : '';
        const activeSupport = typeof getActiveFontCharSupport === 'function' ? getActiveFontCharSupport(styleId) : 'trad';
        const targetScript = activeSupport === 'trad' ? '繁體' : '簡體';
        charLimitWarning.textContent = `當前字體（${fontName}）缺少字符【${sample}${more}】，無法生成；請切換字體或點擊上方“${targetScript}”轉換`;
      }
      if (typeof updateCanvasDimDisplay === 'function') updateCanvasDimDisplay();
      return true;
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

  // High-precision Trad/Simp conversion with server-side OpenCC + client OpenCC fallback
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

    scriptConversionStatus = `正在轉換文本爲${targetScript === 'trad' ? '繁體' : '簡體'}...`;
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
      const scriptLabel = targetScript === 'trad' ? '繁體中文' : '簡體中文';
      scriptConversionStatus = usedFallback
        ? `轉換服務不可用，已使用離線字表轉換爲${scriptLabel}；部分字詞可能未轉換，請檢查文本`
        : `已轉換爲${scriptLabel}`;
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
    btnTrad.setAttribute('aria-pressed', String(currentScript === 'trad'));
    btnSimp.setAttribute('aria-pressed', String(currentScript === 'simp'));
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
  function getActiveFontCharSupport(targetId) {
    const styleId = targetId || (styleSelect ? styleSelect.value : '');
    const fontMeta = getFontMeta(styleId);
    if (fontMeta && fontMeta.char_support) return fontMeta.char_support;
    if (LOCAL_FONTS_MAP[styleId] && LOCAL_FONTS_MAP[styleId].charSupport) return LOCAL_FONTS_MAP[styleId].charSupport;
    return "both";
  }

  function getActiveFontDisplayName(targetId) {
    const styleId = targetId || (styleSelect ? styleSelect.value : '');
    const fontMeta = getFontMeta(styleId);
    if (fontMeta && fontMeta.name_zh) return fontMeta.name_zh;
    if (styleSelect) {
      const opt = Array.from(styleSelect.options).find(o => o.value === styleId);
      if (opt) return opt.textContent.split(' - ')[0].trim();
    }
    return styleId || '當前字體';
  }

  // Characters that exist in traditional Chinese (Big5 / ancient heritage characters)
  // but may be converted by 1-to-1 default dictionaries (e.g. 醜 -> 醜, 裏 -> 裏, 後 -> 後).
  const TRAD_COMPAT_CHARS = new Set([
    '丑', '里', '云', '余', '准', '几', '凶', '后', '复', '干', '庄', '征', '斗',
    '杰', '极', '朴', '洒', '游', '群', '范', '触', '辟', '采', '谷', '面', '松',
    '借', '只', '卜', '板', '卷', '折', '咸', '升', '台', '叶', '愿', '据', '晒',
    '确', '秘', '筑', '雇', '适', '郁', '沈', '布', '帘', '系', '累', '克', '致',
    '历', '舍', '姜', '回', '困', '蔑', '钟', '党', '床'
  ]);

  function getMissingCharacters(text, targetId) {
    if (!text) return [];
    const styleId = targetId || (styleSelect ? styleSelect.value : '');
    const support = getActiveFontCharSupport(styleId);

    const FIXED_STYLES = {
      'yan-contact': '人有悲歡離合月陰晴圓缺此事古難全但願長久千里共嬋娟',
      'lishu': '人有悲歡離合月陰晴圓缺此事古難全但願長久千里共嬋娟',
      'liu': '人有悲歡離合月陰晴圓缺此事古難全但願長久千里共嬋娟'
    };
    const hanChars = [...new Set([...text].filter(c => /\p{Script=Han}/u.test(c)))];
    if (FIXED_STYLES[styleId]) {
      const allowed = new Set(FIXED_STYLES[styleId]);
      return hanChars.filter(c => !allowed.has(c));
    }

    if (support === 'trad') {
      const convertedFull = fallbackConvert(text, 'trad');
      if (convertedFull === text) {
        return [];
      }
      const textArr = [...text];
      const convArr = [...convertedFull];
      const changed = new Set();
      if (textArr.length === convArr.length) {
        for (let i = 0; i < textArr.length; i++) {
          if (textArr[i] !== convArr[i] && /\p{Script=Han}/u.test(textArr[i]) && !TRAD_COMPAT_CHARS.has(textArr[i])) {
            changed.add(textArr[i]);
          }
        }
        return Array.from(changed);
      }
      return hanChars.filter(c => {
        if (TRAD_COMPAT_CHARS.has(c)) return false;
        const converted = fallbackConvert(c, 'trad');
        return converted !== c;
      });
    } else if (support === 'simp') {
      const convertedFull = fallbackConvert(text, 'simp');
      if (convertedFull === text) {
        return [];
      }
      const textArr = [...text];
      const convArr = [...convertedFull];
      const changed = new Set();
      if (textArr.length === convArr.length) {
        for (let i = 0; i < textArr.length; i++) {
          if (textArr[i] !== convArr[i] && /\p{Script=Han}/u.test(textArr[i])) {
            changed.add(textArr[i]);
          }
        }
        return Array.from(changed);
      }
      return hanChars.filter(c => {
        const converted = fallbackConvert(c, 'simp');
        return converted !== c;
      });
    }
    return [];
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
      const showTradName = (currentScript === 'trad' || activeSupport === 'trad') && activeSupport !== 'simp';
      btn.textContent = (showTradName && p.nameTrad) ? p.nameTrad : p.name;
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

  function layoutStagePaper() {
    if (!calligraphyStage) return;
    // clientWidth includes padding. Fit vertical paper to the usable content
    // width instead of forcing a 260px minimum on narrow phones.
    const viewportStyle = stageViewport ? window.getComputedStyle(stageViewport) : null;
    const paddingX = viewportStyle
      ? (parseFloat(viewportStyle.paddingLeft) || 0) + (parseFloat(viewportStyle.paddingRight) || 0)
      : 0;
    const measuredWidth = stageViewport ? stageViewport.clientWidth : 0;
    const vw = measuredWidth > 0 ? Math.max(1, measuredWidth - paddingX) : 600 - 48;
    const cw = canvasWidth || 720;
    const ch = canvasHeight || 960;
    const aspect = cw / ch;
    const isVert = currentDirection === 'vertical-rl';
    const baseSizeSetting = fontSizeSlider ? parseInt(fontSizeSlider.value, 10) : 68;

    if (isVert) {
      const pw = Math.min(vw, Math.max(220, Math.min(440, Math.round((cw / 720) * 340))));
      const ph = Math.round(pw / aspect);

      calligraphyStage.style.width = `${pw}px`;
      calligraphyStage.style.height = `${ph}px`;
      calligraphyStage.style.minWidth = `${pw}px`;
      calligraphyStage.style.minHeight = `${ph}px`;

      const scale = pw / cw;
      const baseFontSize = Math.max(16, Math.round(baseSizeSetting * scale));
      if (calligraphyText) {
        calligraphyText.style.fontSize = `${baseFontSize}px`;
      }
      calligraphyStage.dataset.baseFontSize = String(baseFontSize);
    } else {
      const ph = Math.max(180, Math.min(380, Math.round((ch / 640) * 260)));
      const pw = Math.round(ph * aspect);

      calligraphyStage.style.width = `${pw}px`;
      calligraphyStage.style.height = `${ph}px`;
      calligraphyStage.style.minWidth = `${pw}px`;
      calligraphyStage.style.minHeight = `${ph}px`;

      const scale = ph / ch;
      const baseFontSize = Math.max(16, Math.round(baseSizeSetting * scale));
      if (calligraphyText) {
        calligraphyText.style.fontSize = `${baseFontSize}px`;
      }
      calligraphyStage.dataset.baseFontSize = String(baseFontSize);
    }
  }

  function isStageOverflowing() {
    if (!calligraphyStage || !calligraphyText) return false;
    const r = calligraphyText.getBoundingClientRect ? calligraphyText.getBoundingClientRect() : { width: 0, height: 0 };
    const cs = typeof window !== 'undefined' && window.getComputedStyle ? window.getComputedStyle(calligraphyStage) : null;
    const padW = cs ? (parseFloat(cs.paddingLeft) + parseFloat(cs.paddingRight)) : 56;
    const padH = cs ? (parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom)) : 48;
    const stageW = calligraphyStage.clientWidth || parseInt(calligraphyStage.style.width, 10) || 340;
    const stageH = calligraphyStage.clientHeight || parseInt(calligraphyStage.style.height, 10) || 450;

    return (r.width + padW > stageW + 2) || (r.height + padH > stageH + 2);
  }

  function fitStage(updatePreview = true) {
    if (!calligraphyStage || !calligraphyText) return;
    const baseSizeSetting = fontSizeSlider ? parseInt(fontSizeSlider.value, 10) : 68;
    const stageW = calligraphyStage.clientWidth || parseInt(calligraphyStage.style.width, 10) || 340;
    const baseFontSize = parseFloat(calligraphyStage.dataset.baseFontSize) ||
      Math.max(16, Math.round(baseSizeSetting * (stageW / (canvasWidth || 720))));
    let size = baseFontSize;
    calligraphyText.style.fontSize = `${size}px`;

    const shouldFit = fitToggle ? fitToggle.checked : true;
    if (shouldFit && isStageOverflowing()) {
      let lo = 12, hi = size;
      while (hi - lo > 1) {
        const mid = Math.floor((lo + hi) / 2);
        calligraphyText.style.fontSize = `${mid}px`;
        if (isStageOverflowing()) hi = mid; else lo = mid;
      }
      size = lo;
      calligraphyText.style.fontSize = `${size}px`;
    }

    const shrunk = size < baseFontSize;
    if (fontSizeVal) {
      fontSizeVal.textContent = shrunk
        ? `${baseSizeSetting}px (自動縮小適應)`
        : `${baseSizeSetting}px`;
    }
    const len = [...((textInput ? textInput.value : '') || '').replace(/\s/g, '')].length;
    if (stageCaption) {
      stageCaption.innerHTML = `<span>${len} 字 · ${currentDirection === 'vertical-rl' ? '豎排右起' : '橫排'} · 畫布 ${canvasWidth}×${canvasHeight}</span><span>${shrunk ? '字數超出已微調適應' : ''}</span>`;
    }
    if (canvasMeta) {
      canvasMeta.textContent = typeof getActiveFontDisplayName === 'function' ? getActiveFontDisplayName() : '';
    }
    if (updatePreview) scheduleEditorPreview();
  }

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
    const axis = isVert ? '高度' : '寬度';
    const len = isVert ? canvasHeight : canvasWidth;

    if (canvasLenAxis) canvasLenAxis.textContent = axis;
    if (canvasLenSlider) {
      canvasLenSlider.min = Math.min(Number(canvasLenSlider.min), len);
      canvasLenSlider.max = Math.max(Number(canvasLenSlider.max), len);
      canvasLenSlider.value = len;
    }
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
    layoutStagePaper();
    fitStage();
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
    updateCanvasDimDisplay();
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
  if (fontSizeSlider) {
    if (fontSizeVal) fontSizeVal.textContent = `${fontSizeSlider.value}px`;
    fontSizeSlider.addEventListener('input', (e) => {
      const px = e.target.value + 'px';
      if (fontSizeVal) fontSizeVal.textContent = px;
      layoutStagePaper();
      fitStage();
    });
  }

  // Character spacing slider
  if (spacingSlider) {
    const initialSpacing = `${spacingSlider.value}em`;
    if (spacingVal) spacingVal.textContent = initialSpacing;
    if (calligraphyText) calligraphyText.style.letterSpacing = initialSpacing;
    spacingSlider.addEventListener('input', (e) => {
      const em = e.target.value + 'em';
      if (spacingVal) spacingVal.textContent = em;
      if (calligraphyText) calligraphyText.style.letterSpacing = em;
      fitStage();
    });
  }

  if (fitToggle) {
    fitToggle.addEventListener('change', fitStage);
  }

  // Numeric matching also handles the standard speed button's "1" vs "1.0".
  const speedSeg = document.getElementById('speed-seg');
  const fpsSeg = document.getElementById('fps-seg');

  function selectOutputValue(select, segment, key, value) {
    if (select) {
      const option = Array.from(select.options).find(o => Number(o.value) === value);
      if (option) select.value = option.value;
    }
    segment?.querySelectorAll('.seg-btn').forEach(button => {
      const active = Number(button.dataset[key]) === value;
      button.classList.toggle('active', active);
      button.setAttribute('aria-pressed', String(active));
    });
  }

  for (const [select, segment, key] of [[speedSelect, speedSeg, 'speed'], [fpsSelect, fpsSeg, 'fps']]) {
    segment?.addEventListener('click', event => {
      const button = event.target.closest('.seg-btn');
      if (button && segment.contains(button)) selectOutputValue(select, segment, key, Number(button.dataset[key]));
    });
    selectOutputValue(select, segment, key, Number(select?.value));
  }

  // Apply selected font to live calligraphy stage and update badge
  function applySelectedFont(styleId, { preserveText = false } = {}) {
    if (!calligraphyText) return;

    // Check local font mapping
    calligraphyText.style.fontFamily = "var(--font-serif)";

    // Find font metadata in catalog if available
    const fontMeta = getFontMeta(styleId);
    if (fontMeta && activeFontBadge) {
      activeFontBadge.innerHTML = `
        <strong>當前臨摹字庫：</strong>${fontMeta.name_zh} (${fontMeta.name_en || fontMeta.id}) ·
        <strong>書法脈系：</strong>${fontMeta.style_display} ·
        <strong>名家宗師：</strong>${fontMeta.artist} (${fontMeta.dynasty_era}) ·
        <strong>經典出處：</strong>${fontMeta.historical_reference || "傳世名作"}
      `;
    } else if (activeFontBadge) {
      activeFontBadge.innerHTML = `<strong>當前書法風格：</strong>${styleId}`;
    }

    // Automatically adapt example section and script toggle to font's support
    const activeSupport = getActiveFontCharSupport(styleId);
    if (!preserveText && activeSupport === 'trad' && (currentScript !== 'trad' || getMissingCharacters(textInput.value, styleId).length > 0)) {
      performScriptConversion('trad');
    } else if (!preserveText && activeSupport === 'simp' && (currentScript !== 'simp' || getMissingCharacters(textInput.value, styleId).length > 0)) {
      performScriptConversion('simp');
    } else {
      renderPresets();
    }

    updateStyleHint();
    updateText();
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
      styleHint.innerHTML = '💡 <strong>霞鶩文楷繁體版</strong>：文人手書清雅風骨，全字庫完備覆蓋，<strong>已自動切換為繁體法帖示例</strong>。';
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
      styleHint.innerHTML = '💡 <strong>閔齊伋令東齊伋體楷書</strong>：明代套印刻本巔峯之作，古雅絕倫、刀筆兼融，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'iansui-kai') {
      styleHint.innerHTML = '💡 <strong>芫荽硬筆楷書</strong>：ButTaiwan 依據手寫楷體改造，清麗溫潤，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'yuji-boku') {
      styleHint.innerHTML = '💡 <strong>佑字 · 墨</strong>：成田佑司手寫真跡，筆酣墨飽、枯筆飛白，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'yuji-mai') {
      styleHint.innerHTML = '💡 <strong>佑字 · 舞</strong>：成田佑司手寫真跡，翩若驚鴻、富於律動，<strong>已自動切換為繁體法帖示例</strong>。';
    } else if (val === 'yuji-syuku') {
      styleHint.innerHTML = '💡 <strong>佑字 · 宿</strong>：成田佑司手寫真跡，端穆沉靜、內斂古拙，<strong>已自動切換爲繁體法帖示例</strong>。';
    } else if (val === 'klee-one' || val === 'klee-one-semibold') {
      styleHint.innerHTML = '💡 <strong>Fontworks Klee 手寫楷體</strong>：日本頂級字廠典範，兼具正楷法度與日常手書靈韻。';
    } else if (val.startsWith('jason-handwriting')) {
      styleHint.innerHTML = '💡 <strong>遊清松清鬆手寫體</strong>：當代書法名家遊清松先生數年全字庫手寫真跡，溫潤清秀。';
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
    revealResult();
    videoContainer.classList.add('hidden');
    resultVideo.pause();
    previewImg.classList.remove('hidden');
    previewImg.src = url;
    previewSvgContainer.replaceChildren();
    previewSvgContainer.classList.add('hidden');
    previewImageContainer.classList.remove('hidden');
    if (resultDownload) {
      resultDownload.href = url;
      resultDownload.setAttribute('download', 'calligraphy_preview.png');
      resultDownload.hidden = false;
    }
    if (resultZoom) {
      resultZoom.hidden = false;
      resultZoom.textContent = '實際大小';
    }
    exportOutputBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showPreviewSvg(svgContent) {
    revealResult();
    videoContainer.classList.add('hidden');
    resultVideo.pause();
    previewImg.classList.add('hidden');
    // Keep the image node mounted for later direct and history previews.
    previewSvgContainer.innerHTML = svgContent;
    previewSvgContainer.classList.remove('hidden');
    const svgEl = previewSvgContainer.querySelector('svg');
    if (svgEl) {
      svgEl.style.maxWidth = '88%';
      svgEl.style.maxHeight = '100%';
      svgEl.style.boxShadow = '0 4px 16px rgba(0, 0, 0, 0.08)';
    }
    previewImageContainer.classList.remove('hidden');
    if (resultDownload) {
      try {
        const blob = new Blob([svgContent], { type: 'image/svg+xml' });
        resultDownload.href = URL.createObjectURL(blob);
      } catch (_) {
        resultDownload.href = '#';
      }
      resultDownload.setAttribute('download', 'calligraphy_preview.svg');
      resultDownload.hidden = false;
    }
    if (resultZoom) {
      resultZoom.hidden = false;
      resultZoom.textContent = '實際大小';
    }
    exportOutputBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showVideo(videoUrl, downloadUrl) {
    revealResult();
    previewImageContainer.classList.add('hidden');
    const dlBtn = document.getElementById('btn-video-dl');
    if (dlBtn && (downloadUrl || videoUrl)) {
      dlBtn.href = downloadUrl || videoUrl;
    }
    if (resultDownload) {
      resultDownload.href = downloadUrl || videoUrl;
      resultDownload.setAttribute('download', 'calligraphy_video.mp4');
      resultDownload.hidden = false;
    }
    if (resultZoom) {
      resultZoom.hidden = true;
    }
    if (resultVideo && videoUrl) {
      resultVideo.src = videoUrl;
      resultVideo.load();
    }
    videoContainer.classList.remove('hidden');
    exportOutputBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  if (resultZoom) {
    resultZoom.addEventListener('click', () => {
      if (exportOutputBox) {
        const actual = exportOutputBox.classList.toggle('actual');
        resultZoom.textContent = actual ? '適應窗口' : '實際大小';
      }
    });
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
        if (Array.isArray(data.styles)) {
          availableStyleIds = new Set(data.styles.map(s => s.id));
          stylesLoaded = true;
          const currentVal = styleSelect.value;
          const currentOption = styleSelect.selectedOptions[0]?.cloneNode(true);
          styleSelect.innerHTML = '';
          data.styles.forEach(s => {
            const opt = document.createElement('option');
            opt.value = s.id;
            opt.textContent = fallbackConvert(`${s.name} - ${s.description || ''}`, 'trad');
            styleSelect.appendChild(opt);
          });
          // Catalog/history selections can precede the styles response.
          if (currentOption && !Array.from(styleSelect.options).some(o => o.value === currentVal)) {
            styleSelect.appendChild(currentOption);
          }
          // Default to generic Kai; preserve an explicitly selected style.
          if (currentVal && Array.from(styleSelect.options).some(o => o.value === currentVal)) {
            styleSelect.value = currentVal;
          } else if (Array.from(styleSelect.options).some(o => o.value === 'kai')) {
            styleSelect.value = 'kai';
          }
          restoreSavedStyle();
          applySelectedFont(styleSelect.value, { preserveText: true, persist: false });
          renderFontGrid();
        }
      }
    } catch (e) {
      console.warn('Failed to load dynamic styles:', e);
    }
  }

  // Preview action
  btnPreview.addEventListener('click', async () => {
    if (btnPreview.disabled) return;
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
    const missingPreview = [...new Set([...getMissingCharacters(text, style), ...verifiedMissingGlyphs])];
    if (missingPreview.length > 0) {
      const activeSupport = getActiveFontCharSupport(style);
      const targetScript = activeSupport === 'trad' ? '繁體' : '簡體';
      const sample = missingPreview.slice(0, 6).join('、');
      showStatus(`當前字體缺少字符【${sample}】，無法生成；請切換字體或轉爲${targetScript}`, 'error');
      return;
    }

    const presentationVersion = ++previewPresentationVersion;
    btnPreview.disabled = true;
    showStatus('正在生成高精度靜圖預覽...', 'info');

    try {
      const punctuation = punctuationSelect ? punctuationSelect.value : 'omit';
      const res = await fetch('/api/previews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, style, format: 'auto', ...compositionSettings(), direction: currentDirection, punctuation })
      });

      if (!res.ok) {
        const err = await res.json();
        const detail = err.detail || '預覽失敗';
        if (/missing.*glyph/i.test(detail)) {
          const match = detail.match(/Missing (?:font |prepared [^ ]* )?glyphs: ([^\.]+)/i);
          const chars = match ? match[1].trim() : '';
          const msg = chars ? `當前字體缺少字符【${chars}】，無法生成` : '當前字體缺少字符，無法生成';
          showStatus(msg, 'error');
          if (charLimitWarning) {
            charLimitWarning.textContent = msg;
            charLimitWarning.hidden = false;
            charLimitWarning.classList.remove('hidden');
          }
          return;
        }
        throw new Error(detail);
      }

      const data = await res.json();
      if (presentationVersion !== previewPresentationVersion) return;
      if (data.svg) {
        showPreviewSvg(data.svg);
      } else if (data.preview_url) {
        showPreviewImage(data.preview_url);
      }
      if (resultWarning) {
        resultWarning.textContent = data.warning_message || '';
        resultWarning.hidden = !data.warning_message;
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
    const missingRender = [...new Set([...getMissingCharacters(text, style), ...verifiedMissingGlyphs])];
    if (missingRender.length > 0) {
      const activeSupport = getActiveFontCharSupport(style);
      const targetScript = activeSupport === 'trad' ? '繁體' : '簡體';
      const sample = missingRender.slice(0, 6).join('、');
      showStatus(`當前字體缺少字符【${sample}】，無法生成；請切換字體或轉爲${targetScript}`, 'error');
      return;
    }

    const speed = parseFloat(speedSelect.value);
    const fps = parseInt(fpsSelect.value, 10);

    btnRender.disabled = true;
    hideStatus();

    try {
      const punctuation = punctuationSelect ? punctuationSelect.value : 'omit';
      const res = await fetch('/api/renders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, style, speed, fps, ...compositionSettings(), direction: currentDirection, punctuation })
      });

      if (!res.ok) {
        const err = await res.json();
        const detail = err.detail || '任務創建失敗';
        if (/missing.*glyph/i.test(detail)) {
          const match = detail.match(/Missing (?:font |prepared [^ ]* )?glyphs: ([^\.]+)/i);
          const chars = match ? match[1].trim() : '';
          const msg = chars ? `當前字體缺少字符【${chars}】，無法生成` : '當前字體缺少字符，無法生成';
          showStatus(msg, 'error');
          if (charLimitWarning) {
            charLimitWarning.textContent = msg;
            charLimitWarning.hidden = false;
            charLimitWarning.classList.remove('hidden');
          }
          return;
        }
        throw new Error(detail);
      }

      await res.json();
      // Only submission owns the button. Progress belongs to the job card,
      // and a repeated request can reuse the same active server-side job.
      hasActiveJobs = true;
      loadJobs();
      acknowledgeCreation();
    } catch (e) {
      showStatus(`提交失敗: ${e.message}`, 'error');
    } finally {
      btnRender.disabled = false;
    }
  });

  let jobsRefreshTimer = null;
  let jobsLoadVersion = 0;
  let hasActiveJobs = false;
  const activeJobStatuses = new Set(['queued', 'rendering', 'running']);
  let cachedJobs = [];
  let historyActiveFilter = 'all';
  let historySearchQuery = '';

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function expiryDateTime(timestamp) {
    const date = new Date(timestamp * 1000);
    return Number.isFinite(timestamp) && Number.isFinite(date.getTime())
      ? date.toLocaleString('zh-TW', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false, timeZoneName: 'short' }) : '';
  }

  function jobRetentionNotice(job) {
    if (activeJobStatuses.has(job.status)) return '完成後顯示保留期限';
    const retention = job.retention;
    if (job.status === 'succeeded' && retention?.output_available === false) return '作品檔案已移除，無法下載';
    const deadline = expiryDateTime(retention?.expires_at);
    if (!deadline) return job.status === 'succeeded' ? '保留期限暫未提供，請儘早下載作品' : '保留期限暫未提供';
    const subject = job.status === 'failed' ? '記錄' : '作品';
    if (retention.expires_at * 1000 <= Date.now()) return `${subject}已到保留期限（${deadline}），即將清理`;
    const extended = retention.share_expires_at > retention.ordinary_expires_at;
    return `${subject}保留至 ${deadline}${extended ? '（分享延長）' : ''}`;
  }

  function updateRetentionDuration(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return;
    const duration = seconds % 3600 === 0 ? `${seconds / 3600} 小時`
      : seconds % 60 === 0 ? `${seconds / 60} 分鐘` : `${seconds} 秒`;
    document.querySelectorAll('[data-retention-duration]').forEach(element => { element.textContent = duration; });
  }

  // Job detail dialog controls
  const jobDetail = document.getElementById('job-detail');
  const detailViewer = document.getElementById('detail-viewer');
  const detailZoom = document.getElementById('detail-zoom');
  const detailDownload = document.getElementById('detail-download');
  const detailMeta = document.getElementById('detail-meta');
  const detailText = document.getElementById('detail-text');
  const detailReuse = document.getElementById('detail-reuse');

  if (detailZoom) {
    detailZoom.addEventListener('click', () => {
      if (detailViewer) {
        const isActual = detailViewer.classList.toggle('actual');
        detailZoom.textContent = isActual ? '適應窗口' : '實際大小';
      }
    });
  }

  function restoreJobSettings(job) {
    const params = job.params && typeof job.params === 'object' && !Array.isArray(job.params) ? job.params : {};
    const notices = [];
    const recognized = new Set(['width', 'height', 'font_size', 'fit', 'direction', 'spacing', 'gap', 'punctuation', 'speed', 'fps', 'palette']);
    const readNumber = (key, fallback, min, max, integer = false) => {
      const value = params[key];
      if (value === undefined || value === null) return fallback;
      if (typeof value === 'number' && Number.isFinite(value) && value >= min && value <= max && (!integer || Number.isInteger(value))) return value;
      notices.push(`${key} 已超出目前支援範圍，改用 ${fallback}`);
      return fallback;
    };
    const restoreRange = (control, value, label) => {
      if (!control) { notices.push(`${label}控制項不可用`); return; }
      control.min = Math.min(Number(control.min), value);
      control.max = Math.max(Number(control.max), value);
      // Range inputs must not round a valid API value to the UI preset step.
      control.step = control === fontSizeSlider ? '1' : 'any';
      control.value = String(value);
    };
    const restoreOutput = (select, segment, key, value, label) => {
      if (!select || !segment) { notices.push(`${label}控制項不可用`); return; }
      select.querySelectorAll('[data-history-value]').forEach(el => el.remove());
      segment.querySelectorAll('[data-history-value]').forEach(el => el.remove());
      if (!Array.from(select.options).some(o => Number(o.value) === value)) {
        const option = document.createElement('option');
        option.value = String(value);
        option.textContent = String(value);
        option.dataset.historyValue = '';
        select.appendChild(option);
      }
      if (!Array.from(segment.querySelectorAll('.seg-btn')).some(b => Number(b.dataset[key]) === value)) {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'seg-btn';
        button.dataset[key] = String(value);
        button.dataset.historyValue = '';
        button.textContent = `${value}${key === 'fps' ? ' fps' : '×'}（歷史）`;
        segment.appendChild(button);
      }
      selectOutputValue(select, segment, key, value);
    };

    invalidateScriptConversion();
    textInput.value = job.text || '';
    // Saved pixel dimensions are authoritative, even when the original draft was adaptive.
    // Older jobs used the worker's 720×960 defaults, never the current draft's size.
    canvasAutoLen = false;
    canvasWidth = readNumber('width', 720, 64, 2400, true);
    canvasHeight = readNumber('height', 960, 64, 2400, true);
    if (canvasWidth * canvasHeight > 2400 * 1280) {
      canvasWidth = 720;
      canvasHeight = 960;
      notices.push('歷史畫布超出目前支援面積，改用 720 × 960');
    }
    const format = Array.from(canvasFormats?.querySelectorAll('[data-w][data-h]') || [])
      .find(button => Number(button.dataset.w) === canvasWidth && Number(button.dataset.h) === canvasHeight);
    canvasFormat = format?.dataset.cf || 'custom';
    if (canvasLenSlider) canvasLenSlider.step = '1';
    const fontSize = readNumber('font_size', 68, 8, 160, true);
    restoreRange(fontSizeSlider, fontSize, '字號');
    if (params.font_size == null) notices.push('舊任務未記錄字號，原本採用整頁自動排版；現以 68px 載入，重製外觀可能不同');
    if (fitToggle) fitToggle.checked = typeof params.fit === 'boolean' ? params.fit : true;
    else notices.push('適應畫布控制項不可用');
    if (params.fit != null && typeof params.fit !== 'boolean') notices.push('適應畫布設定無效，已啟用預設值');

    const direction = params.direction ?? 'vertical-rl';
    if (!['vertical-rl', 'horizontal-lr'].includes(direction)) notices.push('排版方向無效，改用豎排右起');
    selectDirection(['vertical-rl', 'horizontal-lr'].includes(direction) ? direction : 'vertical-rl');
    // Legacy worker rows may use gap instead of spacing.
    const spacing = readNumber(params.spacing == null && params.gap != null ? 'gap' : 'spacing', 0.18, 0, 2);
    restoreRange(spacingSlider, spacing, '字距');
    if (spacingVal) spacingVal.textContent = `${spacing}em`;
    if (calligraphyText) calligraphyText.style.letterSpacing = `${spacing}em`;
    const punctuation = params.punctuation ?? 'omit';
    if (!['omit', 'break'].includes(punctuation)) notices.push('標點設定無效，改用忽略標點');
    if (punctuationSelect) punctuationSelect.value = ['omit', 'break'].includes(punctuation) ? punctuation : 'omit';
    else notices.push('標點控制項不可用');
    restoreOutput(speedSelect, speedSeg, 'speed', readNumber('speed', 1, 0.25, 4), '視頻速度');
    restoreOutput(fpsSelect, fpsSeg, 'fps', readNumber('fps', 24, 1, 60, true), '幀率');

    const palette = params.palette ?? 'light';
    if (!['light', 'dark'].includes(palette)) notices.push('紙墨配色無效，改用淺紙深墨');
    // Old jobs predate palette selection and were rendered on light paper.
    selectTheme(palette === 'dark' ? 'theme-rubbing' :
      (themeSelect?.value === 'theme-gold' ? 'theme-gold' : 'theme-xuan'));

    // Custom legacy colors and transforms still have no editor controls.
    const implicitDefaults = { paper: '#f8f3e9', ink: '#1c1b18', stroke_seconds: 0.18,
      character_gap: 0.15, intro: 0.5, outro: 1, scale: 1, stretch: 1, rotation: 0,
      characters_per_line: null, format: 'auto' };
    const unsupported = Object.keys(params).filter(key => !recognized.has(key) &&
      !(Object.hasOwn(implicitDefaults, key) && params[key] === implicitDefaults[key]));
    if (unsupported.length) notices.push(`目前無法套用的歷史設定：${unsupported.join('、')}。請核對成品；自訂紙墨顏色無法完整還原`);

    const originalStyle = job.style || 'kai';
    const meta = getFontMeta(originalStyle);
    const isAvailable = availableStyleIds.has(originalStyle) || (meta && allFonts.some(font => font.id === meta.id));
    const selectedStyle = isAvailable ? originalStyle : (availableStyleIds.has('kai') ? 'kai' : styleSelect.options[0]?.value || 'kai');
    if (!isAvailable) notices.push(`原字體「${originalStyle}」目前不可用，已改用「${getActiveFontDisplayName(selectedStyle)}」`);
    let option = Array.from(styleSelect.options).find(o => o.value === selectedStyle);
    if (!option) {
      option = document.createElement('option');
      option.value = selectedStyle;
      option.textContent = meta?.name_zh || selectedStyle;
      styleSelect.appendChild(option);
    }
    styleSelect.value = selectedStyle;
    // Reuse is not a request to convert the saved text into another script.
    applySelectedFont(selectedStyle, { preserveText: true });
    const notice = document.getElementById('history-reuse-notice');
    if (notice) {
      notice.textContent = notices.join('；');
      notice.hidden = notices.length === 0;
    }
    return notices;
  }

  function openJobDetail(j) {
    if (!jobDetail) return;
    jobDetail.dataset.jobId = j.job_id;
    previewPresentationVersion += 1;
    if (resultDialog.open) closeNotice(resultDialog);
    detailViewer.querySelectorAll('video').forEach(video => { video.pause(); video.removeAttribute('src'); video.load(); });
    detailViewer.classList.remove('actual');
    detailZoom.textContent = '實際大小';
    detailZoom.hidden = j.job_type === 'render';
    const share = document.getElementById('detail-share');
    share.hidden = !(j.status === 'succeeded' && j.job_type === 'render');
    share.onclick = () => openVideoShare(j.job_id);
    const isVideo = j.job_type === 'render';
    const videoSrc = j.video_url || `/api/jobs/${j.job_id}/video`;
    const imageSrc = j.download_url || `/api/jobs/${j.job_id}/image`;
    const dlSrc = j.download_url || (isVideo ? `/api/jobs/${j.job_id}/download` : imageSrc);

    if (detailViewer) {
      detailViewer.innerHTML = '';
      if (j.status === 'succeeded') {
        if (isVideo) {
          const vid = document.createElement('video');
          vid.src = videoSrc;
          vid.controls = true;
          vid.preload = 'metadata';
          vid.loop = true;
          vid.playsInline = true;
          vid.setAttribute('playsinline', '');
          detailViewer.appendChild(vid);
          vid.load();
        } else {
          const img = document.createElement('img');
          img.src = imageSrc;
          img.alt = '成品預覽';
          detailViewer.appendChild(img);
        }
      } else {
        const ph = document.createElement('div');
        ph.className = 'placeholder';
        ph.textContent = j.status === 'failed' ? (j.error_message || '任務失敗') : '任務正在渲染中…';
        detailViewer.appendChild(ph);
      }
    }

    if (detailDownload) {
      if (j.status === 'succeeded') {
        detailDownload.href = dlSrc;
        detailDownload.setAttribute('download', isVideo ? `calligraphy_${j.job_id}.mp4` : `calligraphy_${j.job_id}.svg`);
        detailDownload.hidden = false;
      } else {
        detailDownload.hidden = true;
      }
    }

    const fontMeta = getFontMeta(j.style);
    const fontName = fontMeta ? fontMeta.name_zh : j.style;
    const timeStr = j.created_at ? j.created_at.replace('T', ' ').substring(0, 16) : '';
    const statusLabel = j.status === 'succeeded' ? '已完成' : (j.status === 'failed' ? '失敗' : '進行中');

    if (detailMeta) {
      detailMeta.innerHTML = `
        <dt>任務類型</dt><dd>${isVideo ? '書寫視頻' : '矢量靜圖'}</dd>
        <dt>所用字庫</dt><dd>${escapeHtml(fontName)} (${escapeHtml(j.style)})</dd>
        <dt>任務狀態</dt><dd>${statusLabel}</dd>
        ${j.status === 'succeeded' && j.warning_message ? `<dt>成品提醒</dt><dd class="job-warning">${escapeHtml(j.warning_message)}</dd>` : ''}
        <dt>創建時間</dt><dd>${timeStr}</dd>
        <dt>保留期限</dt><dd data-detail-retention>${escapeHtml(jobRetentionNotice(j))}</dd>
        <dt data-detail-share-label ${j.retention?.share_expires_at ? '' : 'hidden'}>分享連結期限</dt><dd data-detail-share-expiry ${j.retention?.share_expires_at ? '' : 'hidden'}>${j.retention?.share_expires_at ? `有效至 ${escapeHtml(expiryDateTime(j.retention.share_expires_at))}；停用分享會取消延長保留` : ''}</dd>
        <dt>任務編號</dt><dd>${escapeHtml(j.job_id)}</dd>
      `;
    }

    if (detailText) {
      detailText.textContent = j.text || '';
    }

    if (detailReuse) {
      detailReuse.onclick = () => {
        const notices = restoreJobSettings(j);
        closeNotice(jobDetail);
        location.hash = '#create';
        showStatus(notices.length ? '已載入文本與可用設定，請查看版式區的還原提示' : '已將歷史任務設定與文本載入創作臺', 'info');
        setTimeout(hideStatus, 2500);
      };
    }

    openNotice(jobDetail);
  }

  if (jobDetail) {
    jobDetail.addEventListener('close', () => {
      if (detailViewer) {
        const vid = detailViewer.querySelector('video');
        if (vid) { vid.pause(); vid.removeAttribute('src'); vid.load(); }
        detailViewer.replaceChildren();
      }
    });
  }

  const deleteHistory = document.getElementById('delete-history');
  const confirmDeleteHistory = document.getElementById('confirm-delete-history');
  const deleteHistoryError = document.getElementById('delete-history-error');
  let pendingDeleteJob = null;
  let deletingHistory = false;

  function confirmHistoryDeletion(job) {
    if (!deleteHistory || deletingHistory) return;
    pendingDeleteJob = job;
    document.getElementById('delete-history-text').textContent = job.text || '';
    deleteHistoryError.hidden = true;
    deleteHistory.showModal();
  }

  if (deleteHistory) {
    deleteHistory.addEventListener('close', () => { pendingDeleteJob = null; });
  }
  if (confirmDeleteHistory) {
    confirmDeleteHistory.addEventListener('click', async () => {
      if (!pendingDeleteJob || deletingHistory) return;
      const job = pendingDeleteJob;
      deletingHistory = true;
      confirmDeleteHistory.disabled = true;
      deleteHistoryError.hidden = true;
      try {
        const res = await fetch(`/api/jobs/${encodeURIComponent(job.job_id)}`, { method: 'DELETE' });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || '刪除失敗，請重試');
        }
        // Invalidate any list response captured before the deletion.
        ++jobsLoadVersion;
        forgetShareLink(job.job_id);
        cachedJobs = cachedJobs.filter(j => j.job_id !== job.job_id);
        renderJobList();
        deleteHistory.close();
        await loadJobs();
      } catch (e) {
        deleteHistoryError.textContent = e.message || '刪除失敗，請重試';
        deleteHistoryError.hidden = false;
      } finally {
        deletingHistory = false;
        confirmDeleteHistory.disabled = false;
      }
    });
  }

  // History filters & search
  const historyFilters = document.getElementById('history-filters');
  if (historyFilters) {
    historyFilters.addEventListener('click', (e) => {
      const chip = e.target.closest('.chip');
      if (!chip) return;
      historyFilters.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      historyActiveFilter = chip.dataset.hf || 'all';
      renderJobList();
    });
  }

  const historySearch = document.getElementById('history-search');
  if (historySearch) {
    historySearch.addEventListener('input', (e) => {
      historySearchQuery = e.target.value.trim().toLowerCase();
      renderJobList();
    });
  }

  function renderJobList() {
    if (!jobsList) return;
    const historyEmpty = document.getElementById('history-empty');

    const filtered = cachedJobs.filter(j => {
      if (historyActiveFilter === 'render' && j.job_type !== 'render') return false;
      if (historyActiveFilter === 'preview' && j.job_type !== 'preview') return false;
      if (historyActiveFilter === 'active' && !activeJobStatuses.has(j.status)) return false;
      if (historyActiveFilter === 'failed' && j.status !== 'failed') return false;

      if (historySearchQuery) {
        const q = historySearchQuery;
        const fontMeta = getFontMeta(j.style);
        const fontName = fontMeta ? fontMeta.name_zh : j.style;
        const hay = [j.text, j.style, fontName].join(' ').toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    if (historyEmpty) {
      historyEmpty.hidden = filtered.length > 0;
    }

    if (filtered.length === 0) {
      jobsList.innerHTML = cachedJobs.length === 0
        ? '<p class="empty-jobs">暫無生成任務</p>'
        : '<p class="empty-jobs">未找到符合條件的任務記錄</p>';
      return;
    }

    jobsList.innerHTML = '';
    filtered.forEach(j => {
      const item = document.createElement('div');
      item.className = 'job-card job-item';
      item.dataset.jobId = j.job_id;

      const isVideo = j.job_type === 'render';
      const videoSrc = j.video_url || `/api/jobs/${j.job_id}/video`;
      const imageSrc = j.download_url || `/api/jobs/${j.job_id}/image`;
      const dlSrc = j.download_url || (isVideo ? `/api/jobs/${j.job_id}/download` : imageSrc);

      const pct = Math.round(Math.max(0, Math.min(1, j.progress || 0)) * 100);
      const statusLabels = {
        queued: '排隊中',
        rendering: `渲染中 (${pct}%)`,
        running: `渲染中 (${pct}%)`,
        succeeded: '完成',
        failed: '失敗',
      };
      const statusLabel = statusLabels[j.status] || j.status;
      const fontMeta = getFontMeta(j.style);
      const fontName = fontMeta ? fontMeta.name_zh : j.style;
      const timeStr = j.created_at ? (j.created_at.split('T')[1]?.substring(0, 5) || '') : '';

      let thumbHtml = '';
      if (j.status === 'succeeded') {
        if (isVideo) {
          thumbHtml = `<video src="${videoSrc}" muted preload="metadata" playsinline></video>`;
        } else {
          thumbHtml = `<img src="${imageSrc}" alt="預覽" loading="lazy" />`;
        }
      } else if (j.status === 'failed') {
        thumbHtml = `<div class="placeholder">渲染失敗</div>`;
      } else {
        thumbHtml = `<div class="placeholder">生成中 (${pct}%)</div>`;
      }

      item.innerHTML = `
        <div class="job-thumb">
          <span class="job-kind">${isVideo ? '視頻' : '靜圖'}</span>
          ${thumbHtml}
        </div>
        <div class="job-body">
          <div class="job-text">${escapeHtml(j.text || '')}</div>
          <div class="job-meta">
            <span class="job-details">${escapeHtml(fontName)} · ${timeStr}</span>
            <span class="status ${j.status} job-status-badge">${statusLabel}</span>
          </div>
          <p class="job-retention">${escapeHtml(jobRetentionNotice(j))}</p>
          ${j.status === 'succeeded' && j.warning_message ? `<p class="job-warning">${escapeHtml(j.warning_message)}</p>` : ''}
          ${activeJobStatuses.has(j.status) ? `<div class="mini-bar"><i style="width:${pct}%"></i></div>` : ''}
          ${j.status === 'failed' && j.error_message ? `<span class="job-details job-error">${escapeHtml(j.error_message)}</span>` : ''}
          ${j.status === 'succeeded' ? `
            <div class="job-action">
              ${isVideo ? '<button type="button" class="btn btn-secondary btn-sm btn-share-video">分享</button>' : ''}
              <button type="button" class="btn btn-secondary btn-sm btn-play-mini">${isVideo ? '▶ 播放' : '👁 查看'}</button>
              <a href="${dlSrc}" download="calligraphy_${j.job_id}.${isVideo ? 'mp4' : 'svg'}" class="btn btn-secondary btn-sm btn-download">${isVideo ? '下載 MP4' : '下載 SVG'}</a>
            </div>
          ` : ''}
          <div class="job-action">
            <button type="button" class="btn btn-ghost btn-sm btn-delete-history" ${activeJobStatuses.has(j.status) ? 'disabled title="任務完成後可刪除"' : ''}>刪除</button>
          </div>
        </div>
      `;

      item.addEventListener('click', (e) => {
        if (e.target.closest('button') || e.target.closest('a')) return;
        openJobDetail(j);
      });

      const thumbVid = item.querySelector('.job-thumb video');
      if (thumbVid) {
        item.addEventListener('mouseenter', () => {
          thumbVid.play().catch(() => {});
        });
        item.addEventListener('mouseleave', () => {
          thumbVid.pause();
          thumbVid.currentTime = 0;
        });
      }

      item.querySelector('.btn-delete-history').addEventListener('click', e => {
        e.stopPropagation();
        confirmHistoryDeletion(j);
      });

      item.querySelector('.btn-share-video')?.addEventListener('click', () => openVideoShare(j.job_id));
      const playBtn = item.querySelector('.btn-play-mini');
      if (playBtn) {
        playBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          openJobDetail(j);
        });
      }

      const dlBtn = item.querySelector('.btn-download');
      if (dlBtn) {
        dlBtn.addEventListener('click', (e) => {
          e.stopPropagation();
        });
      }

      jobsList.appendChild(item);
    });
  }

  // Load session job history
  async function loadJobs() {
    const version = ++jobsLoadVersion;
    clearTimeout(jobsRefreshTimer);
    try {
      const res = await fetch('/api/jobs');
      if (!res.ok) throw new Error('查詢任務狀態失敗');
      const data = await res.json();
      // Ignore an older refresh that finishes after a new submission/refresh.
      if (version !== jobsLoadVersion) return;

      updateRetentionDuration(data.retention_seconds);
      cachedJobs = data.jobs || [];
      if (jobDetail?.open) {
        const current = cachedJobs.find(job => job.job_id === jobDetail.dataset.jobId);
        if (current) {
          const retentionText = detailMeta.querySelector('[data-detail-retention]');
          if (retentionText) retentionText.textContent = jobRetentionNotice(current);
          const expiry = current.retention?.share_expires_at;
          const label = detailMeta.querySelector('[data-detail-share-label]');
          const value = detailMeta.querySelector('[data-detail-share-expiry]');
          if (label && value) {
            label.hidden = value.hidden = !expiry;
            value.textContent = expiry ? `有效至 ${expiryDateTime(expiry)}；停用分享會取消延長保留` : '';
          }
        }
      }
      hasActiveJobs = cachedJobs.some(j => activeJobStatuses.has(j.status));

      const historyCountBadge = document.querySelector('[data-history-count]');
      if (historyCountBadge) {
        const activeCount = cachedJobs.filter(j => activeJobStatuses.has(j.status)).length;
        if (activeCount > 0) {
          historyCountBadge.textContent = activeCount;
          historyCountBadge.hidden = false;
        } else if (cachedJobs.length > 0) {
          historyCountBadge.textContent = cachedJobs.length;
          historyCountBadge.hidden = false;
        } else {
          historyCountBadge.hidden = true;
        }
      }

      renderJobList();
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
      allFonts = (await res.json()).map(font => {
        const localized = { ...font };
        for (const key of ['name_zh', 'style_display', 'artist', 'dynasty_era', 'font_author', 'historical_reference', 'aesthetic_notes', 'license']) {
          if (typeof localized[key] === 'string') localized[key] = fallbackConvert(localized[key], 'trad');
        }
        return localized;
      });
      catalogLoaded = true;
      updateHeaderCounts();
      setupCatalogFilters();
      renderFontGrid();
      restoreSavedStyle();
      // Metadata arrival must not rewrite a draft or overwrite a saved choice.
      applySelectedFont(styleSelect.value, { preserveText: true, persist: false });
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
    const searchInput = document.getElementById("fonts-search") || document.getElementById("search-input");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        activeFilters.search = normalizeFontSearch(e.target.value.trim());
        renderFontGrid();
      });
    }

    document.querySelectorAll("[data-filter] .chip").forEach(pill => {
      pill.addEventListener("click", () => {
        const parentGroup = pill.closest("[data-filter]");
        const filterType = parentGroup ? parentGroup.getAttribute("data-filter") : null;
        const val = pill.getAttribute("data-val");
        if (!filterType) return;

        parentGroup.querySelectorAll(".chip").forEach(p => p.classList.remove("active"));
        pill.classList.add("active");

        if (filterType === "support") {
          activeFilters.char_support = val;
        } else {
          activeFilters[filterType] = val;
        }
        renderFontGrid();
      });
    });
  }

  function renderFontGrid() {
    const grid = document.getElementById("fonts-grid") || document.getElementById("font-grid");
    if (!grid) return;
    grid.innerHTML = "";

    const catalogList = [
      ...Object.values(BUILTIN_FONT_META).filter(f => availableStyleIds.has(f.id)).map(f => getFontMeta(f.id) || f),
      ...allFonts.filter(f => !BUILTIN_FONT_META[f.id])
    ];

    const summaryEl = document.getElementById("fonts-summary");
    if (summaryEl) {
      summaryEl.textContent = `歷代名家書法字庫（共收錄 ${catalogList.length} 款）· 查閱出處與協議，一鍵用於創作。`;
    }

    const filtered = catalogList.filter(f => {
      // 1. Style Category filter
      if (activeFilters.category !== "all") {
        if (activeFilters.category === "kaishu") {
          if (f.style_category !== "kaishu" && f.style_category !== "engine") return false;
        } else if (f.style_category !== activeFilters.category) {
          return false;
        }
      }
      // 2. Char Support filter
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
      // 3. Medium filter
      if (activeFilters.medium !== "all" && f.medium !== activeFilters.medium) {
        return false;
      }
      // 4. Search
      if (activeFilters.search) {
        const s = activeFilters.search;
        const match = [f.name_zh, f.name_en, f.artist, f.style_display, f.historical_reference, f.font_author]
          .some(value => value && normalizeFontSearch(value).includes(s));
        if (!match) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1/-1; text-align: center; padding: 48px; color: var(--muted);">
          未找到符合篩選條件的書法字庫。您可點擊「全部」或調整篩選詞查看歷代名家法帖。
        </div>
      `;
      return;
    }

    filtered.forEach(font => {
      const card = document.createElement("article");
      card.className = "font-card";
      card.dataset.fontId = font.id;

      const isDl = font.is_downloaded === 1;

      let previewText = font.sample_text || "永和九年歲在癸丑";
      if (font.char_support === "simp") {
        previewText = fallbackConvert(previewText, "simp");
      } else {
        previewText = fallbackConvert(previewText, "trad");
      }

      const supportLabel = font.char_support === "trad" ? "繁體支持" : (font.char_support === "simp" ? "簡體優先" : "繁簡兼備");

      card.innerHTML = `
        <div>
          <h3>${font.name_zh}</h3>
          <div class="en">${font.name_en || ''}</div>
        </div>
        <div class="badges">
          <span class="badge accent">${font.style_display}</span>
          <span class="badge">${supportLabel}</span>
          <span class="badge">${font.medium === 'pen' ? '硬筆' : '毛筆'}</span>
          ${isDl ? '<span class="badge accent">✓ 離線可用</span>' : '<span class="badge">典藏收錄</span>'}
        </div>
        <div class="glyph-sample">${fontSampleMarkup(font)}</div>
        <div class="aesthetic">${font.aesthetic_notes || ''}</div>
        <details>
          <summary>出處與協議</summary>
          <dl class="meta-list">
            <dt>名家</dt><dd>${font.artist} · ${font.dynasty_era}</dd>
            <dt>法帖</dt><dd>${font.historical_reference || '歷代名家書道真跡'}</dd>
            <dt>造字</dt><dd>${font.font_author}</dd>
            <dt>協議</dt><dd>${font.license}</dd>
          </dl>
        </details>
        <div class="btn-row">
          ${isDl ? `
            <button type="button" class="btn btn-primary btn-sm btn-use" data-id="${font.id}">
              ✍ 用此字體創作
            </button>
          ` : `
            <span class="btn btn-secondary btn-sm" style="cursor:not-allowed; opacity:0.6;">
              📜 典藏收錄
            </span>
          `}
        </div>
      `;

      const useBtn = card.querySelector(".btn-use");
      if (useBtn) {
        useBtn.addEventListener("click", () => {
          const targetStyleId = font.id === 'mashanzheng-kai' ? 'mashanzheng' : (font.id === 'hanwang-lisu-medium' ? 'lishu hanwang' : (font.id === 'longcang-xingshu' ? 'longcang' : font.id));
          
          if (styleSelect) {
            let optionExists = Array.from(styleSelect.options).some(o => o.value === targetStyleId || o.value === font.id);
            if (!optionExists) {
              const newOpt = document.createElement('option');
              newOpt.value = targetStyleId;
              newOpt.textContent = `${font.name_zh} (${font.name_en || font.id})`;
              styleSelect.appendChild(newOpt);
            }
            styleSelect.value = targetStyleId;
          }

          applySelectedFont(targetStyleId);

          if (font.char_support === "trad" && currentScript !== "trad") {
            performScriptConversion('trad');
          } else if (font.char_support === "simp" && currentScript !== "simp") {
            performScriptConversion('simp');
          }

          location.hash = '#create';
          showStatus(`已選用【${font.name_zh}】，創作臺已就緒`, 'info');
          setTimeout(hideStatus, 2500);
        });
      }

      grid.appendChild(card);
    });
  }


  // =========================================================================
  // Redesigned Workbench Controllers (Router, Canvas Dimension, Font Picker)
  // =========================================================================



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
  function updateRoute(targetHash) {
    const rawHash = (typeof targetHash === 'string' ? targetHash : location.hash) || '';
    const hash = rawHash.replace('#', '') || 'create';
    const view = ['create', 'history', 'fonts'].includes(hash) ? hash : 'create';
    if (document.body.dataset.view && document.body.dataset.view !== view) {
      previewPresentationVersion += 1;
      document.querySelectorAll('.work-dialog[open], #video-share-notice[open]').forEach(closeNotice);
    }
    document.body.dataset.view = view;
    document.querySelectorAll('.view').forEach(v => {
      v.hidden = v.id !== `view-${view}`;
    });
    document.querySelectorAll('[data-nav]').forEach(a => {
      if (a.getAttribute('data-nav') === view) {
        a.setAttribute('aria-current', 'page');
        a.classList.add('active');
      } else {
        a.removeAttribute('aria-current');
        a.classList.remove('active');
      }
    });
    try { if (window.scrollTo && !navigator?.userAgent?.includes('jsdom')) window.scrollTo(0, 0); } catch (_) {}
    if (view === 'create') {
      if (typeof layoutStagePaper === 'function') layoutStagePaper();
      if (typeof fitStage === 'function') fitStage();
    }
    if (view === 'history') loadJobs();
    if (view === 'fonts') renderFontGrid();
  }

  // Bind click navigation for all data-nav and local hash links
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
      const href = a.getAttribute('href');
      if (href && href.startsWith('#')) {
        const targetView = href.slice(1);
        if (['create', 'history', 'fonts'].includes(targetView)) {
          e.preventDefault();
          if (location.hash !== href) {
            location.hash = href;
          }
          updateRoute(targetView);
        }
      }
    });
  });

  window.addEventListener('hashchange', () => updateRoute());
  updateRoute();

  let resizeTimer;
  window.addEventListener('resize', () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => {
      if (typeof layoutStagePaper === 'function') layoutStagePaper();
      // Viewport changes (including mobile browser chrome during scrolling) only
      // scale the displayed paper; the backend canvas and preview pixels are unchanged.
      if (typeof fitStage === 'function') fitStage(false);
    }, 100);
  });

  // Rubbing changes actual artwork pixels; both light themes retain legacy paper.
  // Font/style stays independent of this paper-and-ink selection.
  const themeSelect = document.getElementById('theme-select');
  function selectTheme(theme, { persist = true } = {}) {
    if (!themeIds.includes(theme)) return;
    const nextPalette = theme === 'theme-rubbing' ? 'dark' : 'light';
    const paletteChanged = nextPalette !== artworkPalette;
    artworkPalette = nextPalette;
    document.body.classList.remove(...themeIds);
    document.body.classList.add(theme);
    if (themeSelect) themeSelect.value = theme;
    document.querySelectorAll('.theme-btn').forEach(button => {
      button.classList.toggle('active', button.dataset.theme === theme);
    });
    if (persist) savePreferences({ theme });
    if (paletteChanged) scheduleEditorPreview();
  }
  selectTheme(preferences.theme || 'theme-xuan', { persist: false });
  themeSelect?.addEventListener('change', () => selectTheme(themeSelect.value));
  document.querySelectorAll('.theme-btn').forEach(button => {
    button.addEventListener('click', () => selectTheme(button.dataset.theme));
  });

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
  let pickerActiveSup = 'trad';
  let recentFonts = ['kai'];

  let favoriteFonts = ['kai', 'i-yan-kai', 'tw-sung', 'chill-qiuhong-kai'];
  try {
    const savedFav = localStorage.getItem('calligraphy.favorites');
    if (savedFav) favoriteFonts = JSON.parse(savedFav);
  } catch (_) {}

  function renderRecentFonts() {
    if (!fontRecent) return;
    fontRecent.innerHTML = '';
    recentFonts.slice(0, 5).forEach(id => {
      const f = getFontMeta(id);
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
    const q = pickerSearch ? normalizeFontSearch(pickerSearch.value.trim()) : '';

    const catalogList = [
      ...Object.values(BUILTIN_FONT_META).filter(f => availableStyleIds.has(f.id)).map(f => getFontMeta(f.id) || f),
      ...allFonts.filter(f => !BUILTIN_FONT_META[f.id])
    ];

    const filtered = catalogList.filter(f => {
      if (pickerActiveCat === 'fav') {
        if (!favoriteFonts.includes(f.id)) return false;
      } else if (pickerActiveCat === 'engine') {
        if (f.style_category !== 'engine') return false;
      } else if (pickerActiveCat === 'kaishu') {
        if (f.style_category !== 'kaishu' && f.style_category !== 'engine') return false;
      } else if (pickerActiveCat !== 'all') {
        if (f.style_category !== pickerActiveCat) return false;
      }

      if (pickerActiveSup !== 'all') {
        if (pickerActiveSup === 'trad' && f.char_support !== 'trad' && f.char_support !== 'both') return false;
        if (pickerActiveSup === 'simp' && f.char_support !== 'simp' && f.char_support !== 'both') return false;
      }
      if (q) {
        const hay = normalizeFontSearch([f.name_zh, f.name_en, f.artist, f.style_display, f.historical_reference, f.font_author].filter(Boolean).join(' '));
        if (!hay.includes(q)) return false;
      }
      return true;
    });

    if (filtered.length === 0) {
      const emptyLi = document.createElement('li');
      emptyLi.className = 'picker-empty';
      emptyLi.textContent = '未找到匹配的字體';
      pickerList.appendChild(emptyLi);
      return;
    }

    filtered.forEach(f => {
      const li = document.createElement('li');
      li.className = 'picker-item';
      const targetStyleId = f.id === 'mashanzheng-kai' ? 'mashanzheng' : (f.id === 'hanwang-lisu-medium' ? 'lishu hanwang' : (f.id === 'longcang-xingshu' ? 'longcang' : f.id));
      const isSelected = styleSelect && (styleSelect.value === targetStyleId || styleSelect.value === f.id);
      li.setAttribute('aria-selected', isSelected ? 'true' : 'false');

      const isFav = favoriteFonts.includes(f.id);

      li.innerHTML = `
        <div class="picker-sample">${fontSampleMarkup(f)}</div>
        <div class="picker-info">
          <strong>${f.name_zh}</strong>
          <small>${f.style_display} · ${f.artist} (${f.dynasty_era})</small>
        </div>
        <span class="badge ${f.char_support === 'trad' ? 'accent' : ''}">
          ${f.char_support === 'trad' ? '繁體' : (f.char_support === 'simp' ? '簡體' : '繁簡')}
        </span>
        <button type="button" class="star ${isFav ? 'on' : ''}" title="${isFav ? '取消收藏' : '收藏字體'}" aria-label="收藏">★</button>
      `;

      const starBtn = li.querySelector('.star');
      if (starBtn) {
        starBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          const idx = favoriteFonts.indexOf(f.id);
          if (idx >= 0) {
            favoriteFonts.splice(idx, 1);
            starBtn.classList.remove('on');
          } else {
            favoriteFonts.push(f.id);
            starBtn.classList.add('on');
          }
          try {
            localStorage.setItem('calligraphy.favorites', JSON.stringify(favoriteFonts));
          } catch (_) {}
          if (pickerActiveCat === 'fav') {
            renderPicker();
          }
        });
      }

      li.addEventListener('click', () => {
        if (styleSelect) {
          let opt = Array.from(styleSelect.options).find(o => o.value === targetStyleId || o.value === f.id);
          if (!opt) {
            opt = document.createElement('option');
            opt.value = targetStyleId;
            opt.textContent = `${f.name_zh} (${f.name_en || f.id})`;
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
      if (pickerActiveSup === 'trad') {
        performScriptConversion('trad');
      } else if (pickerActiveSup === 'simp') {
        performScriptConversion('simp');
      }
    });
  }

  // The transparent dialog fills the screen; only its inner panel is content.
  document.querySelectorAll('dialog.sheet').forEach(dialog => {
    dialog.addEventListener('keydown', event => {
      if (event.key === 'Escape') { event.preventDefault(); closeNotice(dialog); return; }
      if (event.key !== 'Tab') return;
      const controls = [...dialog.querySelectorAll('button, a[href], input, select, textarea, video[controls], [tabindex]')]
        .filter(el => !el.disabled && !el.closest('[hidden], .hidden') && el.tabIndex >= 0);
      const first = controls[0], last = controls.at(-1);
      if (!first) { event.preventDefault(); return; }
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) { event.preventDefault(); first.focus(); }
    });
    dialog.addEventListener('close', () => {
      if (!dialog._returnFocus) return;
      if (dialog._returnFocus.isConnected) dialog._returnFocus.focus();
      else document.querySelector('a[data-nav="history"]')?.focus();
    });
    let startedOutside = false;
    dialog.addEventListener('pointerdown', e => {
      startedOutside = e.target === dialog;
    });
    dialog.addEventListener('click', e => {
      if (e.target === dialog && startedOutside) closeNotice(dialog);
      startedOutside = false;
    });
  });

  document.querySelectorAll('dialog [data-close]').forEach(b => {
    b.addEventListener('click', (e) => {
      const d = e.target.closest('dialog');
      if (d) closeNotice(d);
    });
  });

  // Hook applySelectedFont to update font card
  const origApplySelectedFont = applySelectedFont;
  applySelectedFont = function(styleId, options = {}) {
    if (options.persist !== false && styleId && styleSelect.value === styleId) {
      // An explicit picker, recent, catalog or history choice beats late startup
      // metadata, even if the previously saved font has not arrived yet.
      pendingSavedStyle = null;
      savePreferences({ style: styleId });
    }
    origApplySelectedFont(styleId, options);
    const fontMeta = getFontMeta(styleId);
    if (fontCurrentName) fontCurrentName.textContent = fontMeta ? fontMeta.name_zh : getActiveFontDisplayName(styleId);
    if (fontCurrentSub) fontCurrentSub.textContent = fontMeta ? `${fontMeta.style_display} · ${fontMeta.artist} (${fontMeta.dynasty_era})` : '';
    if (fontCurrentGlyph) fontCurrentGlyph.innerHTML = fontSampleMarkup(fontMeta);
    if (fontNote) fontNote.textContent = fontMeta ? (fontMeta.aesthetic_notes || '') : '';
    if (!recentFonts.includes(styleId)) {
      recentFonts = [styleId, ...recentFonts].slice(0, 5);
      renderRecentFonts();
    }
  };

  // Initial loads
  updateCanvasDimDisplay();
  updateText();
  loadStyles();
  loadJobs();
  loadFontDatabase();

  const shareNotice = document.getElementById('video-share-notice');
  const shareCreate = document.getElementById('video-share-create');
  const shareCopy = document.getElementById('video-share-copy');
  const shareRevoke = document.getElementById('video-share-revoke');
  const shareOpen = document.getElementById('video-share-open');
  const shareURL = document.getElementById('video-share-url');
  const shareStatus = document.getElementById('video-share-status');
  let shareJob = null;
  let shareVersion = 0;
  let shareBusy = false;
  let shareChecking = false;
  let shareReady = false;
  let shareActive = false;
  let shareExpiresAt = null;
  const shareLinks = new Map();
  const shareStoragePrefix = 'calligraphy-share:';
  function forgetShareLink(job) {
    shareLinks.delete(job);
    try { sessionStorage.removeItem(shareStoragePrefix + job); } catch (_) { /* Private browsing may deny storage. */ }
  }
  function checkedShareLink(job, data) {
    const url = new URL(data.url, location.origin);
    if (url.origin !== location.origin || url.pathname !== '/watch.html' || url.search ||
        !/^#[A-Za-z0-9_-]+\.[A-Za-z0-9_-]{43}$/.test(url.hash) ||
        url.hash.slice(1).split('.')[0] !== job || !Number.isFinite(data.expires_at) ||
        data.expires_at * 1000 <= Date.now()) throw new Error('分享連結無效或已到期。');
    return { url: url.href, expires_at: data.expires_at };
  }
  function cachedShareLink(job) {
    try {
      const data = shareLinks.get(job) || JSON.parse(sessionStorage.getItem(shareStoragePrefix + job));
      return data ? checkedShareLink(job, data) : null;
    } catch (_) { forgetShareLink(job); return null; }
  }
  function rememberShareLink(job, data) {
    const link = checkedShareLink(job, data);
    shareLinks.set(job, link);
    try { sessionStorage.setItem(shareStoragePrefix + job, JSON.stringify(link)); } catch (_) { /* Reopen still works in memory. */ }
    return link;
  }
  function sharePrivacyNotice() {
    return `任何持有連結的人都能觀看及下載這部影片。分享連結有效至 ${expiryDateTime(shareExpiresAt)}，這部影片至少會保留至此時；你可以隨時停用，取消延長保留。`;
  }
  function updateShareButtons() {
    shareCreate.disabled = shareRevoke.disabled = shareBusy || shareChecking || !shareReady;
    shareCopy.disabled = shareBusy || shareChecking;
    shareCreate.textContent = shareActive ? '取代舊連結（舊連結將失效）' : '建立分享連結';
    shareCreate.classList.toggle('btn-primary', !shareActive);
    shareCreate.classList.toggle('btn-secondary', shareActive);
    shareRevoke.hidden = !shareActive;
  }
  function clearShareLink() {
    shareExpiresAt = null;
    shareURL.value = '';
    shareURL.hidden = shareCopy.hidden = shareOpen.hidden = true;
    shareOpen.removeAttribute('href');
  }
  function showShareLink(link) {
    shareExpiresAt = link.expires_at;
    shareURL.value = link.url;
    shareOpen.href = link.url;
    shareURL.hidden = shareCopy.hidden = shareOpen.hidden = false;
    shareStatus.textContent = `可再次複製原連結；不會延長到期時間。${sharePrivacyNotice()}`;
  }
  async function refreshShareLink() {
    const job = shareJob;
    const version = ++shareVersion;
    shareChecking = true;
    shareReady = false;
    shareActive = false;
    clearShareLink();
    updateShareButtons();
    shareStatus.textContent = '正在檢查現有分享連結…';
    try {
      const cached = cachedShareLink(job);
      const token = cached ? new URL(cached.url).hash.slice(1).split('.')[1] : '';
      const response = await fetch(`/api/jobs/${encodeURIComponent(job)}/share-link/status`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({token}),
      });
      if (!response.ok) {
        if (response.status === 404) forgetShareLink(job);
        throw new Error('無法確認分享狀態，請關閉後重試。');
      }
      const data = await response.json();
      if (version !== shareVersion || !shareNotice.open) return;
      shareReady = true;
      shareActive = data.active === true;
      let validatedLink = null;
      if (shareActive && data.url) {
        validatedLink = rememberShareLink(job, data);
        showShareLink(validatedLink);
      }
      else {
        forgetShareLink(job);
        if (shareActive) {
          shareExpiresAt = data.expires_at;
          shareStatus.textContent = `已有分享連結，有效至 ${new Date(data.expires_at * 1000).toLocaleString()}。此分頁未保留原連結；請使用之前複製的連結，或明確取代。取代後，朋友手上的舊連結會立即失效。`;
        } else shareStatus.textContent = '尚無有效分享連結。建立後才會開放持有連結的人觀看。';
      }
      return validatedLink;
    } catch (error) {
      if (version === shareVersion && shareNotice.open) {
        shareStatus.textContent = error.message;
        // Do not enable an unverified create/replace operation after a failed read.
        return;
      }
    } finally {
      if (version === shareVersion && shareNotice.open) {
        shareChecking = false;
        updateShareButtons();
      }
    }
  }
  function openVideoShare(jobId) {
    shareJob = jobId;
    openNotice(shareNotice);
    refreshShareLink();
  }
  shareNotice.addEventListener('close', () => { shareVersion += 1; shareChecking = false; clearShareLink(); });
  async function changeShareLink(method) {
    if (!shareJob || shareBusy || shareChecking || !shareReady) return;
    const job = shareJob;
    const replacing = shareActive;
    let needsRefresh = false;
    const version = ++shareVersion;
    shareBusy = true;
    updateShareButtons();
    shareStatus.textContent = method === 'POST' ? '正在建立這部影片的分享連結…' : '正在停用分享連結…';
    try {
      const response = await fetch(`/api/jobs/${encodeURIComponent(job)}/share-link`, {
        method, ...(method === 'POST' ? {headers: {'Content-Type': 'application/json'}, body: JSON.stringify({replace: replacing})} : {}),
      });
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '操作失敗，請重試。');
      }
      let link;
      if (method === 'DELETE') forgetShareLink(job);
      else link = rememberShareLink(job, await response.json());
      loadJobs();
      if (version !== shareVersion || !shareNotice.open) return;
      shareActive = method !== 'DELETE';
      clearShareLink();
      if (link) showShareLink(link);
      else shareStatus.textContent = '分享連結已停用。已下載的影片不會被收回。';
    } catch (error) {
      needsRefresh = true;
      if (version === shareVersion && shareNotice.open) shareStatus.textContent = error.message;
    } finally {
      shareBusy = false;
      updateShareButtons();
      // A read in a newly opened dialog may have raced the completed mutation.
      if ((needsRefresh || version !== shareVersion) && shareNotice.open) refreshShareLink();
    }
  }
  shareCreate.addEventListener('click', () => changeShareLink('POST'));
  shareRevoke.addEventListener('click', () => changeShareLink('DELETE'));
  shareCopy.addEventListener('click', async () => {
    if (shareBusy || shareChecking || !shareURL.value) return;
    const job = shareJob;
    const link = await refreshShareLink();
    if (!link || job !== shareJob || !shareNotice.open) return;
    const version = shareVersion;
    try {
      await navigator.clipboard.writeText(link.url);
      if (version === shareVersion) shareStatus.textContent = `影片連結已複製。${sharePrivacyNotice()} 可貼到 Safari／Chrome 觀看。`;
    } catch (_) {
      if (version !== shareVersion) return;
      shareURL.focus(); shareURL.select();
      shareStatus.textContent = `請長按上方已選取的影片連結，選擇「複製」。${sharePrivacyNotice()}`;
    }
  });

  // Recovery is offered at download time, including after the first-visit notice.
  const exportNotice = document.getElementById('video-export-notice');
  const exportCreate = document.getElementById('video-export-create');
  const exportCopy = document.getElementById('video-export-copy');
  const exportRevoke = document.getElementById('video-export-revoke');
  const exportURL = document.getElementById('video-export-url');
  const exportStatus = document.getElementById('video-export-status');
  let exportJob = null;
  let exportVersion = 0;
  let exportBusy = false;
  let exportExpiresAt = null;
  function exportExpiryNotice() {
    return `臨時連結有效至 ${expiryDateTime(exportExpiresAt)}，不延長作品保留期限。任何持有連結的人都能觀看及下載這部影片，請勿轉傳。`;
  }
  exportNotice.addEventListener('close', () => { exportVersion += 1; });

  document.addEventListener('click', event => {
    if (!/MicroMessenger/i.test(navigator.userAgent || '')) return;
    const anchor = event.target.closest('a[href]');
    if (!anchor || anchor.dataset.exportDirect === 'true') return;
    const url = new URL(anchor.href, location.href);
    const match = url.pathname.match(/^\/api\/jobs\/([A-Za-z0-9_-]+)\/download$/);
    if (url.origin !== location.origin || !match) return;
    event.preventDefault();
    event.stopPropagation();
    exportVersion += 1;
    exportJob = match[1];
    exportExpiresAt = null;
    exportURL.value = '';
    exportURL.hidden = true;
    exportCopy.hidden = true;
    exportRevoke.hidden = true;
    exportCreate.disabled = exportBusy;
    exportStatus.textContent = '';
    document.getElementById('video-export-direct').href = anchor.href;
    openNotice(exportNotice);
  }, true);

  exportCreate.addEventListener('click', async () => {
    if (!exportJob || exportBusy) return;
    exportBusy = true;
    const job = exportJob;
    const version = ++exportVersion;
    exportCreate.disabled = true;
    exportCopy.hidden = true;
    exportRevoke.hidden = true;
    exportURL.hidden = true;
    exportURL.value = '';
    exportStatus.textContent = '正在建立這一部影片的下載連結…';
    try {
      const response = await fetch(`/api/jobs/${job}/export-link`, { method: 'POST' });
      const data = await response.json();
      if (version !== exportVersion || !exportNotice.open) return;
      if (!response.ok) throw new Error(data.detail || '無法建立連結，請稍後重試。');
      const url = new URL(data.url, location.origin);
      if (url.origin !== location.origin || url.pathname !== '/export.html' || !Number.isFinite(data.expires_at) || data.expires_at * 1000 <= Date.now()) throw new Error('下載連結無效。');
      exportExpiresAt = data.expires_at;
      exportURL.value = url.href;
      exportURL.hidden = false;
      exportCopy.hidden = false;
      exportRevoke.hidden = false;
      exportStatus.textContent = `${exportExpiryNotice()} 請複製後貼到 Safari／Chrome 網址列，無需重新生成。`;
    } catch (error) {
      if (version === exportVersion && exportNotice.open) exportStatus.textContent = error.message;
    } finally {
      exportBusy = false;
      exportCreate.disabled = false;
    }
  });
  exportCopy.addEventListener('click', async () => {
    const version = exportVersion;
    try {
      await navigator.clipboard.writeText(exportURL.value);
      if (version === exportVersion) exportStatus.textContent = `影片連結已複製。${exportExpiryNotice()} 請手動開啟 Safari／Chrome，貼到網址列後下載。`;
    } catch (_) {
      if (version !== exportVersion) return;
      exportURL.focus();
      exportURL.select();
      exportStatus.textContent = `請長按上方已選取的影片連結，選擇「複製」，再貼到 Safari／Chrome 網址列。${exportExpiryNotice()}`;
    }
  });
  exportRevoke.addEventListener('click', async () => {
    if (exportBusy) return;
    exportBusy = true;
    exportCreate.disabled = true;
    const version = exportVersion;
    exportRevoke.disabled = true;
    try {
      const response = await fetch(`/api/jobs/${exportJob}/export-link`, { method: 'DELETE' });
      if (version !== exportVersion) return;
      if (!response.ok) throw new Error('無法停用連結，請重試；連結仍會自動到期。');
      exportURL.value = '';
      exportURL.hidden = exportCopy.hidden = exportRevoke.hidden = true;
      exportStatus.textContent = '影片連結已停用。';
    } catch (error) {
      if (version === exportVersion) exportStatus.textContent = error.message;
    } finally {
      exportBusy = false;
      exportCreate.disabled = false;
      exportRevoke.disabled = false;
    }
  });

  // An advisory only: UA detection is imperfect, so never block creation/download.
  if (/MicroMessenger/i.test(navigator.userAgent || '')) {
    const notice = document.getElementById('wechat-notice');
    const pageURL = document.getElementById('wechat-page-url');
    const copyStatus = document.getElementById('wechat-copy-status');
    const storageKey = 'calligraphy.wechatNoticeDismissed';
    let dismissed = false;
    try { dismissed = sessionStorage.getItem(storageKey) === '1'; } catch (_) {}
    pageURL.value = location.href;
    notice.addEventListener('close', () => {
      try { sessionStorage.setItem(storageKey, '1'); } catch (_) {}
    });
    document.getElementById('wechat-copy-link').addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(location.href);
        copyStatus.textContent = '網址已複製，請貼到 Safari／Chrome 開啟。';
      } catch (_) {
        pageURL.focus();
        pageURL.select();
        copyStatus.textContent = '請長按上方已選取的網址，選擇「複製」。';
      }
    });
    if (!dismissed) openNotice(notice);
  }
});
