# 台股研究室 — 上市・上櫃股票分析

Next.js + FastAPI + PostgreSQL。支援股票搜尋、免費日終價格、日 K 線、一般業財報、法人籌碼、新聞、登入、自選股與 OpenAI 分析。資料失敗不切換虛構行情；展示模式另外明確標示。

## 建立可從瀏覽器開啟的網站

[部署到 Render](https://render.com/deploy?repo=https%3A%2F%2Fgithub.com%2Fjimhuang0515%2Fmy-first-website%2Ftree%2Fwebsite-deployment)

1. 用 GitHub 帳號登入 Render，必要時授權它讀取這個儲存庫。
2. 開啟上方部署入口，確認分支為 `website-deployment`、兩個資源的方案都是 `Free`，再建立 Blueprint。不要勾選或升級付費方案。
3. 等待 `taiwan-stock-db` 與 `taiwan-stock-lab` 建立完成。Web Service 顯示 `Live` 後，點 Render 服務頁提供的 HTTPS 網址。
4. 驗證能搜尋台積電與環球晶、顯示 K 線、註冊及新增自選股。公開網站實際網址由 Render 建立後提供，不能預先假定。

這個按鈕是部署入口，尚未建立網站服務。Render 帳號與 Blueprint 建立需要使用者本人操作，目前未連接可代為部署的主機帳號。

部署設定明確使用免費 Web Service 與免費 PostgreSQL。依 Render 官方文件，免費網站閒置 15 分鐘後休眠，重新開啟約需一分鐘；免費 PostgreSQL 建立 30 天後到期。適合先驗證 MVP，長期使用需另外選擇資料庫與費用方案。資料庫只允許 Render 內網連線。方案若不再提供或顯示需付費，請停止並確認替代方案。

OpenAI 金鑰不是首次部署的必要條件。其他功能先可使用；AI 按鈕會提示尚未設定。要啟用時在 Render 的 Environment 安全新增 `STOCK_AI_API_KEY`（不要貼到聊天或提交到 Git），重新部署後驗證。模型預設 `gpt-4.1-mini`，每位使用者 5 分鐘最多 3 次，每次最多輸出 1,500 tokens。需自行設定 OpenAI 用量預算。

## 部署架構

Render 一個 Docker Web Service 同時啟動 Next.js 與 FastAPI，對外只開 Next.js 的 `PORT`。FastAPI 只綁 loopback 8000，Next.js 同源代理 `/api`；因此登入 cookie 不跨網域。PostgreSQL 使用獨立受管服務，資料不放在會隨休眠消失的容器檔案系統。

Render 自動提供 `RENDER_EXTERNAL_URL`，後端以此驗證 Origin；HTTPS cookie 設定 Secure + HttpOnly + SameSite=Lax。其他主機需自行設定 `APP_ORIGIN=https://你的網站網域` 及 `COOKIE_SECURE=true`。

市場資料來自 TWSE／TPEx，價格是最新可用日終值，不是盤中即時。每項資料分別顯示日期，財報可能是年度累計；特殊產業專用財報尚未納入。新聞來自 Google News RSS，請核對相關性與原文。AI 可出錯，不能把生成內容當作行情事實。

## 雲端開發與測試

使用現有 checkout，任務已隔離，不另外建立 Git worktree。

```bash
cd /workspace/my-first-website
bash scripts/install.sh
bash scripts/dev.sh
```

`STOCK_DATA_MODE=live` 預設讀真實來源；使用 `STOCK_DATA_MODE=demo bash scripts/dev.sh` 才載入固定虛構資料。

```bash
bash scripts/test.sh
docker build -t taiwan-stock-lab:deployment .
bash scripts/e2e.sh
```

後端測試使用獨立 `stocktest`，會清除測試 schema；不清除 `stockdev`。不要把 `TEST_DATABASE_URL` 指向真實使用者資料庫。E2E 用真正的部署容器、PostgreSQL、展示資料及系統 Chromium，不傳入 OpenAI 金鑰，避免付費測試。

部署容器建置需要 Node.js 24、Python 3.12 與 Debian 官方套件來源，保持 TLS、簽章與鎖檔 integrity 驗證。代理環境可用 Docker 的標準 proxy build args 及正式 DNS 設定，不關閉驗證。

本版在前次環境未保存的原始碼消失後，依已確認需求重建。測試需以本版實際結果為準，不沿用先前的測試數字。程式會提交至部署分支，避免只依賴臨時環境中的未追蹤檔案。
