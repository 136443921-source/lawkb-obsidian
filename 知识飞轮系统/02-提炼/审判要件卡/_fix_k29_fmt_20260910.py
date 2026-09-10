# -*- coding: utf-8 -*-
import io
P="/Users/chenyouqiang/.workbuddy/skills/审判要件卡拆卡流水线/SKILL.md"
s=io.open(P,encoding="utf-8").read()
old="### 29. 🔴🔴 自动化 prompt 里的「待拆清单」是**静态快照**——开工第一步必须查库判状态，不能直接开拆（2026-09-10 实证）"
new="29. **🔴🔴 自动化 prompt 里的「待拆清单」是静态快照——开工第一步必须查库判状态，不能直接开拆（2026-09-10 实证）**"
assert s.count(old)==1, "anchor: %d"%s.count(old)
s=s.replace(old,new)
io.open(P,"w",encoding="utf-8").write(s)
print("FMT OK")
