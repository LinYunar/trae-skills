# -*- coding: utf-8 -*-
"""商标注册通过率评估报告生成器：JSON + 模板 -> HTML + PDF。"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "report_template.html"

LEVEL_TAG = {
    "相同": "t-high",
    "含全称": "t-mid",
    "同构四字": "t-mid",
    "同构": "t-mid",
    "核心词": "t-low",
    "前缀": "t-low",
}

BROWSER_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def esc(text):
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def find_browser():
    env = os.environ.get("CHROME_PATH")
    if env and Path(env).exists():
        return env
    for p in BROWSER_CANDIDATES:
        if Path(p).exists():
            return p
    return None


def render_barriers(items):
    rows = []
    for it in items:
        level = it.get("level", "")
        tone = it.get("tone", "c")
        tag = LEVEL_TAG.get(level, "t-low")
        name = esc(it.get("name", ""))
        name_html = f"<strong>{name}</strong>" if tone == "a" else name
        status_cls = it.get("status_cls", "t-reg")
        rows.append(
            '<tr class="lv-%s">\n'
            '          <td><span class="tag %s">%s</span></td>\n'
            '          <td>%s</td>\n'
            '          <td><span class="tag %s">%s</span></td>\n'
            '          <td>%s</td>\n'
            '          <td>%s</td>\n'
            "        </tr>"
            % (tone, tag, esc(level), name_html, status_cls,
               esc(it.get("status", "")), esc(it.get("owner", "")), esc(it.get("impact", "")))
        )
    return "\n        ".join(rows)


def render_items(items):
    rows = []
    for raw in items:
        text = str(raw)
        if "　" in text:
            head, tail = text.split("　", 1)
            rows.append(f"<li><strong>{esc(head)}</strong>&nbsp;&nbsp;{esc(tail)}</li>")
        else:
            rows.append(f"<li>{esc(text)}</li>")
    return "\n          ".join(rows)


def render_actions(items):
    rows = []
    for i, it in enumerate(items, 1):
        rows.append(
            '<tr><td><span class="act-no">%d</span></td>'
            '<td class="act-name">%s</td><td>%s</td></tr>'
            % (i, esc(it.get("name", "")), esc(it.get("desc", "")))
        )
    return "\n        ".join(rows)


def build(data, out_dir):
    data.setdefault("date", date.today().isoformat())
    data.setdefault("report_no", "TR-" + date.today().strftime("%Y%m%d") + "-001")
    data.setdefault("mark_type", "纯文字申请")
    data.setdefault(
        "verdict_lead",
        "结论按申请主体拆分。同一商标由不同主体申报，通过率相差一个量级，不能合并为单一数值。",
    )

    b_min = int(data.get("rate_b_min", 70))
    b_max = int(data.get("rate_b_max", 85))
    width = max(1, b_max - b_min)
    b_mid = data.get("rate_b_mid", (b_min + b_max) // 2)

    repl = {
        "{{MARK_NAME}}": esc(data.get("mark_name", "")),
        "{{CLASS_ID}}": esc(data.get("class_id", "")),
        "{{MARK_TYPE}}": esc(data.get("mark_type", "")),
        "{{REPORT_NO}}": esc(data.get("report_no", "")),
        "{{DATE}}": esc(data.get("date", "")),
        "{{COMPANY}}": esc(data.get("company", "")),
        "{{VERDICT_LEAD}}": esc(data.get("verdict_lead", "")),
        "{{RATE_A}}": esc(data.get("rate_a", "")),
        "{{RATE_A_PCT}}": str(int(data.get("rate_a_pct", 5))),
        "{{VERDICT_A_TEXT}}": esc(data.get("verdict_a_text", "")),
        "{{RATE_B}}": esc(data.get("rate_b", "")),
        "{{RATE_B_MIN}}": str(b_min),
        "{{RATE_B_MAX}}": str(b_max),
        "{{RATE_B_WIDTH}}": str(width),
        "{{RATE_B_MID}}": str(b_mid),
        "{{VERDICT_B_TEXT}}": esc(data.get("verdict_b_text", "")),
        "{{RATE_NOTE}}": esc(data.get("rate_note", "")),
        "{{BARRIER_ROWS}}": render_barriers(data.get("barriers", [])),
        "{{BARRIER_NOTE}}": esc(data.get("barrier_note", "")),
        "{{WEIGHT_ITEMS}}": render_items(data.get("weights", [])),
        "{{CALIB_ITEMS}}": render_items(data.get("calibrations", [])),
        "{{ACTION_ROWS}}": render_actions(data.get("actions", [])),
        "{{BOUNDARY}}": esc(data.get(
            "boundary",
            "评估边界：基于公开数据快照，不含审查内档、图形比对与类似群判定，不构成注册承诺，以商标局结论为准。")),
        "{{FOOTER_TITLE}}": "商标注册通过率评估 · %s 第 %s 类"
        % (data.get("mark_name", ""), data.get("class_id", "")),
    }

    html = TEMPLATE.read_text(encoding="utf-8")
    for k, v in repl.items():
        html = html.replace(k, v)

    left = re.findall(r"{{[A-Z_]+}}", html)
    if left:
        raise SystemExit("模板仍有未替换占位符：%s" % ", ".join(sorted(set(left))))

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = "商标注册通过率评估-%s-%s类" % (data.get("mark_name", "商标"), data.get("class_id", ""))
    html_path = out_dir / (stem + ".html")
    html_path.write_text(html, encoding="utf-8")

    pdf_path = out_dir / (stem + ".pdf")
    browser = find_browser()
    if not browser:
        print("未找到 Chrome 或 Edge，已跳过 PDF。可设置环境变量 CHROME_PATH。")
        return html_path, None

    profile = tempfile.mkdtemp(prefix="trademark_pdf_")
    try:
        cmd = [
            browser, "--headless=new", "--no-sandbox", "--disable-gpu",
            "--user-data-dir=" + profile,
            "--print-to-pdf=" + str(pdf_path),
            "--no-pdf-header-footer",
            html_path.as_uri(),
        ]
        subprocess.run(cmd, capture_output=True, timeout=90)
        if not pdf_path.exists():
            print("PDF 生成失败，HTML 已输出。")
            return html_path, None
        raw = pdf_path.read_bytes()
        pages = len(re.findall(rb"/Type\s*/Page[^s]", raw))
        if pages != 1:
            print("警告：PDF 为 %d 页，内容超出单页，请精简障碍行或说明文字。" % pages)
    finally:
        shutil.rmtree(profile, ignore_errors=True)

    return html_path, pdf_path


def main():
    ap = argparse.ArgumentParser(description="生成商标注册通过率评估报告")
    ap.add_argument("--data", required=True, help="评估数据 JSON 路径")
    ap.add_argument("--out", required=True, help="输出目录")
    args = ap.parse_args()

    payload = json.loads(Path(args.data).read_text(encoding="utf-8"))
    html_path, pdf_path = build(payload, args.out)
    print("HTML:", html_path)
    if pdf_path:
        print("PDF:", pdf_path)


if __name__ == "__main__":
    main()
