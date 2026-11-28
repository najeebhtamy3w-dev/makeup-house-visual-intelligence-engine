import sqlite3
import json
from contextlib import closing
from .barcode_priority import canonical_gtin

class ProductRegistry:
    def __init__(self,path):
        self.path=str(path)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS products (gtin TEXT PRIMARY KEY, fields TEXT NOT NULL, source TEXT NOT NULL, reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS product_history (id INTEGER PRIMARY KEY, gtin TEXT NOT NULL, fields TEXT NOT NULL, source TEXT NOT NULL, action TEXT NOT NULL, at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")
    def approve(self,barcode,fields,source):
        gtin=canonical_gtin(barcode)
        if not gtin or not isinstance(source,str) or not source.strip() or len(source)>1000:
            raise ValueError('INVALID_REVIEW')
        clean={}
        for k in ('brand','name','size','variant','shade','concentration'):
            v=fields.get(k)
            if v is not None:
                if not isinstance(v,str) or len(v)>200: raise ValueError('INVALID_FIELD')
                if v.strip(): clean[k]=v.strip()
        if not all(clean.get(k) for k in ('brand','name','size')): raise ValueError('INCOMPLETE_IDENTITY')
        clean['gtin']=gtin
        raw=json.dumps(clean,ensure_ascii=False)
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            old=db.execute("SELECT fields FROM products WHERE gtin=?",(gtin,)).fetchone()
            if old and json.loads(old[0])!=clean: raise ValueError('GTIN_CONFLICT_REVOKE_FIRST')
            db.execute("INSERT OR IGNORE INTO products(gtin,fields,source) VALUES(?,?,?)",(gtin,raw,source))
            db.execute("INSERT INTO product_history(gtin,fields,source,action) VALUES(?,?,?,'APPROVE')",(gtin,raw,source))
    def lookup(self,barcode):
        gtin=canonical_gtin(barcode)
        if not gtin: return []
        with closing(sqlite3.connect(self.path)) as db:
            row=db.execute("SELECT fields,source,reviewed_at FROM products WHERE gtin=?",(gtin,)).fetchone()
        return [{'fields':json.loads(row[0]),'source':row[1],'reviewed_at':row[2],'operator_reviewed':True,'publication_allowed':False}] if row else []
    def revoke(self,barcode):
        gtin=canonical_gtin(barcode)
        if not gtin: raise ValueError('INVALID_GTIN')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row=db.execute("SELECT fields,source FROM products WHERE gtin=?",(gtin,)).fetchone()
            if not row: return False
            db.execute("INSERT INTO product_history(gtin,fields,source,action) VALUES(?,?,?,'REVOKE')",(gtin,*row))
            db.execute("DELETE FROM products WHERE gtin=?",(gtin,))
            return True
