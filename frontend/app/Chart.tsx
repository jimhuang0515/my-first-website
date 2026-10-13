"use client";
import {useEffect,useRef} from "react";
import {createChart,ColorType,CandlestickSeries,HistogramSeries,type Time} from "lightweight-charts";
export type Candle={date:string;open:number;high:number;low:number;close:number;volume:number|null};
export default function Chart({rows}:{rows:Candle[]}){
  const ref=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    if(!ref.current||!rows.length)return;
    const chart=createChart(ref.current,{autoSize:true,layout:{background:{type:ColorType.Solid,color:"#fff"},textColor:"#708078"},grid:{vertLines:{color:"#f4f6f4"},horzLines:{color:"#f0f3f1"}},timeScale:{borderVisible:false},rightPriceScale:{borderVisible:false}});
    const bars=chart.addSeries(CandlestickSeries,{upColor:"#d76155",downColor:"#22846c",borderVisible:false,wickUpColor:"#d76155",wickDownColor:"#22846c"});
    bars.setData(rows.map(r=>({time:r.date as Time,open:r.open,high:r.high,low:r.low,close:r.close})));
    const volume=chart.addSeries(HistogramSeries,{priceFormat:{type:"volume"},priceScaleId:""},1);
    volume.setData(rows.filter(r=>r.volume!==null).map(r=>({time:r.date as Time,value:r.volume!,color:r.close>=r.open?"#d761553d":"#22846c3d"})));
    chart.panes()[1]?.setHeight(70);chart.timeScale().fitContent();return()=>chart.remove();
  },[rows]);
  return <div ref={ref} className="chart" role="img" aria-label={`日 K 線與成交量，共 ${rows.length} 筆`}/>;
}
