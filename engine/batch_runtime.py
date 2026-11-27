"""Persistent single-worker job queue. Interrupted jobs can be recovered explicitly."""
import sqlite3
import json
import uuid
from pathlib import Path

class BatchRuntime:
    def __init__(self,path):
        self.path=str(path)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, batch TEXT NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, result TEXT, error TEXT)")
    def connect(self):
        return sqlite3.connect(self.path,timeout=15)
    def submit(self,payloads):
        if not 1<=len(payloads)<=100: raise ValueError('BATCH_LIMIT')
        batch=uuid.uuid4().hex
        with self.connect() as db:
            db.executemany("INSERT INTO jobs(id,batch,payload,state) VALUES(?,?,?,'QUEUED')",[(uuid.uuid4().hex,batch,json.dumps(p,ensure_ascii=False)) for p in payloads])
        return batch
    def status(self,batch):
        with self.connect() as db:
            db.row_factory=sqlite3.Row
            rows=db.execute("SELECT * FROM jobs WHERE batch=? ORDER BY rowid",(batch,)).fetchall()
        return [dict(r) for r in rows]
    def run_next(self,handler):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT id,payload FROM jobs WHERE state='QUEUED' ORDER BY rowid LIMIT 1").fetchone()
            if row is None: return None
            job,payload=row
            db.execute("UPDATE jobs SET state='RUNNING',attempts=attempts+1 WHERE id=?",(job,))
        try:
            result=json.dumps(handler(job,json.loads(payload)),ensure_ascii=False,allow_nan=False)
            state,error='COMPLETED',None
        except Exception as exc:
            state,result,error='FAILED',None,type(exc).__name__
        with self.connect() as db:
            db.execute("UPDATE jobs SET state=?,result=?,error=? WHERE id=?",(state,result,error,job))
        return job
    def retry(self,batch):
        with self.connect() as db:
            return db.execute("UPDATE jobs SET state='QUEUED',error=NULL WHERE batch=? AND state='FAILED' AND attempts<3",(batch,)).rowcount
    def recover_interrupted(self):
        # Operator must ensure no worker is active.
        with self.connect() as db:
            return db.execute("UPDATE jobs SET state='FAILED',error='INTERRUPTED' WHERE state='RUNNING'").rowcount
