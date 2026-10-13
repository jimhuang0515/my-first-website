import os
import re
import time
import threading
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
import httpx
from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from fastapi import HTTPException

TWSE = 'https://openapi.twse.com.tw/v1'
TPEX = 'https://www.tpex.org.tw/openapi/v1'
DEMO = [('2330','台積電','TWSE',1000),('2317','鴻海','TWSE',200),('2454','聯發科','TWSE',1300),('6488','環球晶','TPEX',500),('8069','元太','TPEX',250)]

def number(value):
    try:
        n = Decimal(str(value).replace(',', '').replace(' ', ''))
        return float(n) if n.is_finite() else None
    except InvalidOperation:
        return None

def trading_date(raw):
    s = str(raw).strip()
    try:
        if '/' in s or '-' in s:
            y,m,d = map(int, re.split(r'[/\-]',s))
        elif len(s) == 7:
            y,m,d = int(s[:3]),int(s[3:5]),int(s[5:])
        elif len(s) == 8:
            y,m,d = int(s[:4]),int(s[4:6]),int(s[6:])
        else:
            raise ValueError()
        return date(y+1911 if y<1911 else y,m,d).isoformat()
    except (ValueError, TypeError):
        raise HTTPException(502,'資料日期格式不符合預期') from None

class MarketProvider:
    def __init__(self):
        self.mode = os.getenv('STOCK_DATA_MODE','live')
        if self.mode not in ('demo','live'):
            raise RuntimeError('STOCK_DATA_MODE must be live or demo')
        self.cache = {}
        self.locks = {}
        self.guard = threading.Lock()

    def envelope(self, data, source):
        return {'data':data,'mode':self.mode,'source':'固定虛構展示資料（非行情）' if self.mode=='demo' else source,
                'fetched_at':datetime.now(timezone.utc).isoformat()}

    def fetch(self, url, params=None, xml=False):
        key = (url,str(sorted((params or {}).items())),xml)
        with self.guard:
            lock = self.locks.setdefault(key,threading.Lock())
        with lock:
            cached = self.cache.get(key)
            if cached and cached[0]>time.monotonic():
                return cached[1]
            for attempt in range(3):
                try:
                    headers = {'Accept':'application/xml' if xml else 'application/json'}
                    if attempt:
                        headers['Cache-Control']='no-cache'
                    r = httpx.get(url,params=params,headers=headers,timeout=20,follow_redirects=False)
                    if r.status_code in (429,502,503,504) and attempt<2:
                        time.sleep(.25*(attempt+1)); continue
                    r.raise_for_status()
                    if len(r.content)>10000000:
                        raise ValueError('oversized response')
                    result = ElementTree.fromstring(r.content) if xml else r.json()
                    self.cache[key] = (time.monotonic()+300,result)
                    return result
                except (httpx.TransportError, ValueError):
                    if attempt==2: break
                    time.sleep(.25*(attempt+1))
                except (httpx.HTTPError,ElementTree.ParseError,DefusedXmlException):
                    break
            raise HTTPException(503,'資料來源暫時無法使用，請稍後重試')

    def catalog(self):
        if self.mode=='demo':
            return [{'symbol':s,'name':n,'exchange':e} for s,n,e,_ in DEMO]
        result=[]
        for url,code,name,exchange in [(TWSE+'/opendata/t187ap03_L','公司代號','公司簡稱','TWSE'),
                                      (TPEX+'/mopsfin_t187ap03_O','SecuritiesCompanyCode','CompanyAbbreviation','TPEX')]:
            rows=self.fetch(url)
            if not isinstance(rows,list) or not rows:
                raise HTTPException(502,'公司基本資料格式不符合預期')
            for r in rows:
                s=str(r.get(code,'')).strip()
                n=str(r.get(name,'')).strip()
                if re.fullmatch('[0-9]{4,6}',s) and n:
                    result.append({'symbol':s,'name':n,'exchange':exchange})
        if len({r['symbol'] for r in result})!=len(result):
            raise HTTPException(502,'上市／上櫃代號重複，請核對來源')
        return result

    def quote(self,symbol,exchange):
        if self.mode=='demo':
            p=next(p for s,n,e,p in DEMO if s==symbol)
            return self.envelope({'date':'2025-01-20','close':p,'change':p*.0025,'volume':12000000,'currency':'TWD','frequency':'日終'},exchange)
        otc=exchange=='TPEX'
        rows=self.fetch(TPEX+'/tpex_mainboard_quotes' if otc else TWSE+'/exchangeReport/STOCK_DAY_ALL')
        if not isinstance(rows,list): raise HTTPException(502,'行情格式異常')
        row=next((r for r in rows if r.get('SecuritiesCompanyCode' if otc else 'Code')==symbol),None)
        if not row: raise HTTPException(404,'此股票沒有可用的日行情')
        return self.envelope({'date':trading_date(row.get('Date')),'close':number(row.get('Close' if otc else 'ClosingPrice')),
            'change':number(row.get('Change')),'volume':number(row.get('TradingShares' if otc else 'TradeVolume')),
            'currency':'TWD','frequency':'日終'},exchange)

    def candles(self,symbol,exchange,months=3):
        result=[]
        if self.mode=='demo':
            p=next(p for s,n,e,p in DEMO if s==symbol)
            end=date(2025,1,20);start=end.replace(day=1)
            for _ in range(months-1):
                start=(start-timedelta(days=1)).replace(day=1)
            days=[start+timedelta(days=i) for i in range((end-start).days+1) if (start+timedelta(days=i)).weekday()<5]
            for i,d in enumerate(days):
                close=round(p*(1-(len(days)-1-i)*.0025),2);opening=close+(3 if i%2 else -2)
                result.append({'date':d.isoformat(),'open':opening,'high':max(opening,close)+4,'low':min(opening,close)-4,'close':close,'volume':12000000})
            return self.envelope(result,exchange)
        first=datetime.now(timezone(timedelta(hours=8))).date().replace(day=1)
        for _ in range(months):
            otc=exchange=='TPEX'
            body=self.fetch('https://www.tpex.org.tw/www/zh-tw/afterTrading/tradingStock' if otc else 'https://www.twse.com.tw/exchangeReport/STOCK_DAY',
                {'code':symbol,'date':first.strftime('%Y/%m/%d'),'response':'json'} if otc else {'stockNo':symbol,'date':first.strftime('%Y%m%d'),'response':'json'})
            first=(first-timedelta(days=1)).replace(day=1)
            if not isinstance(body,dict): raise HTTPException(502,'K 線格式異常')
            if not otc and body.get('stat')!='OK':
                if '很抱歉' in str(body.get('stat')) or '沒有' in str(body.get('stat')): continue
                raise HTTPException(502,'K 線來源狀態異常')
            if otc:
                if body.get('stat')!='ok': raise HTTPException(502,'上櫃 K 線來源狀態異常')
                tables=body.get('tables',[])
            else:
                tables=[{'data':body.get('data',[])}]
            for table in tables:
                if otc and table.get('data') and (table.get('fields') or [None,None])[1]!='成交張數':
                    raise HTTPException(502,'上櫃成交量單位異常')
                for r in table.get('data',[]):
                    if len(r)<7: raise HTTPException(502,'K 線欄位不足')
                    o,h,l,c=[number(r[i]) for i in (3,4,5,6)]
                    if any(v is None for v in (o,h,l,c)): continue
                    if l>min(o,c) or h<max(o,c): raise HTTPException(502,'OHLC 範圍異常')
                    v=number(r[1])
                    result.append({'date':trading_date(r[0]),'open':o,'high':h,'low':l,'close':c,'volume':v*1000 if otc and v is not None else v})
        return self.envelope(sorted({r['date']:r for r in result}.values(),key=lambda r:r['date']),exchange)

    def financials(self,symbol,exchange):
        if self.mode=='demo':
            return self.envelope([{'year':2024,'quarter':3,'revenue':759692000,'operating_income':360771000,'net_income':325258000,'eps':12.54,'amount_unit':'TWD 千元','period_basis':'來源報告數值，可能為年度累計'}],exchange)
        otc=exchange=='TPEX'
        rows=self.fetch(TPEX+'/mopsfin_t187ap06_O_ci' if otc else TWSE+'/opendata/t187ap06_L_ci')
        if not isinstance(rows,list): raise HTTPException(502,'財報格式異常')
        result=[]
        for r in rows:
            if str(r.get('SecuritiesCompanyCode' if otc else '公司代號','')).strip()!=symbol: continue
            try:
                y=int(r['Year' if otc else '年度']);q=int(r['Season' if otc else '季別'])
                if not 1<=q<=4: raise ValueError()
            except (KeyError,ValueError,TypeError): raise HTTPException(502,'財報報告期間異常') from None
            result.append({'year':y+1911 if y<1911 else y,'quarter':q,'revenue':number(r.get('營業收入')),
                'operating_income':number(r.get('營業利益（損失）')),'net_income':number(r.get('本期淨利（淨損）')),
                'eps':number(r.get('基本每股盈餘（元）')),'amount_unit':'TWD 千元','period_basis':'來源報告數值，可能為年度累計'})
        return self.envelope(sorted(result,key=lambda r:(r['year'],r['quarter']),reverse=True),exchange+' 一般業綜合損益表')

    def institutional(self,symbol,exchange):
        if self.mode=='demo':
            return self.envelope([{'date':'2025-01-20','foreign':2500000,'investment_trust':-300000,'dealer':100000,'total':2300000,'unit':'股'}],exchange)
        if exchange=='TPEX':
            rows=self.fetch(TPEX+'/tpex_3insti_daily_trading')
            if not isinstance(rows,list): raise HTTPException(502,'法人格式異常')
            r=next((r for r in rows if str(r.get('SecuritiesCompanyCode','')).strip()==symbol),None)
            if not r: return self.envelope([],exchange)
            keys=['Foreign Investors include Mainland Area Investors (Foreign Dealers excluded)-Difference','SecuritiesInvestmentTrustCompanies-Difference','Dealers-Difference','TotalDifference']
            r={k.strip():v for k,v in r.items()}
            if any(k not in r for k in keys): raise HTTPException(502,'法人欄位異常')
            values=[r[k] for k in keys];d=trading_date(r.get('Date'))
        else:
            today=datetime.now(timezone(timedelta(hours=8))).date()
            for offset in range(10):
                target=today-timedelta(days=offset)
                if target.weekday()>=5: continue
                b=self.fetch('https://www.twse.com.tw/fund/T86',{'date':target.strftime('%Y%m%d'),'response':'json','selectType':'ALLBUT0999'})
                if not isinstance(b,dict): raise HTTPException(502,'法人格式異常')
                if b.get('stat')!='OK':
                    if '很抱歉' in str(b.get('stat')) or '沒有' in str(b.get('stat')): continue
                    raise HTTPException(502,'法人來源狀態異常')
                fields=b.get('fields',[])
                keys=['外陸資買賣超股數(不含外資自營商)','投信買賣超股數','自營商買賣超股數','三大法人買賣超股數']
                try:
                    indices=[fields.index(k) for k in keys];code=fields.index('證券代號')
                    row=next((r for r in b.get('data',[]) if str(r[code]).strip()==symbol),None)
                    if not row: return self.envelope([],exchange)
                    values=[row[i] for i in indices];d=trading_date(b.get('date'))
                except (ValueError,IndexError): raise HTTPException(502,'法人欄位異常') from None
                break
            else: return self.envelope([],exchange)
        return self.envelope([{'date':d,**dict(zip(('foreign','investment_trust','dealer','total'),map(number,values))),'unit':'股'}],exchange)

    def news(self,symbol,name):
        if self.mode=='demo':
            return self.envelope([{'title':name+'新聞展示項目：虛構資料，不是真實報導','source':'展示資料','published_at':'2025-01-20T02:00:00+00:00','url':None}],'demo')
        root=self.fetch('https://news.google.com/rss/search',{'q':f'"{name}" 股票','hl':'zh-TW','gl':'TW','ceid':'TW:zh-Hant'},xml=True)
        result=[];seen=set()
        for item in root.findall('./channel/item'):
            link=(item.findtext('link') or '').strip();parsed=urlparse(link)
            if parsed.scheme!='https' or parsed.hostname!='news.google.com' or parsed.username or link in seen: continue
            try: published=parsedate_to_datetime(item.findtext('pubDate') or '').astimezone(timezone.utc).isoformat()
            except (ValueError,TypeError): continue
            seen.add(link)
            result.append({'title':(item.findtext('title') or '')[:500],'source':item.findtext('source') or 'Google News','published_at':published,'url':link})
        return self.envelope(sorted(result,key=lambda r:r['published_at'],reverse=True)[:10],'Google News RSS（請核對相關性與原文）')

provider=MarketProvider()
