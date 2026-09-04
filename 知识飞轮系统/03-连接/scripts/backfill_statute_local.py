# -*- coding: utf-8 -*-
"""
把 15 张卡里「待回源」的**民法典条文**升级为「已核填」（本地民法典全文，免费）。
非民法典条目（司法解释 / 规章 / 复函）保留待回源，绝不凭记忆编。

用法：dry-run（默认）→ --apply
"""
import re, os, sys, shutil, time

FW = "/Users/chenyouqiang/Documents/LawKB/"
MF = FW + "法律法规库/通用实体法/中华人民共和国民法典（全文）.md"
MF_REL = "本地·法律法规库/通用实体法/中华人民共和国民法典（全文）.md"

CN = "零一二三四五六七八九"


def num2cn(n):
    if n < 10:
        return CN[n]
    if n < 20:
        return ("十" + CN[n % 10]) if n % 10 else "十"
    if n < 100:
        s = CN[n // 10] + "十"
        return s + (CN[n % 10] if n % 10 else "")
    if n < 1000:
        s = CN[n // 100] + "百"
        r = n % 100
        if r == 0:
            return s
        if r < 10:
            return s + "零" + CN[r]
        if r < 20:
            return s + "一十" + (CN[r % 10] if r % 10 else "")
        s += CN[r // 10] + "十"
        return s + (CN[r % 10] if r % 10 else "")
    s = CN[n // 1000] + "千"
    r = n % 1000
    if r == 0:
        return s
    if r < 100:
        s += "零"
    return s + num2cn(r)


lines = open(MF, encoding="utf-8").read().split("\n")
pat = re.compile(r"^(第[零一二三四五六七八九十百千]+条)([　\s]*)")
idx, cur = {}, None
for i, ln in enumerate(lines):
    m = pat.match(ln)
    if m:
        if cur:
            idx[cur] = (idx[cur][0], i)
        cur = m.group(1)
        idx[cur] = (i, i + 1)
if cur:
    idx[cur] = (idx[cur][0], len(lines))


def get_article(n):
    """返回 (标题key, 正文, 行号范围字符串) 或 None"""
    key = "第%s条" % num2cn(n)
    if key not in idx:
        return None
    s, e = idx[key]
    body = "\n".join(lines[s:e]).strip()
    # 正文：去掉行首重复的条号
    body = re.sub(r"^" + re.escape(key) + r"[　\s]*", "", body)
    return key, body, "%d-%d" % (s + 1, e)


# 卡片 -> 需核填的民法典条号
PLAN = {
    "合同风险/R-HT-181-合同订立的成立要素与风险防范.md": {
        "nums": [144, 146, 147, 148, 149, 150, 151, 153, 154],
        "drop_lines": ["《民法典》第一百四十四条、第一百四十六条、第一百五十三条、第一百五十四条、第一百四十七条至第一百五十一条"],
    },
    "合同风险/R-HT-182-技术开发合同十大避坑要点.md": {
        "nums": [855, 857, 563],
        "drop_lines": ["《中华人民共和国民法典》第八百五十五条（合作开发合同当事人的义务）、第八百五十七条（申请专利的权利归属的约定优先）、第五百六十三条各项完整条文"],
    },
    "合同风险/R-HT-183-保理合同的性质认定与穿透审查.md": {
        "nums": list(range(762, 770)),
        "drop_lines": ["《中华人民共和国民法典》第七百六十二条至第七百六十九条"],
    },
    "合同风险/R-HT-184-承揽合同的认定与风险防范.md": {
        "nums": [782, 784, 786, 796],
        "drop_lines": ["《中华人民共和国民法典》第七百八十二条"],
    },
    "合同风险/R-HT-186-以物抵债协议的性质与履行.md": {
        "nums": [401, 428, 538, 539, 540, 541],
        "drop_lines": ["《中华人民共和国民法典》第四百零一条（流押条款的效力）、第四百二十八条（流质条款的效力）",
                       "《中华人民共和国民法典》第五百三十八条至第五百四十一条（债权人撤销权）"],
    },
    "合同风险/R-HT-187-车辆挂靠经营的对外责任承担.md": {
        "nums": [563],
        "drop_lines": ["《中华人民共和国民法典》第五百六十三条各项完整条文"],
    },
}

APPLY = "--apply" in sys.argv
BASE = FW + "知识飞轮系统/06-沉淀/裁判规则库/"

for rel, cfg in PLAN.items():
    path = BASE + rel
    if not os.path.exists(path):
        print("❌ 不存在:", rel)
        continue
    txt = open(path, encoding="utf-8").read()
    orig = txt

    # ⭐ 幂等护栏（行号切块，比正则稳）：先剥离全部旧块，再统一插入一次
    MARK = "**已核填补充（本地民法典全文"
    _ls = txt.split("\n")
    _start = None
    for _i, _l in enumerate(_ls):
        if _l.startswith(MARK):
            _start = _i
            break
    if _start is not None:
        _end = len(_ls)
        for _j in range(_start + 1, len(_ls)):
            if _ls[_j].startswith("## ") or _ls[_j].startswith("**待回源"):
                _end = _j
                break
        while _end > _start and _ls[_end - 1].strip() == "":
            _end -= 1
        del _ls[_start:_end]
        txt = "\n".join(_ls)

    blocks, ok, bad = [], [], []
    for n in cfg["nums"]:
        g = get_article(n)
        if not g:
            bad.append(n)
            continue
        key, body, ln = g
        blk = "\n**《中华人民共和国民法典》%s**（本地全文核填）\n\n> %s　%s\n\n*效力状态：现行有效（%s:%s）*\n" % (
            key, key, body.replace("\n", "\n> "), MF_REL, ln)
        blocks.append(blk)
        ok.append(key)

    if not blocks:
        print("⚠️ 无条文可填:", rel)
        continue

    # 1) 删除待回源块中已被本地覆盖的行
    new_lines = []
    for ln in txt.split("\n"):
        if ln.startswith("> ⚠️ 待回源：") and any(d in ln for d in cfg["drop_lines"]):
            continue
        new_lines.append(ln)
    txt = "\n".join(new_lines)

    # 2) 在「待回源（本地库无源，未核填）」标题前插入已核填块
    anchor = "**待回源（本地库无源，未核填）**"
    insert = "**已核填补充（本地民法典全文 · 2026-09-04 回补核填）**\n" + "".join(blocks)
    if anchor in txt:
        txt = txt.replace(anchor, insert + "\n" + anchor, 1)
    else:
        # 无待回源标题（已全部核填）则插到「## 六、抗辩与但书」前
        a2 = "\n## 六、抗辩与但书"
        if a2 in txt:
            txt = txt.replace(a2, "\n" + insert + a2, 1)
        elif "## 六、" in txt:
            txt = txt.replace("\n## 六、", "\n" + insert + "\n## 六、", 1)
        else:
            print("⚠️ 找不到插入锚点:", rel)
            continue

    # 3) 清理空标题：若待回源标题下已无条目，删掉该标题
    txt = re.sub(r"\*\*待回源（本地库无源，未核填）\*\*\s*\n(?=\n## )", "", txt)

    if APPLY and txt != orig:
        ts = time.strftime("%Y%m%d-%H%M%S")
        shutil.copy2(path, path + ".bak-" + ts)
        open(path, "w", encoding="utf-8").write(txt)

    print("%-58s 核填 %2d 条 %s | 失败 %s | %s" % (
        rel.split("/")[-1][:56], len(ok),
        ("（%s…）" % "、".join(ok[:3])) if ok else "",
        bad or "无",
        "已写入" if APPLY and txt != orig else ("无变化" if txt == orig else "待写入")))

print("\n" + ("APPLY 完成" if APPLY else "DRY-RUN（加 --apply 执行；改前自动 .bak-时间戳 备份）"))
