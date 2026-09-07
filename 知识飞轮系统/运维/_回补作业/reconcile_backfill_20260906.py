import json, datetime, copy, os
SRC='ima_intake_state.json'
d=json.load(open(SRC))
m=json.load(open('运维/_回补作业/2026-09-04/选文清单.json'))
libs=d['libraries']

ADD=[
 ('律师AI助手','R-LN-052','wechatarticle_62fe55a7567bc291dfbbee29900b27c3_5ac1e1519485af2d518bd6fe1ccdb2a07312042960642489','交通肇事罪丨定罪量刑标准及缓刑适用规则'),
 ('律师AI助手','R-LN-053','wechatarticle_62fe55a7567bc291dfbbee29900b27c3_492681b1dd0389b777e30a982a4ee45c7312042960642489','办案手记：损害公司利益责任纠纷裁判规则与理论梳理'),
 ('律师AI助手','R-LN-054','wechatarticle_62fe55a7567bc291dfbbee29900b27c3_812d1c33bd76878abf3a4a0d1fd137427312042960642489','司法介入法定代表人涤除登记的条件'),
 ('合规与政府监管AI助手','R-HG-062','wechatarticle_62fe55a7567bc291dfbbee29900b27c3_490331c6e27158ee4f5c2201fcdfdef17333014572917409','民营企业涉税合规自查手册'),
]
def get_mid(x): return x.get('media_id') if isinstance(x,dict) else x

added=0
for lib,rid,mid,title in ADD:
    lib_id=[it['lib_id'] for it in m[lib]][0]
    arr=libs[lib_id]['ingested']
    ids={get_mid(x) for x in arr}
    if mid in ids:
        print('SKIP already',rid); continue
    ts=int(datetime.datetime(2026,9,4,15,38,tzinfo=datetime.timezone(datetime.timedelta(hours=8))).timestamp()*1000)
    arr.append({'media_id':mid,'title':title,'create_time':ts,'ingested_at':'2026-09-04T15:38','value':7})
    added+=1; print('ADD',rid,'->',lib_id)

tot=sum(len(v.get('ingested',[])) for v in libs.values())
d['totals']['ingested_total']=tot
for k,v in libs.items():
    d['totals']['libraries'][k]=len(v.get('ingested',[]))

for w in d['pending_windows']:
    if w.get('window_id') in ('w_2026-09-03_A1B_channel_down','w_2026-09-04_A1B_channel_down'):
        w['status']='backfilled'; w['total_target']=15; w['total_done']=15
        w.setdefault('backfill_log',[]).append({'at':'2026-09-06T08:39','added':15,'note':'回补对账完成：选文清单45/45全部摄入（41项先前已记入 + 4项补记 R-LN-052/053/054、R-HG-062）；关闭漏窗。','cards':['R-LN-052','R-LN-053','R-LN-054','R-HG-062']})

d['checkpoint']={'session_id':'reconcile-2026-09-06-backfill-close','stage':'FINAL','status':'done','started_at':'2026-09-06T08:39','finished_at':'2026-09-06T08:39','done':['backfill 45/45 closed (09-02/03/04 windows)'],'remaining':{}}
d['updated']='2026-09-06'

print('added=',added,'new ingested_total=',tot)
print('lib counts=',{k:len(v.get('ingested',[])) for k,v in libs.items()})
if os.environ.get('APPLY')=='1':
    json.dump(d,open(SRC,'w'),ensure_ascii=False,indent=2)
    print('APPLIED')
else:
    print('DRY-RUN (set APPLY=1 to write)')
