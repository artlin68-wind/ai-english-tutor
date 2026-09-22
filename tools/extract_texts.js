/* extract_texts.js — 從 index.html 的固定資料結構 + words.json 收集
 * 「會被念出來的固定英文」,輸出 tools/_texts.json 給 gen_tts.py 預生成 mp3。
 *
 * 收集來源:
 *   - words.json        每個字的 en(單字)、exEn(例句)        → normal
 *   - SCENARIOS         每個 turn 的 t(老師台詞,含 byLevel)   → normal
 *   - PRACTICE_SENTENCES 每句 en(跟讀練習)                     → normal + slow(0.55)
 *   - QUIZ_BANK         每題正解選項 opts[a]                     → normal
 *   - 少數固定台詞(老師自我介紹、語速試聽)                     → normal
 *
 * 用法:node tools/extract_texts.js
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.dirname(__dirname);
const html = fs.readFileSync(path.join(ROOT, 'index.html'), 'utf8');

// 取 `const NAME=` 後、字串感知的平衡大括號區塊,eval 成 JS 物件
function extractConst(name) {
  const marker = 'const ' + name + '=';
  const i = html.indexOf(marker);
  if (i < 0) throw new Error('找不到 ' + name);
  let j = html.indexOf('{', i);
  const start = j;
  let depth = 0, inStr = false, q = '', esc = false;
  for (; j < html.length; j++) {
    const c = html[j];
    if (inStr) {
      if (esc) { esc = false; }
      else if (c === '\\') { esc = true; }
      else if (c === q) { inStr = false; }
      continue;
    }
    if (c === '"' || c === "'" || c === '`') { inStr = true; q = c; continue; }
    if (c === '{') depth++;
    else if (c === '}') { depth--; if (depth === 0) { j++; break; } }
  }
  const literal = html.slice(start, j);
  // eslint-disable-next-line no-eval
  return eval('(' + literal + ')');
}

const normal = new Set();
const slow = new Set();
function addN(t) { if (t && typeof t === 'string' && /[A-Za-z]/.test(t)) normal.add(t.trim()); }
function addS(t) { if (t && typeof t === 'string' && /[A-Za-z]/.test(t)) slow.add(t.trim()); }

// --- words.json ---
try {
  const wj = JSON.parse(fs.readFileSync(path.join(ROOT, 'words.json'), 'utf8'));
  const groups = wj.words || {};
  for (const lv of Object.keys(groups)) {
    for (const w of groups[lv]) { addN(w.en); addN(w.exEn); }
  }
} catch (e) { console.error('words.json 讀取失敗:', e.message); }

// --- SCENARIOS:收集所有 turn.t ---
const SCENARIOS = extractConst('SCENARIOS');
function walkTurns(arr) { if (Array.isArray(arr)) for (const t of arr) if (t && t.t) addN(t.t); }
for (const key of Object.keys(SCENARIOS)) {
  const sc = SCENARIOS[key];
  walkTurns(sc.turns);
  if (sc.byLevel) for (const lv of Object.keys(sc.byLevel)) walkTurns(sc.byLevel[lv]);
}

// --- PRACTICE_SENTENCES:en(normal + slow) ---
const PRACTICE = extractConst('PRACTICE_SENTENCES');
for (const lv of Object.keys(PRACTICE)) for (const s of PRACTICE[lv]) { addN(s.en); addS(s.en); }

// --- QUIZ_BANK:正解選項 ---
const QUIZ = extractConst('QUIZ_BANK');
for (const lv of Object.keys(QUIZ)) for (const it of QUIZ[lv]) {
  if (Array.isArray(it.opts) && typeof it.a === 'number') addN(it.opts[it.a]);
}

// --- 固定台詞 ---
[
  "Hi, I'm Ryan. Let's practice English together!",
  "Hello, I'm Emma. Nice to meet you!",
  "Hi! This is my speaking speed. Does it feel comfortable for you?",
].forEach(addN);

const out = { normal: [...normal], slow: [...slow] };
fs.writeFileSync(path.join(__dirname, '_texts.json'), JSON.stringify(out, null, 0), 'utf8');
console.log('normal:', out.normal.length, '| slow:', out.slow.length,
  '| 合計唯一句(含重疊):', new Set([...normal, ...slow]).size);
