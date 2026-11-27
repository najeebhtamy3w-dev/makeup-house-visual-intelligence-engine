"""Persistent single-worker job queue. Interrupted jobs can be recovered explicitly."""
import sqlite3
import json
import uuid
import hashlib
from pathlib import Path

class BatchRuntime:
    def __init__(self,path):
        self.path=str(path)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, batch TEXT NOT NULL, payload TEXT NOT NULL, state TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0, result TEXT, error TEXT)")
            db.execute("CREATE TABLE IF NOT EXISTS submissions (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, batch TEXT NOT NULL)")
    def connect(self):
        return sqlite3.connect(self.path,timeout=15)
    def submit(self,payloads,idempotency_key=None):
        if not 1<=len(payloads)<=100: raise ValueError('BATCH_LIMIT')
        if idempotency_key is not None and (not isinstance(idempotency_key,str) or not 1<=len(idempotency_key)<=128): raise ValueError('INVALID_IDEMPOTENCY_KEY')
        encoded=json.dumps(payloads,ensure_ascii=False,sort_keys=True,allow_nan=False)
        fingerprint=hashlib.sha256(encoded.encode()).hexdigest()
        batch=uuid.uuid4().hex
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if idempotency_key is not None:
                previous=db.execute('SELECT fingerprint,batch FROM submissions WHERE key=?',(idempotency_key,)).fetchone()
                if previous:
                    if previous[0]!=fingerprint: raise ValueError('IDEMPOTENCY_CONFLICT')
                    return previous[1]
            db.executemany("INSERT INTO jobs(id,batch,payload,state) VALUES(?,?,?,'QUEUED')",[(uuid.uuid4().hex,batch,json.dumps(p,ensure_ascii=False)) for p in payloads])
            if idempotency_key is not None:
                db.execute('INSERT INTO submissions(key,fingerprint,batch) VALUES(?,?,?)',(idempotency_key,fingerprint,batch))
        return batch
    def status(self,batch):
        with self.connect() as db:
            db.row_factory=sqlite3.Row
            rows=db.execute("SELECT * FROM jobs WHERE batch=? ORDER BY rowid",(batch,)).fetchall()
        return [dict(r) for r in rows]
    def run_next(self,handler):
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT id,payload,attempts FROM jobs WHERE state='QUEUED' ORDER BY rowid LIMIT 1").fetchone()
            if row is None: return None
            job,payload,attempts=row
            db.execute("UPDATE jobs SET state='RUNNING',attempts=attempts+1 WHERE id=?",(job,))
        try:
            result=json.dumps(handler(job,json.loads(payload)),ensure_ascii=False,allow_nan=False)
            state,error='COMPLETED',None
        except Exception as exc:
            allowed={'IDENTITY_UNAVAILABLE','STUDIO_UNAVAILABLE','SEGMENTER_UNAVAILABLE','INVALID_INPUT_ID','INPUT_NOT_FOUND','INPUT_HASH_MISMATCH','IDENTITY_LOCK_FAILED','HUMAN_MASK_REVIEW_REQUIRED'}
            state,result,error='FAILED',None,str(exc) if str(exc) in allowed else type(exc).__name__
        with self.connect() as db:
            db.execute("UPDATE jobs SET state=?,result=?,error=? WHERE id=? AND state='RUNNING' AND attempts=?",(state,result,error,job,attempts+1))
        return job
    def retry(self,batch):
        with self.connect() as db:
            return db.execute("UPDATE jobs SET state='QUEUED',error=NULL,result=NULL WHERE batch=? AND state IN ('FAILED','CANCELLED') AND attempts<3",(batch,)).rowcount
    def cancel(self,batch):
        # Active handlers finish cooperatively; their output cannot overwrite CANCELLED.
        with self.connect() as db:
            return db.execute("UPDATE jobs SET state='CANCELLED',error=NULL,result=NULL WHERE batch=? AND state IN ('QUEUED','RUNNING')",(batch,)).rowcount
    def recover_interrupted(self):
        # Operator must ensure no worker is active.
        with self.connect() as db:
            return db.execute("UPDATE jobs SET state='FAILED',error='INTERRUPTED' WHERE state='RUNNING'").rowcount
