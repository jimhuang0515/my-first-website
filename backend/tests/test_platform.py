from datetime import timedelta
import httpx
import pytest
from sqlalchemy import select
from app.db import SessionLocal,User,SessionToken,now
from app.market import provider,number,trading_date

BODY={'email':'reader@example.com','password':'strong-password-123'}
def register(client,email=BODY['email']):
    r=client.post('/api/v1/auth/register',json={**BODY,'email':email});assert r.status_code==201
    return r

@pytest.mark.parametrize('query,symbol,exchange',[('台積','2330','TWSE'),('2330','2330','TWSE'),('環球晶','6488','TPEX'),('6488','6488','TPEX')])
def test_search_both_markets(client,query,symbol,exchange):
    rows=client.get('/api/v1/stocks',params={'q':query}).json()['data']
    assert len(rows)==1 and rows[0]['symbol']==symbol and rows[0]['exchange']==exchange

def test_search_empty_unknown_and_length(client):
    assert len(client.get('/api/v1/stocks').json()['data'])==5
    assert client.get('/api/v1/stocks?q=不存在').json()['data']==[]
    assert client.get('/api/v1/stocks',params={'q':'x'*51}).status_code==422

@pytest.mark.parametrize('symbol',['2330','6488'])
def test_quote_candles_consistent(client,symbol):
    q=client.get(f'/api/v1/stocks/{symbol}/quote').json();bars=client.get(f'/api/v1/stocks/{symbol}/candles').json()
    assert q['mode']=='demo' and '虛構' in q['source']
    assert q['data']['close']==bars['data'][-1]['close']
    assert q['data']['date']==bars['data'][-1]['date']
    dates=[r['date'] for r in bars['data']]
    assert dates==sorted(set(dates)) and len(dates)>30
    assert all(r['low']<=min(r['open'],r['close'])<=max(r['open'],r['close'])<=r['high'] for r in bars['data'])

def test_symbol_and_month_validation(client):
    assert client.get('/api/v1/stocks/abcd/quote').status_code==422
    assert client.get('/api/v1/stocks/9999/quote').status_code==404
    assert client.get('/api/v1/stocks/2330/candles?months=7').status_code==422

def test_candles_respects_requested_months(client):
    rows=client.get('/api/v1/stocks/2330/candles?months=1').json()['data']
    assert rows and all(row['date'].startswith('2025-01-') for row in rows)

@pytest.mark.parametrize('raw,value',[('1,000.5',1000.5),('--',None),('NaN',None),('Infinity',None)])
def test_number(raw,value): assert number(raw)==value

@pytest.mark.parametrize('raw',['114/01/20','1140120','20250120'])
def test_date(raw): assert trading_date(raw)=='2025-01-20'

def test_financials_units_period(client):
    r=client.get('/api/v1/stocks/2330/financials').json()['data'][0]
    assert r['year']==2024 and r['quarter']==3 and r['amount_unit']=='TWD 千元' and r['eps']==12.54

def test_institutional_sign_and_unit(client):
    r=client.get('/api/v1/stocks/6488/institutional-flows').json()['data'][0]
    assert r['unit']=='股' and r['investment_trust']<0
    assert r['total']==r['foreign']+r['investment_trust']+r['dealer']

def test_news_demo_no_fabricated_link(client):
    r=client.get('/api/v1/stocks/2330/news').json()['data'][0]
    assert r['url'] is None and '虛構' in r['title']

def test_live_failure_never_falls_back(client,monkeypatch):
    provider.mode='live'
    def failed(*a,**kw): raise httpx.ConnectError('blocked')
    monkeypatch.setattr(httpx,'get',failed)
    assert client.get('/api/v1/stocks?q=2330').status_code==503

def test_otc_lot_conversion(client,monkeypatch):
    provider.mode='live'
    monkeypatch.setattr(provider,'catalog',lambda:[{'symbol':'6488','name':'環球晶','exchange':'TPEX'}])
    monkeypatch.setattr(provider,'fetch',lambda *a,**kw:{'stat':'ok','tables':[{'fields':['日期','成交張數','金額','開','高','低','收'],'data':[['115/09/01','12,770','0','908','998','908','994']]}]})
    rows=client.get('/api/v1/stocks/6488/candles?months=1').json()['data']
    assert rows[0]['volume']==12770000 and rows[0]['close']==994

