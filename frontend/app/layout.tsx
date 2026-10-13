import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata={title:"台股研究室 | 上市・上櫃 AI 分析",description:"台股資料、K 線與 AI 輔助分析"};
export default function Layout({children}:{children:React.ReactNode}){
  return <html lang="zh-Hant"><body>{children}</body></html>;
}
