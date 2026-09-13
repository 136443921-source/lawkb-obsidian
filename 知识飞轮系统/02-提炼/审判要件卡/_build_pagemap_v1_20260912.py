# -*- coding: utf-8 -*-
"""
《贵州法院类案审判要件指南（第一卷）》页码映射表 v2（正式版）

要点（对应铁律坑 26 / 坑 4）：
- 页脚在 PDF 里被拆成 3 行渲染：装饰符 / 页码 / 装饰符（如 I / 035 / I）
  → 取**倒数第一行或第二行**中形如 `\W*(\d{1,3})\W*` 的短串
- OCR 形似字符归一：I|l!→1, O o Q D→0, s S→5, B→8, g q→9, Z z→2
- 缺失页用**相邻已知点线性插值**（全书映射非线性，禁止套全局公式）
- 以「页眉部分名」分段 + 总目录给出的各部分起始书页做**锚点校验**
- ⚠ key 一律 **0-based** fitz 页索引：书页 = mp[str(PDF页 - 1)]
"""
import fitz, json, re, random

PDF = "/Users/chenyouqiang/Desktop/贵州法院类案审判要件指南（第一卷）.pdf"
OUT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/02-提炼/审判要件卡/贵州类案指南第一卷-页码映射表.json"

doc = fitz.open(PDF)
N = doc.page_count

CMAP = str.maketrans({
    "I": "1", "l": "1", "i": "1", "|": "1", "!": "1", "[": "1",
    "O": "0", "o": "0", "Q": "0", "D": "0",
    "s": "5", "S": "5", "B": "8", "g": "9", "q": "9", "Z": "2", "z": "2",
})

PARTS = ["第一部分", "第二部分", "第三部分", "第四部分", "第五部分",
         "第六部分", "第七部分", "第八部分", "第九部分", "第十部分"]
PART_BOOK = dict(zip(PARTS, [1, 37, 73, 103, 139, 177, 211, 247, 275, 313]))

W, H = doc[0].rect.width, doc[0].rect.height


def parse_page_no(i):
    t = doc[i].get_text()
    ls = [x.strip() for x in t.split("\n") if x.strip()]
    if not ls:
        return None
    # 优先末行，其次倒数第 2、3 行（页脚被拆行渲染）
    for line in reversed(ls[-3:]):
        fl = re.sub(r"\s+", "", line)
        if not fl or len(fl) > 8:
            continue
        # 🔴 硬门槛：原行必须至少含 1 个「真」ASCII 数字
        #    否则单个装饰符 I / | 经 CMAP 会变成 "1" 被误判为页码（本坑实证）
        if not re.search(r"[0-9]", fl):
            continue
        m = re.fullmatch(r"\W*(\d{1,3})\W*", fl.translate(CMAP))
        if m:
            v = int(m.group(1))
            if 1 <= v <= 400:
                return v
    return None


def header_part(i):
    t = re.sub(r"\s+", "", doc[i].get_text(clip=fitz.Rect(0, 0, W, H * 0.07)).strip())
    for name in PARTS:
        if name in t:
            return name
    return None


# ---- 1. 解析印刷页码 ----
raw = {i: parse_page_no(i) for i in range(N)}
hit = sum(1 for v in raw.values() if v is not None)
print(f"页脚解析命中: {hit}/{N} ({hit/N*100:.1f}%)")

# ---- 2. 线性插值补缺失 ----
mapping = dict(raw)
i = 0
while i < N:
    if mapping.get(i) is None:
        j = i
        while j < N and mapping.get(j) is None:
            j += 1
        left = mapping.get(i - 1) if i > 0 else None
        right = mapping.get(j) if j < N else None
        span = j - i
        for k in range(i, j):
            if left is not None and right is not None:
                mapping[k] = round(left + (right - left) * (k - i + 1) / (span + 1))
            elif left is not None:
                mapping[k] = left + (k - i + 1)
            elif right is not None:
                mapping[k] = right - (j - k)
        i = j
    else:
        i += 1

# ---- 3. 页眉分段 + offset ----
seg = {}
for i in range(N):
    s = header_part(i)
    if s:
        seg.setdefault(s, i)

print("\n=== 分段 offset 与目录锚点校验 ===")
offsets = {}
for name in PARTS:
    idx = seg.get(name)
    if idx is None:
        print(f"  {name}: ❌ 未定位到页眉")
        continue
    offs = [mapping[k] and k - mapping[k] for k in range(idx, min(idx + 10, N))]
    # 取出现次数最多的 offset（防御个别页解析错）
    from collections import Counter
    c = Counter([o for o in offs if isinstance(o, int)])
    if not c:
        print(f"  {name}: ❌ 无可解析页脚")
        continue
    off = c.most_common(1)[0][0]
    offsets[name] = off
    start_idx = PART_BOOK[name] + off
    actual = mapping.get(start_idx)
    ok = "✅" if actual == PART_BOOK[name] else f"⚠️(读={actual})"
    print(f"  {name}: 页眉起始 idx={idx}(PDF页{idx+1}) offset={off} "
          f"起始 idx={start_idx}(PDF页{start_idx+1}) 目录书页={PART_BOOK[name]} {ok}")

