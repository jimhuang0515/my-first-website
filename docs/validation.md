# 部署驗證 — 2026-10-13（Asia/Taipei）

這次環境與遠端 main 均只有初始 README，前次未提交的 MVP 無法恢復；本版依原需求重建，不沿用前次 48 項測試的結果。

## 本版實際通過

- PostgreSQL 17 健康檢查與真實 DB 連線。
- 28 項 pytest：上市／上櫃搜尋、行情／OHLC／日期／單位、來源失敗、密碼雜湊、cookie、到期／登出、Origin、限流、自選股保存與隔離、AI mock 成功／錯誤／私人歷史。
- Next.js production build 與 TypeScript（包含部署容器中的正式建置）。
- Render Blueprint 通過當日官方 JSON schema 驗證：<https://render.com/schema/render.yaml.json>。
- Docker image 建置成功；以非 root 使用者運行，單一公開前端端口代理真正的 FastAPI 與 PostgreSQL。
- 部署容器上 6 項 Playwright 測試通過：桌面 3 項、手機 3 項。包括搜尋、實際 canvas K 線、財報／法人／新聞、註冊、自選股、重新登入、AI 缺金鑰提示。
- 真實 TWSE／TPEx 基本資料取得 1,988 筆；台積電與環球晶各項價格、K 線、財報、法人及新聞查詢通過。

## 失敗與修正

Docker build 最初無法解析環境代理，改用正式 DNS mapping。TLS 攔截代理的 CA 未隨 Docker 基底提供，透過 BuildKit 的可選 `build_ca` mount 使用執行環境提供的公開 CA bundle。APT 的 `_apt` 使用者需要讀取該公開憑證，所以 mount 設為 0444。憑證沒有提交到 Git，也沒有留在最終 image。保留 HTTPS、憑證驗證、APT 簽章及 npm lock integrity；沒有停用驗證。

TPEx 曾回傳截斷 JSON；有限次重試時加入 `Cache-Control: no-cache` 重新驗證來源，受影響的完整上市／上櫃查詢之後通過。公開主機上的供應商可用性仍需在真正部署後再驗證。

## 尚未執行

- Render 帳號尚未連接，尚未建立 Web Service 或公開網址，沒有宣稱已部署。
- 真實 OpenAI 呼叫未執行：缺少 `STOCK_AI_API_KEY`；成功及錯誤 contract 已用 mock 驗證，缺 key 不生成虛構結果。
- 免費主機休眠／喚醒、Render HTTPS cookie、自訂網域與平台 DB 連線，需要建立真正服務後再驗證。

## 使用者的必要操作

用 GitHub 登入 Render，再開啟 README 的部署入口，確認兩個資源都採 Free 方案，建立 Blueprint。服務顯示 Live 後，使用 Render 產生的 HTTPS 網址。

免費網站閒置 15 分鐘後休眠，重新開啟約需一分鐘；免費 PostgreSQL 30 天後到期。資料庫到期前必須決定長期儲存方案，避免資料遺失。依據官方限制：<https://render.com/docs/free>。
