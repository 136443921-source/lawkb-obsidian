#!/usr/bin/env python3
# -*- coding: utf-8 -*-
""".bak 清理器（P2-1）——保留最近 N 个 + 按月打包归档

═══════════ 为什么要有这个 ═══════════
2026-10-23 实测：LawKB 下 .bak 类文件 488 个 / 37.6 MB，skills 下 156 个 / 8.7 MB。
最夸张的是同一个文件堆了 45~50 个历史版本：
  · 知识飞轮系统/ima_intake_state.json          45 个
  · 案件生命周期大屏流水线/.../案件生命周期大屏.html  50 个
  · LTI文本监控器/.../yuandian_verify_cache.json 25 个
害处不是占盘（才 46 MB），是**污染扫描**：grep、扫卡、统计规模时全被历史副本干扰，
数字算不准、结论跟着错。

═══════════ 三步安全模型（不直接删）═══════════
1. scan     只读扫描，按「基名」分组，算出每组保留哪几个、归档哪些
2. archive  把该归档的打成 <root>/_bak归档/YYYY-MM.tar.gz，包内附 manifest.json
            （记录每个成员的 sha256 + 原始相对路径 + mtime），并**校验包内成员数**
3. delete   只有在「归档包已存在且成员数与清单一致」时，才允许删原件
            （三-B 铁律：删之前必须先有可验证的安全网）

═══════════ 用法 ═══════════
    python3 bak_janitor.py --dry-run                     # 只看不动（默认）
    python3 bak_janitor.py --archive                     # 打包归档，不删
    python3 bak_janitor.py --delete --yes                # 归档校验通过后删原件
    python3 bak_janitor.py --root ~/Documents/LawKB --keep 5
    python3 bak_janitor.py --report out.md               # 输出人读清单

退出码：0 正常；2 归档校验不通过（拒绝删除）；3 参数错误
"""
import os
import re
import sys
import json
import time
import tarfile
import hashlib
import argparse
import datetime

DEFAULT_ROOTS = [
    os.path.expanduser("~/Documents/LawKB"),
    os.path.expanduser("~/.workbuddy/skills"),
]
SKIP_DIRS = {"node_modules", "venv", "__pycache__", ".git", "_bak归档", ".obsidian"}
# 判定 .bak 类文件：以 .bak 开头后缀，或含 .bak / .backup / .old / .orig
PAT = re.compile(r"(\.bak[^/]*$|\.backup[^/]*$|\.old[^/]*$|\.orig[^/]*$)", re.I)


def is_bak(name):
    return bool(PAT.search(name))


def base_of(name):
    """剥掉 .bak 后缀，得到"这份文件是谁的副本" """
    return PAT.sub("", name)


def scan(roots, keep):
    """返回 (groups, total, size)
    groups: {abs_base_key: {"keep":[...], "archive":[...]}}
    """
    found = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for f in fn:
                if not is_bak(f):
                    continue
                p = os.path.join(dp, f)
                try:
                    st = os.stat(p)
                except OSError:
                    continue
                key = os.path.join(dp, base_of(f))
                found.setdefault(key, []).append(
                    {"path": p, "mtime": st.st_mtime, "size": st.st_size}
                )
    groups = {}
    total = 0
    size = 0
    for key, items in found.items():
        items.sort(key=lambda x: x["mtime"], reverse=True)
        groups[key] = {"keep": items[:keep], "archive": items[keep:]}
        total += len(items)
        size += sum(i["size"] for i in items)
    return groups, total, size


def sha256(p, limit_mb=48):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _pick_archive_path(archive_dir, month):
    """选定归档包路径。已存在则用 _2/_3 后缀另存。

    ⚠️ 踩过的坑：tarfile 的 mode="a" 写的是**未压缩** tar，即使文件名以 .tar.gz 结尾；
       写进去再用 "r:gz" 读回必然报 `not a gzip file`。故一律用 "w:gz" 新建，
       月度重跑时另起分卷，而不是往 gzip 里 append（gzip 也不支持随机 append）。
    """
    base = os.path.join(archive_dir, f"{month}.tar.gz")
    if not os.path.exists(base):
        return base
    k = 2
    while True:
        p = os.path.join(archive_dir, f"{month}_{k}.tar.gz")
        if not os.path.exists(p):
            return p
        k += 1


