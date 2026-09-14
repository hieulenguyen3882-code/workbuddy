# 抖音内容读取桥（MVP 0）

铭哥增长判断中枢的「抖音内容获取能力」最小实现。目标：铭哥在本地已登录 Chrome 抖音网页，点一下扩展图标，系统自动读取当前页已加载、可见的内容，把结构化事实送入增长判断中枢，随后才生成快速判断卡。

## 架构

```
Chrome 扩展 (extension/, MV3)
   │  仅主动点击「抓取当前页」时，读取当前抖音活动页可见 DOM
   ▼
本地桥 (bridge/, Node, localhost:8910)
   │  接收结构化事实，落盘到 bridge/captures/，暴露 GET /latest
   ▼
增长判断中枢 (WorkBuddy)
   │  读取 captures/ 或轮询 GET /latest，拿到结构化事实后出卡
   ▼
快速判断卡
```

- **Chrome 扩展**：只在铭哥点击图标时读取当前活动 tab 的可见内容，POST 给本地桥。
- **本地桥**：监听 `localhost:8910`，接收结构化 JSON，落盘 `bridge/captures/<时间戳>.json`，供中枢读取。
- **中枢**：读取 `bridge/captures/` 或轮询 `GET /latest`，拿到结构化事实后出卡。

## 读取纪律（最高优先级，写在代码里、不可绕过）

1. 只在铭哥主动点击扩展图标「抓取当前页」时读取当前活动 tab；**不轮询、不批量爬取**。
2. 只在已登录会话内读取 DOM，**不绕过登录 / 验证码 / 风控**。
3. 解析失败，或标题 / 正文 / 作者 / 数据 / 评论**全部缺失** → 返回 `{ok:false, reason:"未读取内容", url}`。
4. 本地桥**拒绝入库**任何 `ok !== true` 的负载（返回 422）。
5. 中枢对 `ok !== true` 的负载，只输出「未读取内容」提示，**绝不分析、绝不用标题或空字段推断**。

## 安装（铭哥本地，一次性）

前置：本地已装 Node.js（桥用 Node 内置模块，无需 `npm install` 任何依赖）。

1. 拉取仓库：
   ```
   git clone https://github.com/hieulenguyen3882-code/workbuddy.git
   cd workbuddy
   ```
2. 启动本地桥：
   - Windows：双击 `start.cmd`
   - macOS / Linux：`bash start.sh`
   - 通用：`node bridge/server.js`
3. 加载扩展：Chrome 打开 `chrome://extensions` → 开启「开发者模式」→「加载已解压的扩展程序」→ 选择仓库里的 `extension/` 目录。

> 关于「扩展包」：MVP 0 阶段用 Chrome 开发者模式**加载已解压的 extension/ 目录**即可，无需打包 `.crx`（`.crx` 需 Chrome 开发者账号）。换电脑同样三步。

## 使用

1. 本地 Chrome 登录抖音，打开任意视频页或账号页。
2. 点扩展图标 → 「抓取当前页」。
3. 数据进入本地桥 `bridge/captures/`，中枢读取后出快速判断卡。

## 中枢对接

桥把结构化事实写入 `bridge/captures/<时间戳>.json`，并暴露：
- `GET /latest`：最近一次成功抓取
- `POST /ingest`：扩展上报入口（仅接受 `ok===true` 的负载）

增长判断中枢读取 `bridge/captures/` 或轮询 `/latest`，拿到结构化事实后出快速判断卡。

## 版本源与协作

- GitHub 仓库 `hieulenguyen3882-code/workbuddy` 的 `main` 是唯一正式版本源。
- WorkBuddy 负责代码生产、修改与本地测试。
- ChatGPT 负责当前阶段的 GitHub 入库与回读验收。
- 新环境恢复时直接从 `main` 拉取，不以聊天记录或临时 ZIP 作为正式版本。

## 目录

```
extension/   Chrome 扩展（MV3）
bridge/      本地桥（Node，纯内置模块）；运行时生成 bridge/captures/
start.cmd     Windows 一键启动桥
start.sh      macOS / Linux 启动桥
```
