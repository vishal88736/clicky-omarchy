"""Transactional SQLite history, drafts and explicit context references."""
import os
import sqlite3
import uuid
from pathlib import Path
from .config import private_dir


class Store:
    def __init__(self,directory=None):
        directory=private_dir(directory or os.environ.get("CLICKY_DATA_HOME",Path.home()/".local/share/clicky"))
        path=directory/"history.sqlite3"
        if path.is_symlink(): raise ValueError("Refusing symlink history database")
        self.db=sqlite3.connect(path);path.chmod(0o600);self.db.row_factory=sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON");self.db.execute("PRAGMA journal_mode=WAL");self.db.execute("PRAGMA busy_timeout=5000")
        version=self.db.execute("PRAGMA user_version").fetchone()[0]
        if version>1: raise ValueError("History schema is newer than this application")
        if not version:
            self.db.executescript("""
            BEGIN IMMEDIATE;
            CREATE TABLE conversations(id TEXT PRIMARY KEY,title TEXT NOT NULL,draft TEXT NOT NULL DEFAULT '',updated TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
            CREATE TABLE messages(id INTEGER PRIMARY KEY,conversation TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,role TEXT NOT NULL,content TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'complete',created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
            CREATE TABLE selections(conversation TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,message INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,PRIMARY KEY(conversation,message));
            CREATE TABLE events(id INTEGER PRIMARY KEY,conversation TEXT REFERENCES conversations(id) ON DELETE CASCADE,kind TEXT NOT NULL,tool TEXT NOT NULL,status TEXT NOT NULL,created TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')));
            CREATE INDEX messages_conversation ON messages(conversation,id);
            PRAGMA user_version=1;
            COMMIT;
            """)
        with self.db: self.db.execute("UPDATE messages SET status='interrupted' WHERE status='streaming'")

    def close(self): self.db.close()
    def conversations(self,search=""):
        return [dict(r) for r in self.db.execute("SELECT * FROM conversations WHERE instr(lower(title),lower(?))>0 OR id IN (SELECT conversation FROM messages WHERE instr(lower(content),lower(?))>0) ORDER BY updated DESC",(search,search))]
    def new(self,title="New conversation"):
        cid=uuid.uuid4().hex
        with self.db: self.db.execute("INSERT INTO conversations(id,title) VALUES (?,?)",(cid,title))
        return cid
    def messages(self,cid): return [dict(r) for r in self.db.execute("SELECT * FROM messages WHERE conversation=? ORDER BY id",(cid,))]
    def message(self,mid):
        r=self.db.execute("SELECT * FROM messages WHERE id=?",(mid,)).fetchone()
        if not r: raise ValueError("Message no longer exists")
        return dict(r)
    def add(self,cid,role,content,status="complete"):
        with self.db:
            c=self.db.execute("INSERT INTO messages(conversation,role,content,status) VALUES (?,?,?,?)",(cid,role,content,status))
            self.db.execute("UPDATE conversations SET updated=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id=?",(cid,))
            if role=="user": self.db.execute("UPDATE conversations SET title=? WHERE id=? AND title='New conversation'",(content[:64],cid))
        return c.lastrowid
    def update(self,mid,content,status):
        with self.db: self.db.execute("UPDATE messages SET content=?,status=? WHERE id=?",(content,status,mid))
    def draft(self,cid,text):
        with self.db: self.db.execute("UPDATE conversations SET draft=? WHERE id=?",(text[:100000],cid))
    def selections(self,cid):
        return [dict(r) for r in self.db.execute("SELECT m.*,c.title FROM selections s JOIN messages m ON m.id=s.message JOIN conversations c ON c.id=m.conversation WHERE s.conversation=? ORDER BY m.id",(cid,))]
    def select(self,cid,mid,enabled):
        m=self.message(mid)
        if m["conversation"]==cid or m["role"] not in {"user","assistant"} or m["status"]!="complete": raise ValueError("Choose complete messages from a different conversation")
        with self.db:
            if enabled: self.db.execute("INSERT OR IGNORE INTO selections VALUES (?,?)",(cid,mid))
            else: self.db.execute("DELETE FROM selections WHERE conversation=? AND message=?",(cid,mid))
    def fresh_context(self,cid):
        with self.db: self.db.execute("DELETE FROM selections WHERE conversation=?",(cid,))
    def clear(self,cid):
        with self.db:
            self.db.execute("DELETE FROM selections WHERE conversation=?",(cid,));self.db.execute("DELETE FROM messages WHERE conversation=?",(cid,))
            self.db.execute("DELETE FROM events WHERE conversation=?",(cid,));self.db.execute("UPDATE conversations SET draft='',title='New conversation' WHERE id=?",(cid,))
    def event(self,cid,kind,tool,status):
        with self.db: self.db.execute("INSERT INTO events(conversation,kind,tool,status) VALUES (?,?,?,?)",(cid,kind,tool,status))
    def events(self,cid): return [dict(r) for r in self.db.execute("SELECT * FROM events WHERE conversation=? ORDER BY id DESC LIMIT 100",(cid,))]
