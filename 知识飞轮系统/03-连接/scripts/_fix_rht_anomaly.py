#!/usr/bin/env python3
# 修复 3 张 R-HT 异常卡（实为 R-HT-249/250/251，撞号重编为 R-HT-255/256/257）：
#   1) 补 card_type: 实务规则卡 (+ card_type_inferred: true，标注为判定型)
#   2) 反向补 consumed_by（双向链接）：指向 合同审查工作流 + 合同风险实务规则卡接驳清册
# 幂等：已有 card_type / consumed_by 则跳过。
import sys, re
from pathlib import Path

LAWKB = Path("/Users/chenyouqiang/Documents/LawKB")

FILES = {
    "R-HT-249": LAWKB / "知识飞轮系统/06-沉淀/裁判规则库/合同风险/R-HT-249-学校食堂委托管理服务合同食安合规与转包红线.md",
    "R-HT-250": LAWKB / "知识飞轮系统/06-沉淀/裁判规则库/合同风险/R-HT-250-网络推广服务合同分包禁止与效果举证风险.md",
    "R-HT-251": LAWKB / "知识飞轮系统/06-沉淀/裁判规则库/合同风险/R-HT-251-增资入股先确权后出资与回购连带保证.md",
}

CONSUMED_BY = [
    "合同审查工作流",
    "合同风险实务规则卡接驳清册",
]

def split_fm(text):
    if not text.startswith("---"):
        return None
    # 找第二个 ---
    m = re.search(r"\n---\n", text)
    if not m:
        return None
    fm = text[3:m.start()]          # 首个---之后到第二个---之前
    body = text[m.end():]
    return fm, body

def process(path, dry):
    raw = path.read_text(encoding="utf-8")
    sp = split_fm(raw)
    if sp is None:
        print(f"⚠️  {path.name}: 无法解析 frontmatter，跳过")
        return "skip"
    fm, body = sp
    lines = fm.splitlines()
    changed = []

    # 1) card_type
    has_ct = any(l.startswith("card_type:") or l.startswith("card_type_inferred:") for l in lines)
    if not has_ct:
        # 插在 domain 行之后，若无 domain 则插在开头
        out = []
        inserted = False
        for l in lines:
            out.append(l)
            if not inserted and l.startswith("domain:"):
                out.append("card_type: 实务规则卡")
                out.append("card_type_inferred: true")
                inserted = True
        if not inserted:
            out = ["card_type: 实务规则卡", "card_type_inferred: true"] + out
        lines = out
        changed.append("card_type")

    # 2) consumed_by（块列表，插在末尾闭合前）
    cb_existing = [l for l in lines if l.startswith("consumed_by:")]
    if not cb_existing:
        # 去除末尾空行
        while lines and lines[-1].strip() == "":
            lines.pop()
        lines.append("consumed_by:")
        for c in CONSUMED_BY:
            lines.append(f"  - {c}")
        changed.append("consumed_by")

    if not changed:
        return "noop"

    if dry:
        print(f"🔍 {path.name}: 将补 → {', '.join(changed)}")
        return "dry"

    new_fm = "\n".join(lines)
    new_text = "---\n" + new_fm + "\n---\n" + body
    path.write_text(new_text, encoding="utf-8")
    print(f"✅ {path.name}: 已补 → {', '.join(changed)}")
    return "done"

if __name__ == "__main__":
    dry = "--dry" in sys.argv
    print("=== DRY-RUN ===" if dry else "=== 正式写入 ===")
    for rid, p in FILES.items():
        if not p.is_file():
            print(f"❌ {rid}: 文件缺失 {p}")
            continue
        process(p, dry)
