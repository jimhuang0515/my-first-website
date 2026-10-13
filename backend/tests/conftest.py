import os
os.environ['DATABASE_URL']=os.getenv('TEST_DATABASE_URL','postgresql+psycopg://stockdev:stockdev@127.0.0.1:5432/stocktest')
os.environ['STOCK_DATA_MODE']='demo'
import pytest
from fastapi.testclient import TestClient
from app.db import Base,engine
from app.main import app,limits,ORIGIN
from app.market import provider

@pytest.fixture
def client():
    assert engine.url.database and engine.url.database.endswith('test')
    Base.metadata.drop_all(engine)
    provider.mode='demo';provider.cache.clear();limits.clear()
    with TestClient(app,headers={'Origin':ORIGIN}) as c:
        yield c