def do_archive(groups, month, archive_dir):
    os.makedirs(archive_dir, exist_ok=True)
    members = []
    for key, g in groups.items():
        for it in g["archive"]:
            members.append(it)
    if not members:
        print("没有需要归档的副本（每组都不超过保留数）。")
        return None, 0
    tar_path = _pick_archive_path(archive_dir, month)
    manifest = {"created": datetime.datetime.now().isoformat(timespec="seconds"),
                "month": month, "count": 0, "files": [], "archive": os.path.basename(tar_path)}
    with tarfile.open(tar_path, "w:gz", format=tarfile.GNU_FORMAT) as tf:
        for it in members:
            rel = os.path.relpath(it["path"], os.path.expanduser("~"))
            try:
                tf.add(it["path"], arcname=rel)
            except OSError as e:
                print(f"  ⚠️ 加入失败 {rel}: {e}")
                continue
            manifest["files"].append({
                "arc": rel,
                "sha256": sha256(it["path"]),
                "size": it["size"],
                "mtime": it["mtime"],
            })
    # 校验：包里实际成员必须全覆盖清单
    with tarfile.open(tar_path, "r:gz") as tf:
        names = set(tf.getnames())
    ok = all(m["arc"] in names for m in manifest["files"])
    manifest["verified"] = ok
    manifest["count"] = len(manifest["files"])
    mf = tar_path + ".manifest.json"
    json.dump(manifest, open(mf, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"📦 归档包：{tar_path}")
    print(f"   加入 {len(members)} 个文件，清单 {manifest['count']} 条，校验：{'✅ 通过' if ok else '❌ 失败'}")
    print(f"   清单文件：{mf}")
    return tar_path, len(members) if ok else 0


def do_delete(groups, archive_dir, month):
    """仅删除「归档包+清单 都已验证覆盖」的文件。

    支持月度多分卷：把该月所有 *.tar.gz.manifest.json 里 verified=true 的成员合并成覆盖集。
    """
    import glob as _glob
    paths = sorted(_glob.glob(os.path.join(archive_dir, f"{month}*.tar.gz.manifest.json")))
    if not paths:
        print("❌ 找不到归档清单，拒绝删除。先跑 --archive。")
        return 1
    covered = set()
    bad = []
    for mp in paths:
        try:
            man = json.load(open(mp, encoding="utf-8"))
        except Exception as e:
            bad.append((mp, str(e)))
            continue
        if not man.get("verified"):
            bad.append((mp, "verified=false"))
            continue
        covered |= {f["arc"] for f in man.get("files", [])}
    if bad:
        print("❌ 以下归档清单未通过校验，拒绝删除（先确认归档完整）：")
        for mp, why in bad:
            print(f"   {mp}  ← {why}")
        return 2
    print(f"已校验 {len(paths)} 份归档清单，覆盖 {len(covered)} 个文件")
    # 「进回收站，不硬删」——默认 move 到 ~/.Trash/bak_janitor_<ts>/，可原样拖回；
    # 只有显式 --purge 才真正 os.remove。
    trash_dir = os.path.join(os.path.expanduser("~"), ".Trash",
                             f"bak_janitor_{datetime.datetime.now():%Y%m%d_%H%M%S}")
    purged = getattr(do_delete, "_purge", False)
    if not purged:
        os.makedirs(trash_dir, exist_ok=True)
    n = 0
    skipped = 0
    for key, g in groups.items():
        for it in g["archive"]:
            rel = os.path.relpath(it["path"], os.path.expanduser("~"))
            if rel not in covered:
                skipped += 1
                continue
            try:
                if purged:
                    os.remove(it["path"])
                else:
                    dest = os.path.join(trash_dir, rel)
                    os.makedirs(os.path.dirname(dest), exist_ok=True)
                    os.rename(it["path"], dest)
                n += 1
            except OSError as e:
                print(f"  ⚠️ 处理失败 {rel}: {e}")
    if purged:
        print(f"🗑 已硬删 {n} 个原件（均有归档包覆盖）")
    else:
        print(f"🗑 已移入回收站 {n} 个原件（均有归档包覆盖）")
        print(f"   回收站：{trash_dir}")
        print(f"   恢复：把上述目录整体拖回原位即可；确认无碍后可清空回收站")
    if skipped:
        print(f"⏭ 跳过 {skipped} 个（不在归档覆盖集内，未动）")
    return 0


def write_report(groups, total, size, keep, path):
    L = ["# .bak 清理清单", ""]
    L.append(f"- 生成时间：{datetime.datetime.now():%Y-%m-%d %H:%M}")
    L.append(f"- 扫描到 .bak 类文件：**{total}** 个，合计 **{size/1048576:.2f} MB**")
    L.append(f"- 每份基名保留最近 **{keep}** 个版本，其余归档/删除")
    L.append("")
    arch = [(k, v) for k, v in groups.items() if v["archive"]]
    arch.sort(key=lambda x: -len(x[1]))
    L.append(f"## 有多余版本的文件组：{len(arch)} 组")
    L.append("")
    L.append("| 基名（相对 ~） | 总版本 | 保留 | 归档 |")
    L.append("|---|---|---|---|")
    home = os.path.expanduser("~")
    for k, v in arch:
        L.append(f'| `{os.path.relpath(k, home)}` | {len(v["keep"])+len(v["archive"])} | {len(v["keep"])} | {len(v["archive"])} |')
    L.append("")
    L.append("*本清单由 bak_janitor.py --report 生成，只统计、未改动任何文件。*")
    open(path, "w", encoding="utf-8").write("\n".join(L) + "\n")
    print(f"📄 清单已写：{path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", help="扫描根目录，可多次给；默认 LawKB + skills")
    ap.add_argument("--keep", type=int, default=5, help="每组保留最近几个（默认 5）")
    ap.add_argument("--archive", action="store_true", help="打包归档（不删）")
    ap.add_argument("--delete", action="store_true", help="归档校验后把原件移入回收站")
    ap.add_argument("--purge", action="store_true", help="配合 --delete：真删（不进回收站，慎用）")
    ap.add_argument("--yes", action="store_true", help="配合 --delete，确认执行")
    ap.add_argument("--dry-run", action="store_true", help="只看不动（默认行为）")
    ap.add_argument("--report", help="输出人读清单到指定路径")
    a = ap.parse_args()

    roots = a.root or DEFAULT_ROOTS
    groups, total, size = scan(roots, a.keep)
    arch_cnt = sum(len(v["archive"]) for v in groups.values())
    print(f"扫描根：{', '.join(roots)}")
    print(f"发现 .bak 类文件 {total} 个（{size/1048576:.2f} MB），"
          f"其中 {arch_cnt} 个超出「保留最近 {a.keep} 个」")
    print(f"模式：{'DELETE' if a.delete else ('ARCHIVE' if a.archive else 'DRY-RUN')}")

    if a.report:
        write_report(groups, total, size, a.keep, a.report)

    if a.delete:
        if not a.yes:
            print("❌ --delete 需配合 --yes（防误触）")
            return 3
        month = f"{datetime.date.today():%Y-%m}"
        do_delete._purge = bool(a.purge)
        return do_delete(groups, os.path.join(roots[0], "_bak归档"), month)

    if a.archive:
        month = f"{datetime.date.today():%Y-%m}"
        do_archive(groups, month, os.path.join(roots[0], "_bak归档"))
        print("\n下一步（需老强确认后才做）：")
        print("  python3 bak_janitor.py --delete --yes")
        return 0

    # dry-run：只打印 TOP 组
    print("\n=== 多余版本最多的 10 组 ===")
    arch = sorted([(k, v) for k, v in groups.items() if v["archive"]],
                  key=lambda x: -len(x[1]))[:10]
    home = os.path.expanduser("~")
    for k, v in arch:
        print(f'  {len(v["archive"]):3d} 待归档  {os.path.relpath(k, home)}')
    print("\n（dry-run 未改动任何文件。加 --report 出清单，加 --archive 打包）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
