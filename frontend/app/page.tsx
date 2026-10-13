"use client";
import {useEffect,useRef,useState} from "react";
import Chart,{type Candle} from "./Chart";

type Stock={symbol:string;name:string;exchange:string};
type User={id:number;email:string};
type Envelope<T>={data:T;mode:string;source:string;fetched_at:string};
type Quote={date:string;close:number|null;change:number|null;volume:number|null;currency:string;frequency:string};
type Financial={year:number;quarter:number;revenue:number|null;operating_income:number|null;net_income:number|null;eps:number|null;amount_unit:string};
type Flow={date:string;foreign:number|null;investment_trust:number|null;dealer:number|null;total:number|null;unit:string};
type News={title:string;source:string;published_at:string;url:string|null};
type Analysis={id:number;content:string;model:string;created_at:string;evidence:{quote:Envelope<Quote>}};
type Panels={quote?:Envelope<Quote>;candles?:Envelope<Candle[]>;financials?:Envelope<Financial[]>;flows?:Envelope<Flow[]>;news?:Envelope<News[]>;errors:Record<string,string>};
const fmt=(n:number|null|undefined,digits=0)=>n==null?"—":new Intl.NumberFormat("zh-TW",{maximumFractionDigits:digits}).format(n);
const market=(s:Stock)=>s.exchange==="TPEX"?"上櫃":"上市";
async function api<T>(path:string,options?:RequestInit):Promise<T>{
  const response=await fetch(`/api/v1${path}`,{...options,headers:{"Content-Type":"application/json",...options?.headers}});
  if(response.status===204)return undefined as T;
  let body;try{body=await response.json();}catch{throw new Error("服務暫時無法使用，請稍後重試");}
  if(!response.ok)throw new Error(typeof body.detail==="string"?body.detail:"輸入格式不正確，請檢查後重試");
  return body as T;
}
function Source({value}:{value?:{source:string;mode:string}}){return value?<p className="source">來源：{value.source}{value.mode==="demo"?" · 僅供功能展示":""}</p>:null;}

