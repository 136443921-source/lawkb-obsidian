# -*- coding: utf-8 -*-
"""
孤儿噪音概念页清理 v1.0（2026-08-30）
============================================================================
判据（安全优先 · 依 MEMORY「宁可少挂不可错挂」铁律）：
    真实笔记入链 = 0  →  移走不会造成任何断链

在此之上再做人工语义分档：
    【噪音】畸形链接产物（文件名带引号）/ 纯数字 / 占位符 / 有同名真实笔记的冗余副本
    【保留】真概念（法概念、案件名、待建枢纽提示）——零入链只是暂时状态，不动

产物：概念页/.trash-2026-08-30/ + manifest.txt（记录映射，可回滚）
"""
import os
import re
import io
import shutil

CP = "/Users/chenyouqiang/Documents/LawKB/知识飞轮系统/03-连接/概念页"
TRASH = os.path.join(CP, ".trash-2026-08-30")

# 判定为噪音的概念页（basename，不含 .md）
NOISE = [
    # ① 畸形链接产物：链接写成 [["R-XXX-..."]] 带引号，解析器误建
    '"R-HG-050-董监高任职资格负面清单与上市公司管理层稳定要求"',
    '"R-LN-027-实习律师接案须先评估可诉性与诉讼价值并区分一般与特别授权"',
    '"R-LN-028-小额诉讼标的额三档适用标准与一审终审审限举证期限规则"',
    '"R-LN-029-实习律师应建案件管理台账与电子卷宗并全程工作留痕防范执业过失"',
    '"R-PI-164-道交和解不丧失医疗损害诉权多因一果按份责任损失填平"',
    # ② 违反护栏：纯数字、占位符
    "033",
    "规则名",
    # ③ 有同名真实笔记的冗余副本
    "王德明担保合同纠纷案-案件笔记",
    "罗江辉诉易思立达教育培训合同纠纷案-案件笔记",
]

# 明确保留（真概念/待建枢纽），列出以固化决策、防误移
KEEP = [
    "医疗合规", "病历管理", "公益辨析",
    "合同相对性-包工包料-业主不担责",
    "永康润达诉宁夏燕宝慈善基金会",
    "连接枢纽-公司法",
]


def main():
    os.makedirs(TRASH, exist_ok=True)
    moved, missing = [], []
    for b in NOISE:
        src = os.path.join(CP, b + ".md")
        if not os.path.exists(src):
            missing.append(b)
            continue
        dst = os.path.join(TRASH, b + ".md")
        shutil.move(src, dst)
        moved.append(b)
        print("  已移入 .trash : %s" % b[:58])

    mf = os.path.join(TRASH, "manifest.txt")
    with io.open(mf, "w", encoding="utf-8") as f:
        f.write("# 概念页噪音清理 manifest\n")
        f.write("# 日期  : 2026-08-30\n")
        f.write("# 判据  : 真实笔记入链 = 0（移走零断链风险）\n")
        f.write("# 回滚  : mv 概念页/.trash-2026-08-30/*.md 概念页/\n")
        f.write("# 全量备份: ~/WorkBuddy/Backups/2026-08-30_概念页清理前/\n")
        f.write("\n## 已移入（%d 个）\n" % len(moved))
        for b in moved:
            f.write("  %s\n" % b)
        f.write("\n## 明确保留（真概念/待建枢纽，零入链但不动，%d 个）\n" % len(KEEP))
        for b in KEEP:
            f.write("  %s\n" % b)
        if missing:
            f.write("\n## 未找到（跳过）\n")
            for b in missing:
                f.write("  %s\n" % b)

    print()
    print("=== 完成 ===")
    print("  已移入 .trash : %d 个" % len(moved))
    print("  未找到(跳过)  : %d 个" % len(missing))
    print("  明确保留      : %d 个" % len(KEEP))
    print("  manifest      : %s" % mf)


if __name__ == "__main__":
    main()
