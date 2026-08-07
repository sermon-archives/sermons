#!/usr/bin/env python3
"""Push/pull sermon and queue state between local SQLite and Turso."""
import argparse, asyncio, os, sqlite3
from pathlib import Path

def local():
    db=sqlite3.connect('data/sermons.sqlite3'); db.row_factory=sqlite3.Row
    db.executescript(Path('db/schema.sql').read_text()); return db
async def main(pull=False):
    from libsql_client import create_client
    client=create_client(os.environ['TURSO_DATABASE_URL'],auth_token=os.environ['TURSO_AUTH_TOKEN'])
    db=local()
    async with client:
      for statement in Path('db/schema.sql').read_text().split(';'):
        if statement.strip(): await client.execute(statement)
      if pull:
        for table in ('sermons','transcription_queue'):
          rs=await client.execute(f'SELECT * FROM {table}')
          cols=list(rs.columns)
          for values in rs.rows:
            db.execute(f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})",tuple(values))
        db.commit(); print('pulled Turso sermon and queue state')
      else:
        for table in ('sermons','transcription_queue'):
          rows=db.execute(f'SELECT * FROM {table}').fetchall(); cols=[d[0] for d in db.execute(f'SELECT * FROM {table} LIMIT 0').description]
          for row in rows:
            await client.execute(f"INSERT OR REPLACE INTO {table} ({','.join(cols)}) VALUES ({','.join(':'+c for c in cols)})",dict(row))
        print(f'pushed {db.execute("SELECT COUNT(*) FROM sermons").fetchone()[0]} sermons and {db.execute("SELECT COUNT(*) FROM transcription_queue").fetchone()[0]} queue jobs')
    db.close()
if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--pull',action='store_true'); args=ap.parse_args(); asyncio.run(main(args.pull))