export default function Home(){
  const [query,setQuery]=useState("");
  const [stocks,setStocks]=useState<Stock[]>([]);
  const [searchError,setSearchError]=useState("");
  const [searching,setSearching]=useState(true);
  const [selected,setSelected]=useState<Stock>({symbol:"2330",name:"台積電",exchange:"TWSE"});
  const [panels,setPanels]=useState<Panels>({errors:{}});
  const [loading,setLoading]=useState(true);
  const [revision,setRevision]=useState(0);
  const [tab,setTab]=useState("overview");
  const [mode,setMode]=useState<string|null>(null);
  const [user,setUser]=useState<User|null>(null);
  const [watchlist,setWatchlist]=useState<Stock[]>([]);
  const [busy,setBusy]=useState(false);
  const [notice,setNotice]=useState("");
  const [authOpen,setAuthOpen]=useState(false);
  const [register,setRegister]=useState(false);
  const [aiBusy,setAiBusy]=useState(false);
  const [history,setHistory]=useState<Analysis[]>([]);
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{
    api<User>("/auth/me").then(setUser).catch(()=>setUser(null));
    api<{data_mode:string}>("/health").then(r=>setMode(r.data_mode)).catch(()=>setMode(null));
  },[]);
  useEffect(()=>{if(authOpen)dialog.current?.showModal();else dialog.current?.close();},[authOpen]);
  useEffect(()=>{
    const c=new AbortController();setSearching(true);
    const timer=setTimeout(()=>{api<Envelope<Stock[]>>(`/stocks?q=${encodeURIComponent(query)}`,{signal:c.signal})
      .then(r=>{setStocks(r.data);setSearchError("");setMode(r.mode);})
      .catch(e=>{if(!c.signal.aborted){setSearchError(e.message);setStocks([]);}})
      .finally(()=>{if(!c.signal.aborted)setSearching(false);});},250);
    return()=>{clearTimeout(timer);c.abort();};
  },[query]);
  useEffect(()=>{
    const c=new AbortController();setLoading(true);setPanels({errors:{}});setNotice("");
    Promise.all(Object.entries({quote:"quote",candles:"candles",financials:"financials",flows:"institutional-flows",news:"news"}).map(async([key,path])=>{
      try{const value=await api(`/stocks/${selected.symbol}/${path}`,{signal:c.signal});if(!c.signal.aborted)setPanels(p=>({...p,[key]:value}));}
      catch(e){if(!c.signal.aborted)setPanels(p=>({...p,errors:{...p.errors,[key]:(e as Error).message}}));}
    })).finally(()=>{if(!c.signal.aborted)setLoading(false);});return()=>c.abort();
  },[selected.symbol,revision]);
  useEffect(()=>{
    const c=new AbortController();setWatchlist([]);
    if(user)api<{data:Stock[]}>("/watchlist",{signal:c.signal}).then(r=>setWatchlist(r.data)).catch(e=>{if(!c.signal.aborted)setNotice(e.message);});
    return()=>c.abort();
  },[user]);
  useEffect(()=>{
    const c=new AbortController();setHistory([]);
    if(user)api<{data:Analysis[]}>(`/stocks/${selected.symbol}/analyses`,{signal:c.signal}).then(r=>setHistory(r.data)).catch(e=>{if(!c.signal.aborted)setNotice(e.message);});
    return()=>c.abort();
  },[user,selected.symbol]);
  function openAuth(){setRegister(false);setNotice("");setAuthOpen(true);}
  async function authenticate(e:React.FormEvent<HTMLFormElement>){
    e.preventDefault();setBusy(true);setNotice("");const form=new FormData(e.currentTarget);
    try{setUser(await api<User>(`/auth/${register?"register":"login"}`,{method:"POST",body:JSON.stringify({email:form.get("email"),password:form.get("password")})}));setAuthOpen(false);}
    catch(e){setNotice((e as Error).message);}finally{setBusy(false);}
  }
  async function logout(){setBusy(true);try{await api("/auth/logout",{method:"POST"});setUser(null);setNotice("");}catch(e){setNotice((e as Error).message);}finally{setBusy(false);}}
  async function toggleWatch(){
    if(!user){openAuth();return;}setBusy(true);setNotice("");
    try{await api(`/watchlist/${selected.symbol}`,{method:watchlist.some(s=>s.symbol===selected.symbol)?"DELETE":"PUT"});setWatchlist((await api<{data:Stock[]}>("/watchlist")).data);}
    catch(e){setNotice((e as Error).message);}finally{setBusy(false);}
  }
  async function analyze(){
    if(!user){openAuth();return;}setAiBusy(true);setNotice("");
    try{const r=await api<Analysis>(`/stocks/${selected.symbol}/analyses`,{method:"POST"});setHistory(p=>[r,...p]);}
    catch(e){setNotice((e as Error).message);}finally{setAiBusy(false);}
  }
  const quote=panels.quote?.data;
  const saved=watchlist.some(s=>s.symbol===selected.symbol);
  const tabs=[["overview","市場概覽"],["financials","財報"],["flows","法人籌碼"],["news","新聞"],["ai","AI 分析"]];
  return <>
    <header className="topbar"><a className="brand" href="/"><span className="brand-icon">↗</span><span>台股研究室<small>TAIWAN STOCK LAB</small></span></a><span className="header-note">看懂數據，再做判斷。</span><div className="account">{user?<><span>{user.email}</span><button className="ghost" disabled={busy||aiBusy} onClick={logout}>登出</button></>:<button className="primary" onClick={openAuth}>登入 / 註冊</button>}</div></header>
    <div className="workspace"><aside className="sidebar"><p className="eyebrow">EXPLORE THE MARKET</p><h2>尋找你的下一個觀察標的</h2><label className="searchbox"><span>⌕</span><input aria-label="股票搜尋" maxLength={50} value={query} onChange={e=>setQuery(e.target.value)} placeholder="輸入代號或公司名稱"/></label><div className="list-title">股票搜尋 <span>上市・上櫃</span></div><div className="stock-list" aria-live="polite">{searching&&<p className="muted">搜尋中…</p>}{searchError&&<p role="alert" className="error">{searchError}</p>}{!searching&&!searchError&&!stocks.length&&<p className="muted">沒有符合的股票</p>}{stocks.map(s=><button key={s.symbol} aria-label={`${s.name} ${s.symbol}`} className={`stock-row ${selected.symbol===s.symbol?"active":""}`} disabled={busy||aiBusy} onClick={()=>setSelected(s)}><span><strong>{s.name}</strong><small>{s.symbol} · {market(s)}</small></span><span>↗</span></button>)}</div><div className="list-title watch-heading">我的自選股 <span>{watchlist.length}</span></div>{!user?<p className="muted">登入後儲存你的關注清單。</p>:!watchlist.length?<p className="muted">在股票頁面點選「加入自選」。</p>:<div data-testid="watchlist">{watchlist.map(s=><button key={s.symbol} className="stock-row" disabled={busy||aiBusy} onClick={()=>setSelected(s)}><span><strong>{s.name}</strong><small>{s.symbol} · {market(s)}</small></span>☆</button>)}</div>}<p className="sidebar-footer">● 免費日終資料<br/>資料時間依各來源為準</p></aside>
    <main><div className={`mode-banner ${mode==="demo"?"demo":""}`} role="status">{mode==="demo"?"展示模式 · 行情、財報、籌碼與新聞皆為虛構測試資料，不可用於投資決策。":mode==="live"?"上市／上櫃 · 免費日終行情，非盤中即時報價。請核對各項資料日期。":"正在確認資料來源；尚未確認行情模式。"}</div><div className="page-heading"><div><p className="eyebrow">YOUR MARKET, IN FOCUS</p><h1>每一個決策，從理解開始。</h1><p className="muted">整合市場數據與 AI，建立自己的投資觀點。</p></div><button className="ghost" disabled={loading||aiBusy} onClick={()=>setRevision(r=>r+1)}>↻ 更新資料</button></div>{notice&&!authOpen&&<div role="alert" aria-label="操作提示" className="notice">{notice}</div>}
    <section className="stock-summary"><div><span className="pill">{market(selected)} · {selected.exchange}</span><h2>{selected.name} <span>{selected.symbol}</span></h2><p className="muted">新台幣 TWD · 日終價格</p></div><div className="quote-block"><strong data-testid="quote-price">{fmt(quote?.close,2)}</strong><span className={quote?.change!=null&&quote.change>=0?"up":"down"}>{quote?.change!=null&&quote.change>=0?"+":""}{fmt(quote?.change,2)}<small>資料日 {quote?.date??"—"}</small></span></div><button className={`watch-button ${saved?"saved":""}`} disabled={busy||aiBusy} onClick={toggleWatch}>{saved?"★ 已加入自選":"☆ 加入自選"}</button></section>{panels.errors.quote&&<p role="alert" className="error">價格：{panels.errors.quote}</p>}<Source value={panels.quote}/>
    <nav className="tabs" aria-label="股票資料分類">{tabs.map(([key,label])=><button key={key} aria-label={label} aria-current={tab===key?"page":undefined} className={tab===key?"selected":""} onClick={()=>setTab(key)}>{label}</button>)}</nav>
    {tab==="overview"&&<><div className="metrics"><article><p>收盤價</p><strong>{fmt(quote?.close,2)}<small>TWD</small></strong></article><article><p>當日漲跌</p><strong className={quote?.change!=null&&quote.change>=0?"up":"down"}>{fmt(quote?.change,2)}<small>TWD</small></strong></article><article><p>成交股數</p><strong>{fmt(quote?.volume)}<small>股</small></strong></article></div><section className="card"><div className="card-heading"><div><h3>價格走勢</h3><p className="muted">日 K 線・近三個月</p></div><span className="pill">日線</span></div>{panels.errors.candles?<p role="alert" className="error">{panels.errors.candles}</p>:panels.candles?.data.length?<Chart rows={panels.candles.data}/>:<p className="empty">{loading?"載入 K 線中…":"沒有可用的 K 線資料"}</p>}<div className="chart-footer"><span>紅：上漲 · 綠：下跌</span><span>{panels.candles?.data[0]?.date} — {panels.candles?.data.at(-1)?.date}</span></div><Source value={panels.candles}/></section><div className="bottom-grid"><section className="card"><p className="eyebrow">RESEARCH ASSISTANT</p><h3>讓 AI 協助整理你的觀察</h3><p className="muted">引用價格、財報與籌碼，辨識風險與資料限制。</p><button className="text-button" onClick={()=>setTab("ai")}>前往 AI 分析 ↗</button></section><section className="card"><p className="eyebrow">DATA FIRST</p><h3>不同數據，不同更新時間</h3><p className="muted">財報按季度、籌碼按交易日更新。免費來源可能延遲或缺值，請以原始資料為準。</p></section></div></>}
    {tab==="financials"&&<section className="card"><h3>財務表現</h3>{panels.errors.financials&&<p role="alert" className="error">{panels.errors.financials}</p>}{panels.financials?.data.length?<div className="table-wrap"><table><thead><tr><th>報告期間</th><th>營收（千元）</th><th>營業利益（千元）</th><th>本期淨利（千元）</th><th>EPS（元／股）</th></tr></thead><tbody>{panels.financials.data.map(r=><tr key={`${r.year}-${r.quarter}`}><td>{r.year} Q{r.quarter}</td><td>{fmt(r.revenue)}</td><td>{fmt(r.operating_income)}</td><td>{fmt(r.net_income)}</td><td>{fmt(r.eps,2)}</td></tr>)}</tbody></table></div>:!panels.errors.financials&&<p className="empty">{loading?"載入中…":"沒有可用的一般業財報資料"}</p>}<p className="muted">金額為新台幣千元；損益可能是年度累計值，不能直接當作單季。銀行等特殊產業需專用資料集。</p><Source value={panels.financials}/></section>}
    {tab==="flows"&&<section className="card"><h3>三大法人買賣超</h3>{panels.errors.flows&&<p role="alert" className="error">{panels.errors.flows}</p>}{panels.flows?.data.length?<div className="table-wrap"><table><thead><tr><th>交易日</th><th>外資（不含自營商）</th><th>投信</th><th>自營商</th><th>官方合計</th></tr></thead><tbody>{panels.flows.data.map(r=><tr key={r.date}><td>{r.date}</td>{[r.foreign,r.investment_trust,r.dealer,r.total].map((v,i)=><td key={i} className={v!=null&&v>=0?"up":"down"}>{fmt(v)}</td>)}</tr>)}</tbody></table></div>:!panels.errors.flows&&<p className="empty">{loading?"載入中…":"沒有可用的法人資料"}</p>}<p className="muted">單位：股。正值為買超，負值為賣超。外資自營商分類依來源定義。</p><Source value={panels.flows}/></section>}
    {tab==="news"&&<section className="card"><h3>相關新聞</h3>{panels.errors.news&&<p role="alert" className="error">{panels.errors.news}</p>}{panels.news?.data.map((r,i)=><article className="news-item" key={i}><p>{r.source} · {new Date(r.published_at).toLocaleDateString("zh-TW",{timeZone:"Asia/Taipei"})}</p>{r.url?<a href={r.url} target="_blank" rel="noopener noreferrer">{r.title} ↗</a>:<h4>{r.title}</h4>}</article>)}{panels.news?.data.length===0&&<p className="empty">沒有相關新聞</p>}<Source value={panels.news}/></section>}
    {tab==="ai"&&<section className="card"><p className="eyebrow">AI RESEARCH ASSISTANT</p><h3>數據背後，有哪些值得注意的事？</h3><p className="muted">整理事實、可能解讀與風險，保存在你的私人紀錄。</p><button className="primary ai-button" disabled={aiBusy||loading} onClick={analyze}>{aiBusy?"正在分析…":user?"產生 AI 分析":"登入後開始分析"}</button><p className="source">AI 可能出錯，請核對原始資料。展示模式分析不可用於投資決策。</p>{history.map(r=><article className="analysis-result" key={r.id}><p className="source">{r.model} · {new Date(r.created_at).toLocaleString("zh-TW",{timeZone:"Asia/Taipei"})} · 資料日 {r.evidence.quote.data.date} · {r.evidence.quote.mode==="demo"?"虛構展示資料":"真實日終資料"}</p><div>{r.content}</div></article>)}{user&&!history.length&&<p className="muted">尚無分析紀錄。</p>}</section>}
    <footer>台股研究室 <span>資料與 AI 僅供研究參考；請自行評估風險。</span></footer></main></div>
    <dialog ref={dialog} className="auth-modal" aria-label={register?"註冊帳號":"登入帳號"} onCancel={e=>{if(busy)e.preventDefault();else setAuthOpen(false);}}><button className="close-button" aria-label="關閉登入視窗" disabled={busy} onClick={()=>setAuthOpen(false)}>×</button><p className="eyebrow">YOUR PERSONAL RESEARCH SPACE</p><h2>{register?"建立你的研究帳號":"歡迎回到研究室"}</h2><p className="muted">儲存自選股，累積自己的分析觀點。</p><form onSubmit={authenticate}><label>Email<input name="email" type="email" maxLength={254} autoComplete="email" autoFocus required/></label><label>密碼<input name="password" type="password" minLength={12} maxLength={128} autoComplete={register?"new-password":"current-password"} required/></label><p className="source">密碼至少 12 個字元。</p>{notice&&<p role="alert" className="error">{notice}</p>}<button className="primary" disabled={busy} type="submit">{busy?"處理中…":register?"建立帳號":"登入"}</button></form><button className="text-button" disabled={busy} onClick={()=>{setRegister(v=>!v);setNotice("");}}>{register?"已有帳號？前往登入":"還沒有帳號？建立帳號"}</button></dialog>
  </>;
}
