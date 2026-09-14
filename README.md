# 抖音内容读取桥（MVP 0）

铭哥增长判断中枢的「抖音内容获取能力」最小实现。目标：在本地已登录 Chrome 抖音网页，点一下扩展图标，系统自动读取当前页已加载、可见的内容，把结构化事实送入增长判断中枢。

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

## 读取纪律（最高优先级，写在代码里、不可绕过）

1. 只在主动点击扩展图标「抓取当前页」时读取当前活动 tab；**不轮询、不批量爬取**。
2. 只在已登录会话内读取 DOM，**不绕过登录 / 验证码 / 风控**。
3. 解析失败，或标题 / 正文 / 作者 / 数据 / 评论**全部缺失** → 返回 `{ok:false, reason:"未读取内容", url}`。
4. 本地桥**拒绝入库**任何 `ok !== true` 的负载（返回 422）。
5. 中枢对 `ok !== true` 的负载，只输出「未读取内容」提示，**绝不分析、绝不用标题或空字段推断**。

## 安装（本地，一次性）

前置：本地已装 Node.js（桥用 Node 内置模块，无需 `npm install` 任何依赖）。

1. 启动本地桥：双击 `start.cmd`（Windows）或 `bash start.sh`（macOS/Linux）。
2. 加载扩展：Chrome 打开 `chrome://extensions` → 开启「开发者模式」→「加载已解压的扩展程序」→ 选择仓库里的 `extension/` 目录。

## 使用

1. 本地 Chrome 登录抖音，打开任意视频详情页（`douyin.com/video/<id>`）。
2. 点扩展图标 → 「抓取当前抖音页」。
3. 数据进入本地桥 `bridge/captures/`，可通过 `GET http://localhost:8910/latest` 读取最近一次抓取。

## 读取字段

- `caption`：视频标题/文案（H1）
- `description`：正文（标题之外的文案部分；无独立正文时为 null）
- `author`：作者昵称
- `stats`：点赞数 / 评论数 / 收藏数 / 分享数 / 发布时间
- `comments`：当前已加载的评论（前 12 条原文）

## 中枢对接

桥把结构化事实写入 `bridge/captures/<时间戳>.json`，并暴露：
- `GET /latest`：最近一次成功抓取
- `POST /ingest`：扩展上报入口（仅接受 `ok===true` 的负载）

## 目录

```
extension/   Chrome 扩展（MV3）
bridge/      本地桥（Node，纯内置模块）；运行时生成 bridge/captures/
start.cmd     Windows 一键启动桥
start.sh      macOS / Linux 启动桥
```
