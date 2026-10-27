# -*- coding: utf-8 -*-
"""Standalone Saudi-only dashboard. Secrets never included in HTML."""
import os, subprocess, sys, threading, json, csv, io
from pathlib import Path
from datetime import date
from flask import Flask, jsonify, render_template_string, request, Response
from sqlalchemy import create_engine,text
BASE=Path(__file__).resolve().parent
DATA_DIR=Path(os.environ.get('DATA_DIR',str(BASE))).resolve()
DATA_DIR.mkdir(parents=True,exist_ok=True)
OUT=DATA_DIR/'SAUDI_PGG_RESULTS'
app=Flask(__name__)
app.json.ensure_ascii=False
RUN_LOCK=threading.Lock()
STATUS={'running':False,'message':'جاهز','success':None}
FIELDS=['symbol','signal_date','close','purple_sessions','gray_sessions','sequence_sessions','purple_min_rps','peak_after','peak_date','peak_gain_pct','sessions_to_peak','latest_close']
def db():
    if not os.environ.get('DATABASE_URL'):raise RuntimeError('DATABASE_URL is missing')
    return create_engine(os.environ['DATABASE_URL'],pool_pre_ping=True)
@app.get('/health')
def health():return {'ok':True,'market':'SA','strategy':'PGG'}
@app.get('/api/status')
def status():
    info=dict(STATUS)
    try:
        e=db()
        with e.connect() as c:
            tables=[r[0] for r in c.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' AND tablename IN ('sa_tv_stocks_1d','sa_tv_indices_1d')"))]
            if len(tables)<2:
                info.update(ready=False,message='بيانات السعودية غير محمّلة بعد',symbols=0,latest=None)
            else:
                n,latest=c.execute(text('SELECT count(DISTINCT symbol),max(session_date) FROM public.sa_tv_stocks_1d')).one()
                index_count=c.execute(text("SELECT count(*) FROM public.sa_tv_indices_1d WHERE symbol='TASI'")).scalar()
                info.update(ready=bool(n and index_count),symbols=n,latest=str(latest) if latest else None,tasi_rows=index_count)
        e.dispose()
    except Exception as ex:info.update(ready=False,error=str(ex)[:180])
    return jsonify(info)
@app.get('/api/results')
def results():
    f=OUT/'ALL_MARKET_SIGNALS.csv'
    if not f.exists():return jsonify(rows=[],count=0)
    with f.open(encoding='utf-8-sig',newline='') as h:rows=list(csv.DictReader(h))
    start=request.args.get('start','2024-01-01');end=request.args.get('end','2099-12-31')
    q=request.args.get('symbol','').upper().strip()
    rows=[r for r in rows if start<=r.get('signal_date','')<=end and q in r.get('symbol','').upper()]
    rows.sort(key=lambda r:(r['signal_date'],r['symbol']),reverse=True)
    return jsonify(rows=rows,count=len(rows))
@app.get('/api/export')
def export():
    data=results().get_json()
    buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader();writer.writerows(data['rows'])
    return Response('\ufeff'+buf.getvalue(),mimetype='text/csv',headers={'Content-Disposition':'attachment; filename=saudi_signals.csv'})
@app.post('/api/scan')
def scan():
    # Operational endpoints MUST be restricted; no public open scans.
    secret=os.environ.get('SCAN_ADMIN_TOKEN','')
    if not secret or request.headers.get('X-Admin-Token')!=secret:return jsonify(error='الفحص الإداري غير متاح من الواجهة العامة'),403
    payload=request.get_json(silent=True) or {}
    try:
        rs=int(payload.get('rs',29));fast=int(payload.get('fast',18));slow=int(payload.get('slow',29))
        assert 20<=rs<=150 and 3<=fast<=30 and 20<=slow<=150 and fast<slow
    except (ValueError,TypeError,AssertionError):return jsonify(error='إعدادات غير صالحة'),400
    if not RUN_LOCK.acquire(blocking=False):return jsonify(error='فحص جارٍ'),409
    def job():
        STATUS.update(running=True,success=None,message='جارٍ الفحص')
        try:
            cmd=[sys.executable,str(BASE/'saudi_pgg_scan.py'),'--rs',str(rs),'--ma-fast',str(fast),'--ma-slow',str(slow),'--output',str(OUT)]
            r=subprocess.run(cmd,capture_output=True,text=True,timeout=1800,cwd=BASE,env=os.environ.copy())
            STATUS.update(success=r.returncode==0,message=(r.stdout if r.returncode==0 else r.stderr)[-220:])
        except Exception as ex:STATUS.update(success=False,message=str(ex)[:220])
        finally:STATUS['running']=False;RUN_LOCK.release()
    threading.Thread(target=job,daemon=True).start()
    return jsonify(ok=True,message='بدأ الفحص')
@app.get('/')
def index():return render_template_string(PAGE)
PAGE=r"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>نظام القوة النسبية لسوق المال السعودي</title><style>
:root{color-scheme:dark}*{box-sizing:border-box}body{margin:0;background:#0d1728;color:#f1f5ff;font-family:Tahoma,Arial,sans-serif}header{padding:23px 3%;background:#132238;border-bottom:1px solid #2b4765}h1{margin:0;font-size:26px}.wrap{padding:20px 3%}.panel{background:#15243b;border:1px solid #314662;border-radius:12px;padding:20px;margin-bottom:18px}h2{margin:0 0 16px}p{line-height:1.85}.controls{display:flex;flex-wrap:wrap;gap:12px;align-items:end}label{display:flex;flex-direction:column;gap:7px;color:#a6c5f3;font-size:13px}input{padding:12px;border-radius:8px;border:1px solid #324e70;background:#0e1b2f;color:white;font-size:15px}button,a.btn{padding:12px 16px;border:1px solid #396389;border-radius:8px;background:#117f70;color:white;cursor:pointer;text-decoration:none;font-size:15px}button.secondary,a.btn{background:#1e3553}button:disabled{opacity:.45;cursor:not-allowed}.muted{color:#9cb4d4}.notice{color:#efca83}table{border-collapse:collapse;width:100%;font-size:13px;text-align:right}th,td{padding:12px 10px;border-bottom:1px solid #273c57;white-space:nowrap}th{background:#233a57}tr.gold{background:#51401c}tr.blue{background:#164058}.tableframe{width:100%;overflow-x:auto}small{font-size:12px}
</style></head><body><header><h1>نظام القوة النسبية لسوق المال السعودي</h1></header><main class="wrap">
<section class="panel"><h2>عن النظام</h2><p>نظام تحليلي متخصص في رصد فرص الأسهم بالسوق المالية السعودية باستخدام القوة النسبية وحركة الأسعار.<br>يعتمد على تحليل المراحل السعرية لاكتشاف التحولات المحتملة من الضعف إلى التجميع ثم الصعود.<br>يعرض فرص الشراء المحتملة وأداء الإشارات التاريخية خلال 52 أسبوعًا من ظهورها.</p></section>
<section class="panel"><h2>حالة بيانات تداول السعودية</h2><div id="state" class="notice">جارٍ التحقق من البيانات...</div><small class="muted">الأسهم ومؤشر TASI في قاعدة سعودية مستقلة. لا تُنشأ أسعار أو جلسات غير موجودة.</small></section>
<section class="panel"><h2>إعدادات المؤشرات</h2><div class="controls"><label>قيمة مؤشر القوة النسبية (RS)<input id="rs" type="number" min="20" max="150" value="29"></label><label>متوسط حسابي قصير المدى<input id="fast" type="number" min="3" max="30" value="18"></label><label>متوسط حسابي طويل المدى<input id="slow" type="number" min="20" max="150" value="29"></label><button class="secondary" onclick="reset()">استعادة الافتراضي</button></div><p class="muted">القيم الافتراضية: RS 29 / قصير 18 / طويل 29. يجب أن يكون المتوسط القصير أقل من الطويل. الإعدادات هنا للعرض؛ تنفيذ الفحص الإداري يتطلب صلاحية محمية.</p></section>
<section class="panel"><h2>إشارات السوق السعودي</h2><div class="controls"><label>من تاريخ<input id="start" type="date" value="2024-01-01"></label><label>إلى تاريخ<input id="end" type="date" value="2026-10-27"></label><label>بحث سهم<input id="symbol" placeholder="مثال 2222"></label><button onclick="load()">عرض النتائج</button><a class="btn secondary" id="csv" href="/api/export">تصدير CSV</a></div><p id="count" class="muted">لم تُحمّل النتائج بعد</p><div class="tableframe"><table><thead><tr><th>التاريخ</th><th>السهم</th><th>سعر الشراء المقترح</th><th>مدة التداول الضعيف</th><th>جلسات التجميع</th><th>مدة النمط</th><th>القاع</th><th>أعلى سعر</th><th>القمة</th><th>صعود 52أ %</th><th>جلسات القمة</th><th>آخر سعر</th></tr></thead><tbody id="rows"></tbody></table></div></section>
</main><script>
const ids=['rs','fast','slow'];function reset(){ids.forEach((id,i)=>document.getElementById(id).value=[29,18,29][i]);}
function val(r,k){return String(r[k]??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;')}
async function status(){try{const d=await(await fetch('/api/status')).json();document.getElementById('state').textContent=d.ready?`جاهز — ${d.symbols} سهم — أحدث جلسة ${d.latest} — TASI: ${d.tasi_rows} جلسة`:(d.error||d.message||'لا توجد بيانات')}catch(e){document.getElementById('state').textContent='تعذّر قراءة حالة القاعدة'}}
async function load(){const q=new URLSearchParams({start:document.getElementById('start').value,end:document.getElementById('end').value,symbol:document.getElementById('symbol').value});const d=await(await fetch('/api/results?'+q)).json();document.getElementById('csv').href='/api/export?'+q;document.getElementById('count').textContent=d.count+' إشارة';const freq={};d.rows.forEach(r=>freq[r.signal_date]=(freq[r.signal_date]||0)+1);let prev='',group=-1;const keys=['signal_date','symbol','close','purple_sessions','gray_sessions','sequence_sessions','purple_min_rps','peak_after','peak_date','peak_gain_pct','sessions_to_peak','latest_close'];document.getElementById('rows').innerHTML=d.rows.map(r=>{if(r.signal_date!==prev){prev=r.signal_date;if(freq[prev]>1)group++}return '<tr class="'+(freq[r.signal_date]>1?(group%2?'blue':'gold'):'')+'">'+keys.map(k=>'<td>'+val(r,k)+'</td>').join('')+'</tr>'}).join('')}
status();load();
</script></body></html>"""
