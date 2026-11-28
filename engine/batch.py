"""Single-worker durable batch queue. Completion means review, not approval."""
import hashlib,json,sqlite3,time
from pathlib import Path

class Batch:
    def __init__(self,root):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)
        self.db=sqlite3.connect(self.root/'queue.sqlite')
        self.db.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER DEFAULT 0, error TEXT)')
        self.db.commit()
    def close(self):
        self.db.close()
    def add(self,name,image,fields=None,seeds=()):
        data=Path(image).read_bytes()
        if len(data)>10000000: raise ValueError('INPUT_SIZE_LIMIT')
        payload=dict(name=name,sha256=hashlib.sha256(data).hexdigest(),fields=fields or {},seeds=list(seeds))
        encoded=json.dumps(payload,sort_keys=True,ensure_ascii=False)
        key=hashlib.sha256(encoded.encode()).hexdigest()
        folder=self.root/key
        folder.mkdir(exist_ok=True)
        (folder/'reference.bin').write_bytes(data)
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO jobs(id,payload,state) VALUES(?,?,'PENDING')",(key,encoded))
        return key
    def run(self,processor,limit=100,max_attempts=3):
        if not 1<=limit<=100 or not 1<=max_attempts<=10: raise ValueError('INVALID_LIMIT')
        # Explicit single-worker contract: do not run concurrent instances.
        with self.db:
            self.db.execute("UPDATE jobs SET state='FAILED',error='INTERRUPTED' WHERE state='RUNNING'")
        rows=self.db.execute("SELECT id,payload FROM jobs WHERE state IN ('PENDING','FAILED') AND attempts<? ORDER BY rowid LIMIT ?",(max_attempts,limit)).fetchall()
        for key,encoded in rows:
            with self.db:
                self.db.execute("UPDATE jobs SET state='RUNNING',attempts=attempts+1,error=NULL WHERE id=?",(key,))
            try:
                folder=self.root/key
                payload=json.loads(encoded)
                if hashlib.sha256((folder/'reference.bin').read_bytes()).hexdigest()!=payload['sha256']: raise ValueError('REFERENCE_HASH_MISMATCH')
                start=time.monotonic()
                report=processor(payload,folder)
                report['elapsed_seconds']=time.monotonic()-start
                report['commercial_approved']=False
                temp=folder/'report.tmp'
                temp.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
                temp.replace(folder/'report.json')
                state='REVIEW_REQUIRED' if report.get('status')=='REVIEW_REQUIRED' else 'NO_CANDIDATES' if report.get('status')=='NO_REVIEW_CANDIDATES' else 'IDENTITY_CONFLICT' if report.get('status')=='IDENTITY_CONFLICT' else 'FAILED'
                with self.db:
                    self.db.execute("UPDATE jobs SET state=? WHERE id=?",(state,key))
            except Exception as exc:
                with self.db:
                    self.db.execute("UPDATE jobs SET state='FAILED',error=? WHERE id=?",(str(exc),key))
        return self.summary()
    def summary(self):
        return dict(self.db.execute('SELECT state,count(*) FROM jobs GROUP BY state').fetchall())
