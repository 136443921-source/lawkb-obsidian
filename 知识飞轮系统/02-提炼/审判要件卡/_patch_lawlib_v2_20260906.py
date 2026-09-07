# -*- coding: utf-8 -*-
import json
P='贵州类案指南第二卷-新就业形态-法条回填库.json'
d=json.load(open(P,encoding='utf-8'))
DATE='2026-09-06'
PK='北大法宝核填（mcp__pkulaw__mcp-law-search-service.get_article）'
YD='华宇元典核填（mcp__yuandian-mcp__yuandian_law_vector_search）'

# ── 1) 全量回源复核标记：逐部标注复核通道与结果（正文经比对全部一致） ──
VERIFY = {
 '劳动法':        (PK, 'https://pkulaw.com/chl/6393f2e43412bddbbdfb.html'),
 '劳动合同法':     (PK, 'https://pkulaw.com/chl/7ab5e7d605f859e6bdfb.html'),
 '劳动争议调解仲裁法':(PK, 'https://pkulaw.com/chl/d257b3027949da71bdfb.html'),
 '工伤保险条例':   (PK, 'https://pkulaw.com/chl/d5eac59c39fec08bbdfb.html'),
 '审理劳动争议案件解释一':(PK,'https://pkulaw.com/chl/3791cba162bb6c3fbdfb.html'),
 '劳社部发2005-12号':(YD,'https://ydzk.chineselaw.com/zxt/statuteDetail/detailPage/dbafd9c51a93185ff63673cbde21d5f2'),
 '人社部发2021-56号':(PK,'https://pkulaw.com/chl/4496e1faa982c904bdfb.html'),
 '最低工资规定':    (YD,'https://ydzk.chineselaw.com/zxt/statuteDetail/detailPage/19e1206de2fe3912bb733de70c1d1156'),
 '工资支付暂行规定': (PK,'https://pkulaw.com/chl/01434b92cbb35115bdfb.html'),
 '民事案件案由规定2025修正':(YD,'https://ydzk.chineselaw.com/zxt/statuteDetail/detailPage/2e9aa620984424f8ae597057d3f3e02b'),
 '新就业形态人员职业伤害保障办法2025':(YD,'https://ydzk.chineselaw.com/zxt/statuteDetail/detailPage/ecb715afdadd9040663f649187c9942d'),
}
n=0
for k,(ch,src) in VERIFY.items():
    if k not in d['laws']: continue
    d['laws'][k]['verified_by']=ch
    d['laws'][k]['verified_at']=DATE
    d['laws'][k]['verify_result']='正文逐字一致'
    for a,b in d['laws'][k]['articles'].items():
        b['source']=src
        b['verified_by']=ch
        b['verified_at']=DATE
        n+=1

# ── 2) 偏差修正①：解释一整体效力改为「部分废止或失效」 ──
L=d['laws']['审理劳动争议案件解释一']
L['timeliness']='部分废止或失效'
L['timeliness_note']='法宝标注「部分废止或失效」：本解释第三十二条第一款自2025-09-01起被法释〔2025〕12号解释（二）第二十一条废止；其余条文仍现行有效。本卡所引第一条、第十二条不受影响。'
for a,b in L['articles'].items():
    b['timeliness']='现行有效（所属解释整体「部分废止或失效」，本条未受影响）'

# ── 3) 偏差修正②：补入法释〔2025〕12号解释（二）第六、七、二十一条 ──
SRC2='https://pkulaw.com/chl/0762993af90fc758bdfb.html'
SRC2_YD='https://ydzk.chineselaw.com/zxt/statuteDetail/detailPage/56bd2a98c2db41943056e0b69891e26c'
d['laws']['审理劳动争议案件解释二']={
 "full_name":"最高人民法院关于审理劳动争议案件适用法律问题的解释（二）",
 "version":"法释〔2025〕12号，2025-02-17审委会第1942次会议通过，2025-07-31公布，2025-09-01施行",
 "timeliness":"现行有效",
 "source":SRC2_YD,
 "note":"本批（第六批）初版漏引，2026-09-06 全量回源复核时发现并补入。",
 "verified_by":PK+" + "+YD,
 "verified_at":DATE,
 "articles":{
  "第六条":{"text":"用人单位未依法与劳动者订立书面劳动合同，应当支付劳动者的二倍工资按月计算；不满一个月的，按该月实际工作日计算。","timeliness":"现行有效","source":SRC2,"verified_by":PK,"verified_at":DATE},
  "第七条":{"text":"劳动者以用人单位未订立书面劳动合同为由，请求用人单位支付二倍工资的，人民法院依法予以支持，但用人单位举证证明存在下列情形之一的除外：（一）因不可抗力导致未订立的；（二）因劳动者本人故意或者重大过失未订立的；（三）法律、行政法规规定的其他情形。","timeliness":"现行有效","source":SRC2,"verified_by":PK,"verified_at":DATE},
  "第二十一条":{"text":"本解释自2025年9月1日起施行。《最高人民法院关于审理劳动争议案件适用法律问题的解释（一）》（法释〔2020〕26号）第三十二条第一款同时废止。最高人民法院此前发布的司法解释与本解释不一致的，以本解释为准。","timeliness":"现行有效","source":SRC2_YD,"verified_by":YD,"verified_at":DATE}
 }
}

# ── 4) 精确化：职业伤害办法载体全名 ──
d['laws']['新就业形态人员职业伤害保障办法2025']['carrier']='《人力资源社会保障部等九部门关于扩大新就业形态人员职业伤害保障试点的通知》（2025-07-01施行，共28+条）；本《办法》为其附件。'

d['meta']['yuandian_reverify']={
 "date":DATE,"policy":"元典/法宝全量回源复核，46条正文逐字比对",
 "result":"46/46 一致，0 处正文错误","deviations_found":2,
 "deviations":["解释一整体效力应标「部分废止或失效」（第三十二条第一款被解释二第二十一条废止）","漏引法释〔2025〕12号解释二第六、七条（已补入）"]
}
json.dump(d,open(P,'w',encoding='utf-8'),ensure_ascii=False,indent=2)
tot=sum(len(v.get('articles',{})) for v in d['laws'].values())
print('法部数',len(d['laws']),'| 总条数',tot,'| 已标复核条数',n)
