#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_guard_frmain.py —— FR-MAIN 铁律执行器（法条唯一主源 / 原材料仓只读）

【背景】
2026-09-27 排查发现：LawKB/scripts/ 下多个脚本使用 `os.walk(全库)` 定位
.md 文件后直接 `open(path,"w")` 覆写，其中 update_frontmatter.py 已于
2026-09-23 15:53 洗过全库，原材料仓 40 张卡的 frontmatter 被 yaml.dump
重建、所有 `#` 注释被永久销毁，且已进 git、无回滚源。

【本Guard的作用】
拦截 os.walk，使任何受保护目录下的文件都不会被批量脚本扫描到，
从而在**无需改动各脚本写入逻辑**的前提下实现止血。

【受保护对象】
  - 法律法规库（冻结为只读原材料仓，FR-MAIN 第二条）
  - 法条银行（法条唯一主源，一切自动化法条写入的唯一落点，FR-MAIN 第一条）

【越权通道】
确需越权时，显式传入 --i-know-this-violates-fr-main 即可跳过拦截，
此时会打印醒目留痕提示（事后可据日志/终端记录追溯）。

【用法】
在各脚本顶部、 import os 之后插入：
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import _guard_frmain
    _guard_frmain.install()
"""
import os
import sys

# ── 受保护目录关键字（命中即拦截）─────────────────────────────
PROTECTED_TOKENS = ("法律法规库", "法条银行")

# ── 越权显式开关 ───────────────────────────────────────────
EMERGENCY_FLAG = "--i-know-this-violates-fr-main"

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║  🔴🔴  FR-MAIN 铁律生效 · 法条唯一主源                        ║
║                                                              ║
║  · 法条银行 = 法条唯一主源（一切自动化法条写入的唯一落点）    ║
║  · 法律法规库 = 冻结只读原材料仓，禁止批量写入 / 就地定级     ║
║  · 违规前缀：【🔴法条主源越界】                               ║
║                                                              ║
║  本次运行因涉及受保护目录已被拦截。                           ║
║  如确需越权，请显式传入 %s                     ║
╚══════════════════════════════════════════════════════════════╝
""" % EMERGENCY_FLAG

_ORIGINAL_WALK = os.walk
_GUARD_ACTIVE = False


def _capture_original_walk():
    """
    捕获「未被本 guard 污染」的原始 os.walk。

    修复点（2026-09-27 实测发现）：
    若在已 patch 的进程内 reload 本模块，模块级 `_ORIGINAL_WALK` 会指向
    自己上一版生成的 _safe_walk，形成递归链并最终 RecursionError。
    此处沿 _frmain_orig 链向上回溯，确保拿到干净的原始 os.walk。
    """
    global _ORIGINAL_WALK
    cur = os.walk
    for _ in range(16):
        orig = getattr(cur, "_frmain_orig", None)
        if orig is None:
            break
        cur = orig
    _ORIGINAL_WALK = cur


def _contains_protected(path):
    return any(tok in str(path) for tok in PROTECTED_TOKENS)


def _safe_walk(top, *args, **kwargs):
    """拦截版 os.walk：绝不进入受保护目录"""
    top = str(top)
    if _contains_protected(top):
        sys.stderr.write(
            "\n[FR-MAIN·拦截] 拒绝扫描受保护目录：%s\n" % top)
        sys.stderr.write("[FR-MAIN·拦截] 目标根路径命中受保护关键字，已终止。\n")
        return
    for root, dirs, files in _ORIGINAL_WALK(top, *args, **kwargs):
        # 就地过滤子目录，防止继续下沉（标记属性，便于回溯原始 walk）
        kept = [d for d in dirs if not _contains_protected(d)]
        dropped = [d for d in dirs if d not in kept]
        if dropped:
            sys.stderr.write(
                "[FR-MAIN·拦截] 跳过受保护子目录：%s\n" % ", ".join(
                    os.path.join(root, d) for d in dropped))
        dirs[:] = kept
        yield root, dirs, files


_safe_walk._frmain_wrapped = True
_safe_walk._frmain_orig = None


def install():
    """安装 FR-MAIN 守卫，必须在 os.walk 被使用前调用"""
    global _GUARD_ACTIVE
    # 无论是否越权，都先确保拿到干净的原始 walk（防止 reload 造成递归）
    _capture_original_walk()
    if _GUARD_ACTIVE:
        return True

    if EMERGENCY_FLAG in sys.argv[1:]:
        sys.stderr.write(
            "\n[FR-MAIN·越权] 🔴 本次运行显式越权，正在写入受保护目录。\n"
            "[FR-MAIN·越权] 该操作违反 FR-MAIN，责任自担，建议事后留痕复盘。\n\n")
        return False

    sys.stderr.write(BANNER)
    _safe_walk._frmain_orig = _ORIGINAL_WALK
    os.walk = _safe_walk
    _GUARD_ACTIVE = True
    return True


if __name__ == "__main__":
    print(BANNER)
    print("受保护关键字：%s" % (", ".join(PROTECTED_TOKENS)))
    print("安装状态：%s" % ("已安装 os.walk 拦截" if install() else "越权模式，未安装拦截"))
