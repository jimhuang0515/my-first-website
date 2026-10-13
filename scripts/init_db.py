import sys
from pathlib import Path
import psycopg
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app.db import Base,engine
Base.metadata.create_all(engine)
if engine.url.host in ('127.0.0.1','localhost') and engine.url.database=='stockdev':
    with psycopg.connect('postgresql://stockdev:stockdev@127.0.0.1:5432/postgres',autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname = %s",('stocktest',)).fetchone():
            c.execute('CREATE DATABASE stocktest')
print('Database schema ready; existing data preserved.')
