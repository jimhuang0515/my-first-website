import {test,expect} from "@playwright/test";
test("上市上櫃搜尋、行情與圖表",async({page})=>{
  const errors:string[]=[];page.on("pageerror",e=>errors.push(e.message));
  await page.goto("/");await expect(page.getByRole("status")).toContainText("展示模式");
  await expect(page.getByTestId("quote-price")).toHaveText("1,000");
  await expect(page.getByRole("img",{name:/日 K 線與成交量/})).toBeVisible();
  await page.getByRole("textbox",{name:"股票搜尋"}).fill("環球晶");
  const stock=page.getByRole("button",{name:"環球晶 6488",exact:true});await expect(stock).toContainText("上櫃");await stock.click();
  await expect(page.getByTestId("quote-price")).toHaveText("500");
  await page.getByRole("textbox",{name:"股票搜尋"}).fill("不存在");await expect(page.getByText("沒有符合的股票")).toBeVisible();
  expect(errors).toEqual([]);
});
test("財報、法人與新聞",async({page})=>{
  await page.goto("/");await page.getByRole("button",{name:"財報",exact:true}).click();
  await expect(page.getByRole("cell",{name:"2024 Q3"})).toBeVisible();await expect(page.getByRole("cell",{name:"12.54"})).toBeVisible();
  await page.getByRole("button",{name:"法人籌碼",exact:true}).click();await expect(page.getByRole("cell",{name:"-300,000",exact:true})).toBeVisible();
  await page.getByRole("button",{name:"新聞",exact:true}).click();await expect(page.getByRole("heading",{name:/虛構資料，不是真實報導/})).toBeVisible();
});
test("註冊、保存自選股、重新登入與 AI 設定提示",async({page})=>{
  const email=`e2e-${Date.now()}-${Math.random().toString(16).slice(2)}@example.com`;const password="browser-test-password-123";
  await page.goto("/");await page.getByRole("button",{name:"登入 / 註冊",exact:true}).click();await page.getByRole("button",{name:"還沒有帳號？建立帳號",exact:true}).click();
  await page.getByLabel("Email",{exact:true}).fill(email);await page.getByLabel("密碼",{exact:true}).fill(password);await page.getByRole("button",{name:"建立帳號",exact:true}).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);await page.getByRole("button",{name:"☆ 加入自選",exact:true}).click();await expect(page.getByTestId("watchlist")).toContainText("台積電");
  await page.reload();await expect(page.getByTestId("watchlist")).toContainText("台積電");
  await page.getByRole("button",{name:"AI 分析",exact:true}).click();await page.getByRole("button",{name:"產生 AI 分析",exact:true}).click();await expect(page.getByRole("alert",{name:"操作提示"})).toContainText("STOCK_AI_API_KEY");
  await page.getByRole("button",{name:"登出",exact:true}).click();await expect(page.getByTestId("watchlist")).toHaveCount(0);
  await page.getByRole("button",{name:"登入 / 註冊",exact:true}).click();await page.getByLabel("Email",{exact:true}).fill(email);await page.getByLabel("密碼",{exact:true}).fill(password);await page.getByRole("button",{name:"登入",exact:true}).click();
  await expect(page.getByTestId("watchlist")).toContainText("台積電");await page.getByRole("button",{name:"★ 已加入自選",exact:true}).click();await expect(page.getByTestId("watchlist")).toHaveCount(0);
});
