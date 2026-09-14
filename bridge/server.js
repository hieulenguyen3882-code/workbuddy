// MVP 0 本地桥：接收扩展抓取的结构化事实，落盘，供增长判断中枢读取。
// 纯 Node 内置模块，无第三方依赖。
const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = process.env.PORT || 8910;
const CAP_DIR = path.join(__dirname, 'captures');
fs.mkdirSync(CAP_DIR, { recursive: true });

const server = http.createServer((req, res) => {
  // 上报入口：仅接受 ok===true 的结构化事实
  if (req.method === 'POST' && req.url === '/ingest') {
    let body = '';
    req.on('data', (c) => (body += c));
    req.on('end', () => {
      let data;
      try {
        data = JSON.parse(body);
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: 'invalid json' }));
        return;
      }
      // 读取纪律：未读取内容（ok!==true）拒绝入库，绝不补点
      if (!data || data.ok !== true || !data.url) {
        res.writeHead(422, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: false, error: 'non-content payload rejected (未读取内容不入库)' }));
        return;
      }
      const ts = new Date().toISOString().replace(/[:.]/g, '-');
      const file = path.join(CAP_DIR, ts + '.json');
      fs.writeFileSync(file, JSON.stringify(data, null, 2));
      fs.writeFileSync(path.join(CAP_DIR, 'latest.json'), JSON.stringify(data, null, 2));
      console.log('[ingest] received type=%s url=%s', data.type, data.url);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: true, saved: file }));
    });
    return;
  }

  // 中枢读取：最近一次成功抓取
  if (req.method === 'GET' && req.url === '/latest') {
    const f = path.join(CAP_DIR, 'latest.json');
    if (fs.existsSync(f)) {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(fs.readFileSync(f));
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ ok: false }));
    }
    return;
  }

  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('douyin-bridge ok');
});

server.listen(PORT, () => {
  console.log('douyin bridge listening on http://localhost:' + PORT);
});
