// MVP 0 背景服务（MV3 service worker）
// 职责：铭哥点击扩展图标 → 抓取当前抖音活动页可见 DOM → POST 给本地桥。
// 读取纪律：只在主动点击时读取当前 tab；解析失败返回 {ok:false}；绝不伪造内容。

const BRIDGE_URL = 'http://localhost:8910/ingest';

// 注入到页面执行的提取函数（在抖音已登录会话的 DOM 上只读，不碰登录/风控）
function extractOnPage() {
  function text(sels) {
    for (const s of sels) {
      const el = document.querySelector(s);
      if (!el) continue;
      const visible = el.innerText && el.innerText.trim();
      if (visible) return visible;
      // meta 等无可见文本节点，用 content 作为只读兜底证据。
      const metaContent = el.getAttribute && el.getAttribute('content');
      if (metaContent && metaContent.trim()) return metaContent.trim();
    }
    return null;
  }

  function allText(sels, limit) {
    for (const s of sels) {
      const els = document.querySelectorAll(s);
      const out = [];
      els.forEach((el, i) => {
        if (i >= limit) return;
        const t = el.innerText ? el.innerText.trim() : '';
        if (t) out.push(t);
      });
      if (out.length) return out;
    }
    return [];
  }

  const result = {
    ok: true,
    capturedAt: new Date().toISOString(),
    url: location.href,
    type: 'unknown',
    fields: {}
  };

  // 页面类型判断（只用于打标，不用于决定是否读取）
  const isVideo = /video\/|note\/|v\.douyin\.com/.test(location.href) ||
    !!document.querySelector('xg-player, [data-e2e="feed-title"], [data-e2e="detail-title"], .video-title');
  const isProfile = !!document.querySelector('[data-e2e="user-info"], [data-e2e="user-card"], .author-info, .user-info');
  result.type = isVideo ? 'video' : (isProfile ? 'profile' : 'unknown');

  // 标题 / 文案正文 / 作者
  const caption = text([
    '[data-e2e="detail-title"]', '.video-title', '[data-e2e="feed-title"]',
    'meta[property="og:title"]'
  ]);
  const description = text([
    '[data-e2e="detail-desc"]', '.video-desc', '[data-e2e="feed-desc"]'
  ]);
  const author = text([
    '[data-e2e="user-info"] [data-e2e="user-name"]',
    '[data-e2e="user-info"] .author-name',
    '.author-info .name',
    'meta[property="og:author"]'
  ]);

  // 互动数据（点赞/评论/收藏/分享/数量）
  const stats = {};
  document.querySelectorAll('[data-e2e*="like"],[data-e2e*="comment"],[data-e2e*="collect"],[data-e2e*="share"],[data-e2e*="count"]')
    .forEach(el => {
      const label = el.getAttribute('data-e2e') || '';
      const key = label.replace(/[-_]/g, '');
      const val = el.innerText ? el.innerText.trim() : '';
      if (val) stats[key] = val;
    });

  // 评论区（取前 12 条）
  const comments = allText([
    '[data-e2e="comment-item"]', '.comment-item', '.comment-list .comment'
  ], 12);

  result.fields = { caption, description, author, stats, comments };

  // 读取纪律：关键字段全缺失即明确失败，绝不断点伪造
  const hasAny = caption || description || author || Object.keys(stats).length || comments.length;
  if (!hasAny) {
    return { ok: false, reason: '未读取内容：当前页无可解析的标题/正文/作者/数据/评论', url: location.href };
  }
  return result;
}

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg && msg.type === 'CAPTURE') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab || !/douyin\.com/.test(tab.url || '')) {
        sendResponse({ ok: false, reason: '当前页不是抖音页面' });
        return;
      }
      chrome.scripting.executeScript(
        { target: { tabId: tab.id }, func: extractOnPage },
        (injected) => {
          const data = injected && injected[0] && injected[0].result;
          if (!data || !data.ok) {
            sendResponse(data || { ok: false, reason: '未读取内容' });
            return;
          }
          fetch(BRIDGE_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
          })
            .then(r => r.json())
            .then(j => sendResponse({ ok: true, sent: j }))
            .catch(e => sendResponse({ ok: false, reason: '桥未启动或不可达: ' + e.message }));
        }
      );
    });
    return true; // 保持消息通道异步打开
  }
});
