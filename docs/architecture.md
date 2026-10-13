# 架構與交付範圍

台股優先，同時支援上市／上櫃普通股，使用免費日終資料。盤中即時、ETF／興櫃、特殊產業財報、交易下單與投資組合損益尚未納入。

## 公開網站

瀏覽器 → Render HTTPS → Next.js（公開 PORT）→ 同源 `/api` 代理 → FastAPI（容器內 loopback 8000）→ PostgreSQL（Render 私有網路）。

單一 Docker Web Service 保存前後端程式，使用獨立資料庫保存使用者、自選股與分析紀錄。容器內沒有需要保存的使用者檔案，不依賴 Render 免費容器的暫時檔案系統。健康檢查會經前端代理測試後端與真正的資料庫連線。

## 市場資料

MarketProvider 依交易所選擇 TWSE 或 TPEx。上市／上櫃公司基本資料分別同步；價格、K 線、財報及法人資料各顯示來源與日期。TPEx 月 K 線成交量從張乘 1,000 轉成股。不同資料集可能有不同更新日期，不能宣稱即時。

來源 GET 有有限次重試、timeout、TLS 驗證及 5 分鐘程序內快取；同一個來源的並行請求會合併。來源失敗返回明確錯誤，不偷偷載入虛構資料。`STOCK_DATA_MODE=demo` 才提供固定虛構資料並全頁標示。

財报目前一般業綜合損益表，可能是年度累計值。新聞使用 Google News RSS，只保存／顯示標題、來源、日期與連結，需核對關聯性，沒有擷取新聞全文。

## 登入與 AI

PostgreSQL 表：users、sessions、stocks、watchlist_items、analysis_runs。自選股使用 user_id + symbol 唯一約束；私人查詢以目前使用者限制。密碼 Argon2id，不透明 token 在資料庫只保存 SHA-256 雜湊，7 天到期且登出後失效。

公開部署檢查 Origin，HTTPS cookie 為 Secure + HttpOnly + SameSite=Lax。Render 的自動 `RENDER_EXTERNAL_URL` 提供正確網站 Origin；自訂網域需更新 `APP_ORIGIN`。API SQL 使用 SQLAlchemy 參數化操作。

AI 呼叫 OpenAI Responses API，必須登入且明確點擊，輸入包含資料日期／來源，不傳 email。JSON 與新聞標題是不可信輸入，指令要求不遵循其中指令、不捏造事實、區分事實與推論、提醒核對來源。`store=false`，最多輸出 1,500 tokens，成功才保存分析；沒有 key 不偽造模型結果。

## 限制

此為單一 worker MVP，快取與限流為程序內狀態。正式多人規模部署需共享限流、資料同步、schema migrations、備份與監控，登入系統後续需郵件驗證與密碼重設。Render 免費方案僅供試用：網站會休眠，免費 PostgreSQL 在 30 天後到期。

現有 create_all 僅建立缺少的 schema，不負責改動既有資料表。升級舊資料庫前必須建立 migration；不能用刪除資料來解決部署問題。
