#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_tts.py — 為「固定會被念出來的英文」預先合成神經語音 mp3(edge-tts),
打包進 App,執行時直接播本地檔 → 又順又即時(不必連網、不吃 API 額度)。

來源:tools/extract_texts.js 產出的 tools/_texts.json(normal[] / slow[])。
語音:Emma=en-US-EmmaNeural(女)、Ryan=en-US-AndrewNeural(年輕男)。
輸出:
  audio/tts/<voice>/<hash>.mp3          正常語速
  audio/tts/<voice>/slow/<hash>.mp3     慢速(跟讀練習用)
  audio/tts/manifest.json               {voices, normal:[hash...], slow:[hash...]}
hash:FNV-1a 32-bit(與 index.html 內 ttsHash() 完全一致,故檔名對得上)。

特性:斷點續跑(已存在跳過)、進度輸出。
用法:
  node tools/extract_texts.js          # 先產生 _texts.json
  python tools/gen_tts.py              # 再合成
  python tools/gen_tts.py --limit 20   # 測試少量
"""
import argparse
import asyncio
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEXTS = os.path.join(ROOT, "tools", "_texts.json")
OUTDIR = os.path.join(ROOT, "audio", "tts")

VOICES = {"emma": "en-US-EmmaNeural", "ryan": "en-US-AndrewNeural"}
SLOW_RATE = "-40%"

try:
    import edge_tts
except ImportError:
    sys.exit("缺少 edge-tts,請先執行:pip install edge-tts")


def tts_hash(s: str) -> str:
    """FNV-1a 32-bit → 8 位十六進位。務必與 index.html 的 ttsHash() 一致。"""
    h = 2166136261
    for ch in s:
        h ^= ord(ch) & 0xFFFF          # 對應 JS charCodeAt(UTF-16 code unit)
        h = (h * 16777619) & 0xFFFFFFFF
    return format(h, "08x")


async def synth(text, dest, voice, rate="+0%"):
    if os.path.exists(dest) and os.path.getsize(dest) > 400:
        return "skip"
    tmp = dest + ".part"
    try:
        await edge_tts.Communicate(text, voice, rate=rate).save(tmp)
        if os.path.exists(tmp) and os.path.getsize(tmp) > 400:
            os.replace(tmp, dest)
            return "ok"
    except Exception as ex:
        print(f"  ! 失敗 {text[:24]!r}: {ex}", flush=True)
    if os.path.exists(tmp):
        try:
            os.remove(tmp)
        except OSError:
            pass
    return "fail"


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int)
    ap.add_argument("--concurrency", type=int, default=8)
    args = ap.parse_args()

    data = json.load(open(TEXTS, encoding="utf-8"))
    normal = data["normal"][: args.limit] if args.limit else data["normal"]
    slow = data["slow"][: args.limit] if args.limit else data["slow"]

    # 建資料夾
    for v in VOICES:
        os.makedirs(os.path.join(OUTDIR, v, "slow"), exist_ok=True)

    # 任務清單:(text, dest, voice, rate)
    tasks = []
    for v, vname in VOICES.items():
        for t in normal:
            tasks.append((t, os.path.join(OUTDIR, v, tts_hash(t) + ".mp3"), vname, "+0%"))
        for t in slow:
            tasks.append((t, os.path.join(OUTDIR, v, "slow", tts_hash(t) + ".mp3"), vname, SLOW_RATE))

    sem = asyncio.Semaphore(args.concurrency)
    stats = {"ok": 0, "skip": 0, "fail": 0, "n": 0}
    total = len(tasks)

    async def run(t, dest, voice, rate):
        async with sem:
            r = await synth(t, dest, voice, rate)
            stats[r] += 1
            stats["n"] += 1
            if stats["n"] % 100 == 0:
                print(f"  {stats['n']}/{total}  ok={stats['ok']} skip={stats['skip']} fail={stats['fail']}", flush=True)

    await asyncio.gather(*(run(*t) for t in tasks))

    # manifest(hash 與語音無關,兩個語音都會產)
    manifest = {
        "voices": {"female": "emma", "male": "ryan"},
        "slowRate": SLOW_RATE,
        "normal": sorted({tts_hash(t) for t in normal}),
        "slow": sorted({tts_hash(t) for t in slow}),
    }
    json.dump(manifest, open(os.path.join(OUTDIR, "manifest.json"), "w", encoding="utf-8"),
              ensure_ascii=False)
    print(f"完成:ok={stats['ok']} skip={stats['skip']} fail={stats['fail']} | "
          f"manifest: normal={len(manifest['normal'])} slow={len(manifest['slow'])}")


if __name__ == "__main__":
    asyncio.run(main())