# ---- 4. 抽样交叉校验 ----
random.seed(7)
start0 = min(offsets[k] for k in offsets) + PART_BOOK[PARTS[0]]
samples = sorted(random.sample(range(start0, N - 1), 15))
print("\n=== 抽样交叉校验（插值后 vs 原始解析）===")
agree = tot = 0
for i in samples:
    m, e = mapping.get(i), raw.get(i)
    if e is not None:
        tot += 1
        agree += (e == m)
    print(f"  idx{i}(PDF页{i+1}) 映射={m} 原解析={e} {'✅' if (e is None or e==m) else '❌'}")
print(f"一致率: {agree}/{tot}")

# ---- 5. 单调性（分段内）----
print("\n=== 单调性（按段）===")
allmono = True
for pi, name in enumerate(PARTS):
    if name not in offsets:
        continue
    sidx = PART_BOOK[name] + offsets[name]
    eidx = (PART_BOOK[PARTS[pi+1]] + offsets[PARTS[pi+1]]) if pi + 1 < len(PARTS) and PARTS[pi+1] in offsets else N
    seq = [mapping.get(k) for k in range(max(sidx,0), min(eidx, N)) if mapping.get(k) is not None]
    mono = all(seq[j] <= seq[j+1] for j in range(len(seq)-1)) if len(seq) > 1 else True
    allmono &= mono
    print(f"  {name}: idx {sidx}~{eidx}  {'✅单调' if mono else '❌非单调'}")
print(f"全书分段单调: {'✅' if allmono else '❌'}")

# ---- 6. 以「段内 offset」确定性重建（不再用插值结果）----
# 根因：前置页（总序/前言/凡例/目录）各自使用独立页码系列（均从 001 起），
#      在它们之间做插值会跨越页码系列边界，污染正文起点。
# 正解：正文区每部分 offset 恒定 → 书页 = idx - offset，段内无需插值。
part_range = {}
for pi, name in enumerate(PARTS):
    if name not in offsets:
        continue
    s = PART_BOOK[name] + offsets[name]
    nxt = PARTS[pi + 1] if pi + 1 < len(PARTS) else None
    e = (PART_BOOK[nxt] + offsets[nxt] - 1) if (nxt and nxt in offsets) else N - 1
    part_range[name] = (s, min(e, N - 1), offsets[name])

# ---- 6b. 融合页脚实测 + 段内 offset 二次漂移修正 ----
# ① 段内可能二次漂移（第四部分 idx146+ 由 26→24，与坑 4 同源），不能一段一个 offset 到底
# ② 页脚实测优先；但与「当前局部 offset 的预测」偏差 >TOL 者判 OCR 噪声，改用预测值
# ③ 局部 offset 自适应：连续 ADC 页实测稳定偏离时，就地更新 offset
TOL = 3
final = {}
for i in range(N):
    put = None
    for name, (s, e, off) in part_range.items():
        if s <= i <= e:
            put = i - off
            break
    final[str(i)] = put

adopted = rejected = 0
for name, (s, e, off0) in part_range.items():
    cur = off0
    for i in range(s, min(e, N - 1) + 1):
        pred = i - cur
        rr = raw.get(i)
        if rr is not None and abs(rr - pred) <= TOL:
            final[str(i)] = rr          # 采信实测
            adopted += 1
        elif rr is not None:
            # 偏差超限：判为 OCR 噪声；但若连续 3 页都同向偏离 → 视为真实漂移，更新 offset
            nxt = [raw.get(i + k) for k in (1, 2, 3)]
            nxt = [x for x in nxt if x is not None]
            drift = len(nxt) >= 2 and all(abs(x - (i + k + 1 - cur)) > TOL for k, x in enumerate(nxt, 1))
            if drift:
                cur = i - rr
                final[str(i)] = rr
                adopted += 1
                print(f"  ↳ {name} idx{i}(PDF页{i+1}) 发生二次漂移，offset {cur if False else off0}→{cur}")
            else:
                final[str(i)] = pred
                rejected += 1
        else:
            final[str(i)] = pred
print(f"  实测采信 {adopted} 页 / 噪声剔除 {rejected} 页")

# 用页脚原始解析做最终交叉校验
print("\n=== 最终交叉校验（重建 vs 页脚原解析）===")
agree = tot = mism = 0
for i in range(N):
    v, rr = final.get(str(i)), raw.get(i)
    if v is None or rr is None:
        continue
    tot += 1
    if v == rr:
        agree += 1
    else:
        mism += 1
        if mism <= 8:
            print(f"  ❌ idx{i}(PDF页{i+1}) 重建={v} 原解析={rr}")
print(f"  正文区 coincide: {agree}/{tot}  （不符 {mism}）")

seq = [final[str(i)] for i in range(N) if final.get(str(i)) is not None]
mono = all(seq[j] <= seq[j + 1] for j in range(len(seq) - 1))
print(f"  全书单调性: {'✅ 通过' if mono else '❌ 失败'}")

print("\n=== 各部分边界 ===")
for name, (s, e, off) in part_range.items():
    print(f"  {name}: PDF页{s+1}~{e+1}  书页{PART_BOOK[name]}~{final[str(e)]}  ({e-s+1}页) offset={off}")
json.dump(final, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"\n✅ 已写入 {OUT}")
print(f"   条目 {len(final)}，有值 {sum(1 for v in final.values() if v is not None)}")
print(f"   🔴 取值公式：书页 = mp[str(PDF页 - 1)]   （0-based）")
