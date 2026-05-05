"""
LeadRadar Bremen – Backend API (Cloud-Version)
Scheduler läuft als Hintergrund-Thread direkt mit.
"""

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import sqlite3, json, os, threading
from datetime import datetime

app = Flask(__name__, static_folder='static')
CORS(app)
DB_PATH = os.environ.get('DB_PATH', 'data/leads.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs('data', exist_ok=True)
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT, source TEXT, source_label TEXT,
        title TEXT, description TEXT, location TEXT, plz TEXT, score INTEGER DEFAULT 0,
        signals TEXT, outreach TEXT, url TEXT, raw_data TEXT,
        is_hot INTEGER DEFAULT 0, is_contacted INTEGER DEFAULT 0,
        is_archived INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS mietpreis (
        id INTEGER PRIMARY KEY AUTOINCREMENT, plz TEXT UNIQUE, area TEXT,
        miete_avg REAL, kauf_rate_avg REAL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit(); conn.close()

@app.route('/api/leads')
def get_leads():
    source = request.args.get('source','alle')
    sf = request.args.get('score_filter','alle')
    sort = request.args.get('sort','score')
    q = 'SELECT * FROM leads WHERE is_archived=0'
    p = []
    if source != 'alle': q += ' AND source=?'; p.append(source)
    if sf=='hot': q += ' AND score>=80'
    elif sf=='mid': q += ' AND score>=50 AND score<80'
    elif sf=='low': q += ' AND score<50'
    q += {'score':' ORDER BY score DESC','date':' ORDER BY created_at DESC','source':' ORDER BY source'}.get(sort,' ORDER BY score DESC')
    conn = get_db()
    rows = [dict(r) for r in conn.execute(q,p).fetchall()]
    conn.close()
    for r in rows: r['signals']=json.loads(r['signals'] or '[]')
    return jsonify({'leads':rows,'count':len(rows)})

@app.route('/api/leads/<int:lid>/contact', methods=['POST'])
def contact(lid):
    conn=get_db(); conn.execute('UPDATE leads SET is_contacted=1,updated_at=? WHERE id=?',[datetime.now().isoformat(),lid]); conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/leads/<int:lid>/archive', methods=['POST'])
def archive(lid):
    conn=get_db(); conn.execute('UPDATE leads SET is_archived=1,updated_at=? WHERE id=?',[datetime.now().isoformat(),lid]); conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/leads', methods=['POST'])
def add_lead():
    d=request.json; conn=get_db()
    conn.execute('INSERT INTO leads (source,source_label,title,description,location,plz,score,signals,outreach,url,raw_data,is_hot) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        [d.get('source'),d.get('source_label'),d.get('title'),d.get('description'),d.get('location'),d.get('plz'),d.get('score',0),
         json.dumps(d.get('signals',[])),d.get('outreach'),d.get('url'),json.dumps(d.get('raw_data',{})),1 if d.get('score',0)>=80 else 0])
    conn.commit(); conn.close(); return jsonify({'success':True})

@app.route('/api/stats')
def stats():
    conn=get_db()
    t=conn.execute('SELECT COUNT(*) FROM leads WHERE is_archived=0').fetchone()[0]
    h=conn.execute('SELECT COUNT(*) FROM leads WHERE score>=80 AND is_archived=0').fetchone()[0]
    a=conn.execute('SELECT AVG(score) FROM leads WHERE is_archived=0').fetchone()[0]
    n=conn.execute("SELECT COUNT(*) FROM leads WHERE date(created_at)=date('now') AND is_archived=0").fetchone()[0]
    w=conn.execute("SELECT COUNT(*) FROM leads WHERE source='wett' AND is_archived=0").fetchone()[0]
    m=conn.execute('SELECT COUNT(*) FROM mietpreis WHERE miete_avg>kauf_rate_avg').fetchone()[0]
    conn.close()
    return jsonify({'total_leads':t,'hot_leads':h,'avg_score':round(a or 0),'new_today':n,'wettbewerber':w,'miet_alerts':m})

@app.route('/api/mietpreis')
def mietpreis():
    conn=get_db(); rows=[dict(r) for r in conn.execute('SELECT * FROM mietpreis ORDER BY (miete_avg-kauf_rate_avg) DESC').fetchall()]; conn.close(); return jsonify(rows)

@app.route('/api/scrape/all', methods=['POST'])
def scrape_all():
    import subprocess, sys
    scrapers=['scrapers/baugenehmigungen.py','scrapers/handelsregister.py','scrapers/kleinanzeigen.py',
              'scrapers/wg_gesucht.py','scrapers/schwarzesbrett.py','scrapers/wettbewerber.py','scrapers/mietpreis.py']
    results=[]
    for s in scrapers:
        try: subprocess.Popen([sys.executable,s]); results.append({'script':s,'status':'gestartet'})
        except Exception as e: results.append({'script':s,'status':'Fehler','error':str(e)})
    return jsonify({'results':results})

@app.route('/health')
def health(): return jsonify({'status':'ok','time':datetime.now().isoformat()})

@app.route('/')
def index(): return send_from_directory('static','index.html')

def start_scheduler():
    import schedule, time, subprocess, sys
    def run(s): 
        try: subprocess.Popen([sys.executable,s])
        except: pass
    schedule.every(4).hours.do(run,'scrapers/kleinanzeigen.py')
    schedule.every(6).hours.do(run,'scrapers/wg_gesucht.py')
    schedule.every().day.at("08:00").do(run,'scrapers/baugenehmigungen.py')
    schedule.every().day.at("08:15").do(run,'scrapers/handelsregister.py')
    schedule.every().day.at("09:00").do(run,'scrapers/wettbewerber.py')
    schedule.every(12).hours.do(run,'scrapers/schwarzesbrett.py')
    schedule.every().monday.at("07:00").do(run,'scrapers/mietpreis.py')
    while True: schedule.run_pending(); time.sleep(60)

if __name__=='__main__':
    init_db()
    threading.Thread(target=start_scheduler,daemon=True).start()
    port=int(os.environ.get('PORT',5000))
    print(f"\n🎯 LeadRadar Bremen · Port {port}")
    app.run(host='0.0.0.0',port=port,debug=False)
