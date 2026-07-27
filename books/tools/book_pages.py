#!/usr/bin/env python3
"""目次ページと索引ページを生成し、PDF にしおりを付ける。

`books/tools/build_pdf.sh` から呼ばれる。単体では次のように使う。

    book_pages.py toc                       # 目次を生成（ページ番号なし）
    book_pages.py toc    --pdf FILE         # 目次を生成（ページ番号あり）
    book_pages.py index  --pdf FILE         # 索引を生成（ページ番号あり）
    book_pages.py starts --pdf FILE         # 各章の開始ページを JSON で出す
    book_pages.py bookmarks --pdf FILE      # しおりを注入（pikepdf が要る）

ページ番号は PDF から実測する。mdBook にページの概念はないので、これ以外に
知る方法がない（`build_pdf.sh` が2パス構成になっているのはこのため）。
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BOOKS = Path(__file__).resolve().parent.parent
SRC = BOOKS / "lune-book" / "src"
TOC_PATH = SRC / "00-toc.md"
INDEX_PATH = SRC / "zz-index.md"


# --- SUMMARY.md ---------------------------------------------------------------

def read_summary() -> list[dict]:
    """SUMMARY.md を「部の見出し」と「項目」の並びに読み替える。"""
    entries: list[dict] = []
    for line in (SRC / "SUMMARY.md").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# ") and line != "# Summary":
            entries.append({"kind": "part", "title": line[2:].strip()})
            continue
        m = re.match(r'^-?\s*\[([^\]]+)\]\(([0-9a-z-]+\.md)\)$', line)
        if not m:
            continue
        title, href = m.group(1), m.group(2)
        # 表紙・目次・索引は目次に載せない（自分自身と前付け）
        if href in {"00-cover.md", "00-toc.md"}:
            continue
        entries.append({"kind": "item", "title": title, "href": href,
                        "numbered": line.startswith("-")})
    return entries


# --- PDF の実測 ---------------------------------------------------------------

def page_texts(pdf: Path) -> list[str]:
    """1ページ1要素のテキスト。pdftotext が要る。"""
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"],
                         capture_output=True, text=True, check=True).stdout
    # pdftotext はページ区切りに \f を入れる
    pages = out.split("\f")
    return pages[:-1] if pages and not pages[-1].strip() else pages


def heading_of(href: str) -> str:
    """その節の h1 見出し（PDF 上の見出し行と照合するため）。"""
    text = (SRC / href).read_text(encoding="utf-8")
    m = re.search(r'^#\s+(.+)$', text, re.M)
    return m.group(1).strip() if m else href


def measure_starts(pdf: Path) -> dict[str, int]:
    """各節が始まるページ番号（1 始まり）。

    判定は「そのページの最初の非空行が h1 見出しと一致すること」。ゆるく
    「ページ内に見出しが含まれるか」で探すと**目次ページが全章のタイトルを
    持っている**ので、どの章も目次のページ番号になってしまう。実際に一度
    そうなった。
    """
    pages = page_texts(pdf)
    # 長い章題は紙面で2行に折り返される（「第9章 命令的に書く — var・while・for・」
    # / 「IO」のように）。先頭2行をつないでから前方一致で見る。
    heads = []
    for p in pages:
        lines = [ln.strip() for ln in p.splitlines() if ln.strip()][:2]
        heads.append(re.sub(r'\s+', '', "".join(lines)))
    starts: dict[str, int] = {}
    for e in read_summary():
        if e["kind"] != "item":
            continue
        needle = re.sub(r'\s+', '', heading_of(e["href"]))
        for i, head in enumerate(heads, start=1):
            if head.startswith(needle):
                starts[e["href"]] = i
                break
    return starts


# --- 目次 ---------------------------------------------------------------------

def emit_toc(starts: dict[str, int] | None) -> str:
    lines = ["# 目次", ""]
    if starts:
        lines += ["| | | |", "| --- | --- | ---: |"]
    else:
        lines += ["| | |", "| --- | --- |"]
    n = 0
    for e in read_summary():
        if e["kind"] == "part":
            cells = [f"**{e['title']}**", "", ""] if starts else [f"**{e['title']}**", ""]
            lines.append("| " + " | ".join(cells) + " |")
            continue
        label = ""
        if e["numbered"]:
            n += 1
            label = f"第{n}章"
        link = f"[{e['title']}]({e['href']})"
        if starts:
            page = starts.get(e["href"])
            lines.append(f"| {label} | {link} | {page if page else ''} |")
        else:
            lines.append(f"| {label} | {link} |")
    lines += ["", "<div class=\"toc-note\">",
              "",
              "章の中の節までは載せていません。HTML 版では左の目次から、"
              "PDF 版ではしおりからたどれます。",
              "", "</div>", ""]
    return "\n".join(lines)


# --- 索引 ---------------------------------------------------------------------

# 索引語は人が選ぶ。自動抽出だと「診断」のような頻出語が並んで役に立たないため。
# (見出し語, 探す表記のリスト) の形。表記は完全一致で数える。
CONCEPTS: list[tuple[str, list[str]]] = [
    ("値と型", []),
    ("Int（任意精度）", ["任意精度"]),
    ("Double", ["Double"]),
    ("String", ["String"]),
    ("Bool", ["Bool"]),
    ("Unit", ["Unit"]),
    ("Nothing", ["Nothing"]),
    ("タプル", ["タプル"]),
    ("型注釈", ["型注釈"]),
    ("局所型推論", ["局所型推論", "期待型"]),
    ("型変数", ["型変数"]),
    ("遅延評価", []),
    ("遅延評価", ["遅延評価"]),
    ("サンク", ["サンク"]),
    ("メモ化", ["メモ化"]),
    ("正格", ["strict let", "正格引数"]),
    ("force", ["force"]),
    ("deepForce", ["deepForce"]),
    ("seq", ["seq"]),
    ("無限リスト", ["無限リスト"]),
    ("ストリーム", ["ストリーム"]),
    ("関数", []),
    ("部分適用", ["部分適用"]),
    ("カリー化", ["カリー化"]),
    ("高階関数", ["高階関数"]),
    ("ラムダ", ["ラムダ"]),
    ("パイプライン", ["パイプライン", "|>"]),
    ("再帰", ["再帰関数"]),
    ("データと分岐", []),
    ("代数的データ型", ["代数的データ型", "ADT"]),
    ("パターンマッチ", ["パターンマッチ"]),
    ("網羅性", ["網羅性", "網羅的"]),
    ("反駁不能パターン", ["反駁不能", "反駁可能"]),
    ("レコード", ["レコード"]),
    ("Option", ["Option"]),
    ("Result", ["Result"]),
    ("null 安全", []),
    ("null 安全", ["null 安全"]),
    ("ナローイング", ["ナローイング", "絞り込"]),
    ("null 合体演算子", ["??"]),
    ("セーフナビゲーション", ["?."]),
    ("演算子", []),
    ("床除算", ["床除算", "//"]),
    ("複合代入", ["複合代入"]),
    ("短絡評価", ["短絡"]),
    ("命令的な機能", []),
    ("var", ["var "]),
    ("while", ["while"]),
    ("for", ["for "]),
    ("IO", ["IO:"]),
    ("モジュール", ["モジュール"]),
    ("道具と診断", []),
    ("診断コード", ["診断コード"]),
    ("explain", ["lune explain", ":explain"]),
    ("fmt", ["lune fmt"]),
    ("fix", ["lune fix"]),
    ("REPL", ["REPL"]),
    (":thunks", [":thunks"]),
    (":trace", [":trace"]),
    ("Playground", ["Playground"]),
]

MAX_PAGES = 8          # 1 語あたりに載せるページ数の上限
TOO_COMMON = 40        # これより多くのページに出る語は、見出しに出るページだけ載せる


def emit_index(pdf: Path) -> str:
    pages = page_texts(pdf)
    flat = [re.sub(r'[ \t]+', ' ', p) for p in pages]
    # 見出し行（章題・節題）だけを集めたページごとのテキスト
    heads = []
    for p in flat:
        hs = [ln.strip() for ln in p.splitlines()
              if re.match(r'^\s*(序章|第\d+章|付録[A-E]|\d+\.\d+ |目次|索引)', ln.strip())]
        heads.append("\n".join(hs))

    # 前付けと索引自身は対象から外す。
    #  - 目次は本文の語を大量に含むので、入れると索引が目次のページで埋まる
    #  - 表紙は副題に「遅延評価」を含むので、その語が p.1 を指してしまう
    #  - 索引以降は索引自身
    starts = measure_starts(pdf)
    skip = {1}                              # 表紙
    idx = starts.get("zz-index.md")
    if idx:
        skip |= set(range(idx, len(flat) + 1))
    for i, p in enumerate(flat, start=1):
        first = next((ln.strip() for ln in p.splitlines() if ln.strip()), "")
        if first == "目次":
            skip.add(i)

    lines = ["# 索引", "",
             "本文と付録に現れる主な用語です。ページ番号は PDF 版のものです"
             "（HTML 版では上の検索が使えます）。", ""]
    for label, needles in CONCEPTS:
        if not needles:                    # 分類の見出し
            lines += ["", f"**{label}**", ""]
            continue
        hits = sorted({i for i in range(1, len(flat) + 1)
                       if i not in skip
                       for nd in needles if nd in flat[i - 1]})
        if not hits:
            continue
        if len(hits) > TOO_COMMON:
            in_head = sorted({i for i in range(1, len(flat) + 1)
                              if i not in skip
                              for nd in needles if nd in heads[i - 1]})
            hits = in_head or hits[:MAX_PAGES]
        shown = hits[:MAX_PAGES]
        more = "…" if len(hits) > len(shown) else ""
        lines.append(f"- {label} … {', '.join(str(p) for p in shown)}{more}")
    lines += ["", "付録B（標準ライブラリ）・付録C（診断コード）・"
              "付録D（CLI と REPL）は、それぞれの一覧そのものが索引として使えます。", ""]
    return "\n".join(lines)


# --- しおり -------------------------------------------------------------------

def inject_bookmarks(pdf: Path, starts: dict[str, int]) -> bool:
    try:
        import pikepdf
    except ImportError:
        return False
    titles = {e["href"]: e["title"] for e in read_summary() if e["kind"] == "item"}
    order = [e["href"] for e in read_summary() if e["kind"] == "item"]
    with pikepdf.open(pdf, allow_overwriting_input=True) as doc:
        with doc.open_outline() as outline:
            outline.root.clear()
            outline.root.append(pikepdf.OutlineItem("表紙", 0))
            for href in order:
                page = starts.get(href)
                if page is None:
                    continue
                outline.root.append(pikepdf.OutlineItem(titles[href], page - 1))
        doc.save()
    return True


# --- CLI ----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=("toc", "index", "starts", "bookmarks"))
    ap.add_argument("--pdf", type=Path)
    args = ap.parse_args(argv)

    if args.command == "toc":
        starts = measure_starts(args.pdf) if args.pdf else None
        TOC_PATH.write_text(emit_toc(starts) + "\n", encoding="utf-8")
        print(f"{TOC_PATH.name}: 生成 ({'ページ番号あり' if starts else 'ページ番号なし'})")
        return 0

    if args.command == "index":
        if not args.pdf:
            ap.error("index には --pdf が要る")
        INDEX_PATH.write_text(emit_index(args.pdf) + "\n", encoding="utf-8")
        print(f"{INDEX_PATH.name}: 生成")
        return 0

    if args.command == "starts":
        if not args.pdf:
            ap.error("starts には --pdf が要る")
        print(json.dumps(measure_starts(args.pdf), ensure_ascii=False, indent=1))
        return 0

    if args.command == "bookmarks":
        if not args.pdf:
            ap.error("bookmarks には --pdf が要る")
        ok = inject_bookmarks(args.pdf, measure_starts(args.pdf))
        print("しおり: 注入" if ok else "しおり: 省略 (pikepdf がない)")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
