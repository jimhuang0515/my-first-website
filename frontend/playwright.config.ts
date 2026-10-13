import {defineConfig,devices} from "@playwright/test";
export default defineConfig({
  testDir:"./tests",timeout:30000,workers:1,
  use:{baseURL:process.env.TEST_APP_URL||"http://127.0.0.1:13000",trace:"retain-on-failure",launchOptions:{executablePath:process.env.CHROMIUM_PATH||"/usr/bin/chromium",args:["--no-sandbox"]}},
  projects:[{name:"desktop",use:{...devices["Desktop Chrome"]}},{name:"mobile",use:{...devices["Pixel 7"]}}],
});