def test_registration_password_session_and_logout(client):
    assert client.get('/api/v1/auth/me').status_code==401
    r=register(client);assert 'HttpOnly' in r.headers['set-cookie'] and 'SameSite=lax' in r.headers['set-cookie']
    token=client.cookies['stock_session']
    with SessionLocal() as db:
        assert db.scalar(select(User)).password_hash.startswith('$argon2id$')
        assert db.scalar(select(SessionToken)).token_hash!=token
    assert client.get('/api/v1/auth/me').json()['email']==BODY['email']
    assert client.post('/api/v1/auth/logout').status_code==204
    client.cookies.set('stock_session',token)
    assert client.get('/api/v1/auth/me').status_code==401
    client.cookies.clear();assert client.post('/api/v1/auth/login',json=BODY).status_code==200

def test_auth_validation_duplicate_and_expiry(client):
    register(client)
    assert client.post('/api/v1/auth/register',json=BODY).status_code==409
    assert client.post('/api/v1/auth/login',json={**BODY,'password':'wrong-password-123'}).status_code==401
    assert client.post('/api/v1/auth/register',json={**BODY,'password':'short'}).status_code==422
    with SessionLocal() as db:
        db.scalar(select(SessionToken)).expires_at=now()-timedelta(seconds=1);db.commit()
    assert client.get('/api/v1/auth/me').status_code==401

def test_origin_and_rate_limit(client):
    assert client.post('/api/v1/auth/register',json=BODY,headers={'Origin':'https://evil.example'}).status_code==403
    for _ in range(10): assert client.post('/api/v1/auth/login',json=BODY).status_code==401
    assert client.post('/api/v1/auth/login',json=BODY).status_code==429

def test_watchlist_persistence_duplicates_privacy(client):
    assert client.get('/api/v1/watchlist').status_code==401
    register(client)
    for _ in range(2): assert client.put('/api/v1/watchlist/6488').status_code==200
    assert len(client.get('/api/v1/watchlist').json()['data'])==1
    client.post('/api/v1/auth/logout');register(client,'other@example.com')
    assert client.get('/api/v1/watchlist').json()['data']==[]
    client.delete('/api/v1/watchlist/6488');client.post('/api/v1/auth/logout')
    client.post('/api/v1/auth/login',json=BODY)
    assert client.get('/api/v1/watchlist').json()['data'][0]['symbol']=='6488'
    client.delete('/api/v1/watchlist/6488');assert client.get('/api/v1/watchlist').json()['data']==[]

def test_ai_missing_key_requires_login(client,monkeypatch):
    assert client.post('/api/v1/stocks/2330/analyses').status_code==401
    register(client);monkeypatch.delenv('STOCK_AI_API_KEY',raising=False)
    assert client.post('/api/v1/stocks/2330/analyses').status_code==503
    assert client.get('/api/v1/stocks/2330/analyses').json()['data']==[]

def test_ai_success_evidence_and_private_history(client,monkeypatch):
    register(client);monkeypatch.setenv('STOCK_AI_API_KEY','not-a-real-key')
    def response(*a,**kw):
        assert kw['json']['store'] is False and '"data_mode": "demo"' in kw['json']['input']
        return httpx.Response(200,json={'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':'虛構展示資料分析，不能用於投資決策。'}]}]},request=httpx.Request('POST',a[0]))
    monkeypatch.setattr(httpx,'post',response)
    r=client.post('/api/v1/stocks/2330/analyses');assert r.status_code==201 and r.json()['evidence']['quote']['data']['date']=='2025-01-20'
    assert len(client.get('/api/v1/stocks/2330/analyses').json()['data'])==1
    client.post('/api/v1/auth/logout');register(client,'other@example.com')
    assert client.get('/api/v1/stocks/2330/analyses').json()['data']==[]

def test_ai_failure_and_limit(client,monkeypatch):
    register(client);monkeypatch.setenv('STOCK_AI_API_KEY','not-a-real-key')
    def fail(*a,**kw): raise httpx.ReadTimeout('timeout')
    monkeypatch.setattr(httpx,'post',fail)
    for _ in range(3): assert client.post('/api/v1/stocks/2330/analyses').status_code==502
    assert client.post('/api/v1/stocks/2330/analyses').status_code==429
    assert client.get('/api/v1/stocks/2330/analyses').json()['data']==[]
