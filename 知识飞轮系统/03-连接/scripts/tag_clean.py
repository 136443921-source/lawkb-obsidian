#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标签脏数据规整（v1.0 2026-09-06）。
规则（方案A·稳健分批，仅清零语义风险项）：
  - 空标签 ''                      -> 删除
  - '- - X|X' / '- - X' bug 复合    -> 去 '- - ' 前缀；含 '|' 取最后一段
  - 纯数字标签：
       年份白名单(2020-2029 或 2020xxxx 8位) -> 保留
       其余小数字(8/9/7/13/4/1/12/31...)     -> 删除
  - '概念页 概念-XX' 复合（10种/872文件）     -> 本次 SKIP（放下周，先确认原意）
  - '法律资讯 - 日报'/'Claude Code'/超长串等 -> 本次 SKIP（人工确认）
默认 --dry-run（不写文件）；--apply 时先全量备份受影响文件到备份目录再改写。
"""
import os, re, sys, shutil, datetime
VAULT = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统"
def get_all_md():
    out=[]
    for r,d,fs in os.walk(VAULT):
        d[:]=[x for x in d if not x.startswith('.')]
        for f in fs:
            if f.endswith('.md'):
                out.append(os.path.join(r,f))
    return out
def extract_tags(text):
    if not text.startswith('---'): return None
    end=text.find('\n---',3)
    if end==-1: return None
    fm=text[3:end]
    m=re.search(r'^tags:\s*\[(.*?)\]',fm,re.M)
    if m: return [t.strip() for t in m.group(1).split(',')]
    mb=re.search(r'^tags:\s*\n((?:\s*-\s*.+\n)+)',fm,re.M)
    if mb: return [l.strip().lstrip('-').strip() for l in mb.group(1).splitlines() if l.strip().startswith('-')]
    return None
def is_year_keep(tg):
    if not tg.isdigit(): return False
    if len(tg)==4: return 2020<=int(tg)<=2029
    if len(tg)==8: return 2020<=int(tg[:4])<=2029
    return False
def clean_tag(tg):
    """返回 (new_value_or_None, action)，action in {keep,del,fix,skip}。"""
    if tg=='' : return (None,'del')
    if tg.startswith('- - ') or tg.startswith('- -'):
        rest=tg.lstrip('- ').strip()
        if '|' in rest: rest=rest.split('|')[-1].strip()
        return (rest if rest else None,'fix')
    if tg.isdigit():
        if is_year_keep(tg): return (tg,'keep')
        return (None,'del')
    if tg.startswith('概念页 '): return (tg[len('概念页 '):],'fix')  # 去前缀只留 概念-XX
    if ' ' in tg: return (None,'del')  # 其余含空格复合(法律资讯-日报/Claude Code/超长串等)直接删，防标签爆炸
    return (tg,'keep')
BUSINESS={'02-提炼','06-沉淀','01-采集','05-调用'}  # 业务核心库：--safe 下跳过其纯数字删除
def main():
    apply = '--apply' in sys.argv
    safe = '--safe' in sys.argv
    files=get_all_md()
    changes=[]; skip_files=set()
    for f in files:
        try: t=open(f,encoding='utf-8',errors='ignore').read()
        except: continue
        tags=extract_tags(t)
        if tags is None: continue
        new=[]; changed=False; acted=[]
        top=os.path.relpath(f,VAULT).split('/')[0]
        for tg in tags:
            nv,act=clean_tag(tg)
            if safe and top in BUSINESS and act=='del' and tg.isdigit() and not is_year_keep(tg):
                new.append(tg); skip_files.add(f); continue  # --safe: 业务库纯数字保留待确认
            if act=='keep': new.append(tg)
            elif act=='skip': new.append(tg); skip_files.add(f)
            elif act=='del': changed=True; acted.append((tg,'删'))
            elif act=='fix':
                if nv: new.append(nv); changed=True; acted.append((tg,f'修→{nv}'))
                else: changed=True; acted.append((tg,'删'))
        if changed:
            changes.append((f,tags,new,acted))
    print(f"[dry-run={not apply}] 将改动文件数: {len(changes)} | skip(未处理)文件数: {len(skip_files)}")
    if not apply:
        print("=== 变更预览(前40) ===")
        for f,tags,new,acted in changes[:40]:
            print(f"\n• {os.path.relpath(f,VAULT)}")
            for a in acted: print(f"    {a[0]!r} -> {a[1]}")
        if len(changes)>40:
            print(f"\n... 其余 {len(changes)-40} 文件省略，--apply 前可看全量备份清单")
    else:
        ts=datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bakdir=f"/tmp/tag_clean_bak_{ts}"
        os.makedirs(bakdir,exist_ok=True)
        done=0
        for f,tags,new,acted in changes:
            rel=os.path.relpath(f,VAULT)
            shutil.copy2(f, os.path.join(bakdir, rel.replace('/','__')))
            t=open(f,encoding='utf-8',errors='ignore').read()
            end=t.find('\n---',3)
            fm=t[3:end]
            # 重写 tags 段
            if re.search(r'^tags:\s*\[.*?\]',fm,re.M):
                newfm=re.sub(r'^tags:\s*\[.*?\]', 'tags: ['+', '.join(new)+']', fm, flags=re.M, count=1)
            else:
                block='\n'.join('  - '+x for x in new)
                newfm=re.sub(r'^tags:\s*\n(?:\s*-\s*.+\n)+', 'tags:\n'+block+'\n', fm, flags=re.M, count=1)
            open(f,'w',encoding='utf-8').write('---'+newfm+t[end:])
            done+=1
        print(f"已改写 {done} 文件；备份目录: {bakdir}")
        print("验证中...")
        # 复扫
        c2=0
        for f in get_all_md():
            tg=extract_tags(open(f,encoding='utf-8',errors='ignore').read())
            if not tg: continue
            for x in tg:
                if x=='' or x.startswith('- - ') or (x.isdigit() and not is_year_keep(x)):
                    c2+=1; break
        print(f"残留(空/- - /非年份数字)文件数: {c2}（应为0）")
if __name__=='__main__':
    main()
