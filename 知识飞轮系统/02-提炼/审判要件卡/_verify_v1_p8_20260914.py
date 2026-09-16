# -*- coding: utf-8 -*-
# 第八部分·知产惩罚性赔偿 交付校验器（目标 ERROR 0 / WARN 0）
# 校验：frontmatter 必含字段 / rule_id 与文件名一致 / 八段齐全 / 正文串码（日文假名+非白名单拉丁）
import os, re, glob

OUT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/06-沉淀/裁判规则库/商事纠纷/"
RIDS = [f"R-SH-{i:03d}" for i in range(42, 56)]

FM_KEYS = ['title','rule_id','card_type','source','type','created','date','created_month',
           'review_date','updated','geo_scope','yuandian_source_pending','library','aliases',
           'review_step','elements','ruling','burden_of_proof','negative_sample','negative_note','related_links']
SECTIONS = ['一、裁判规则', '二、审查要点', '三、构成要件与举证', '四、法条依据',
            '五、抗辩与但书', '六、翻车标本', '七、来源与地域效力', '八、关联']
KANA = re.compile(r'[぀-ヿ]')
LATIN = re.compile(r'[A-Za-z]{4,}')
URL_RE = re.compile(r'https?://\S+')
FMKEY_RE = re.compile(r'^[a-z_]+:')  # 仅挡正文内的“键:”式误入（正文不应有）
WHITE = {'HTTP','PDF','URL','CSS','JSON','HTML','XML','API','OCR','SQL','NPC','QCC','DOI','ISBN','AI','NFT',
         'HTTPS','LEGAL','REGULATION','COURT','SCOPE','GOV','CN','COM','FLK'}

def split_fm(text):
    if text.startswith('---'):
        end = text.find('\n---', 3)
        if end != -1:
            fm = text[3:end]
            body = text[end+4:]
            return fm, body
    return '', text

errors = []
warns = []

for rid in RIDS:
    files = glob.glob(os.path.join(OUT, rid + '-*.md'))
    if not files:
        errors.append(f"[{rid}] 文件缺失"); continue
    if len(files) > 1:
        errors.append(f"[{rid}] 多文件冲突: {files}")
    fp = files[0]
    text = open(fp, encoding='utf-8').read()
    fm, body = split_fm(text)
    # frontmatter 字段
    for k in FM_KEYS:
        if re.search(r'^%s:' % re.escape(k), fm, re.M) is None:
            errors.append(f"[{rid}] frontmatter 缺字段 {k}")
    # rule_id 与文件名一致
    m = re.search(r'^rule_id:\s*(.+)$', fm, re.M)
    if m and m.group(1).strip() != rid:
        errors.append(f"[{rid}] rule_id 与文件名不符: {m.group(1).strip()}")
    # 八段
    for s in SECTIONS:
        if s not in body:
            errors.append(f"[{rid}] 缺段落 {s}")
    # 正文串码：剥离 URL 后查 假名 + 非白名单拉丁
    b = URL_RE.sub('', body)
    for kk in KANA.findall(b):
        errors.append(f"[{rid}] 日文假名残留: {kk}")
    for mlat in LATIN.findall(b):
        if mlat.upper() not in WHITE and not FMKEY_RE.match(mlat + ':'):
            # 排除正文内偶发的英文专有缩写（此处无），其余报错
            errors.append(f"[{rid}] 可疑拉丁串码: {mlat}")
    # 必含 分层提示 + 核验链接
    if '🔴' not in body:
        warns.append(f"[{rid}] 无 🔴 分层提示")
    if '核验：' not in body and '（核验：' not in body:
        warns.append(f"[{rid}] 无 法条核验链接标注")
    # 关联 连接枢纽
    if '连接枢纽-商事纠纷' not in text:
        warns.append(f"[{rid}] 未挂 连接枢纽-商事纠纷")

n = len([r for r in RIDS if glob.glob(os.path.join(OUT, r + '-*.md'))])
print(f"已落盘卡数: {n} / 14")
print(f"ERROR: {len(errors)}")
for e in errors: print("  ❌", e)
print(f"WARN: {len(warns)}")
for w in warns: print("  ⚠️", w)
print("✅ 校验通过（ERROR=0）" if not errors else "❌ 存在 ERROR，须修复")
