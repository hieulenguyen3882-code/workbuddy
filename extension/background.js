// MVP 0 背景服务（MV3 service worker）
// 职责：点击扩展图标 → 抓取当前抖音活动页可见 DOM → POST 给本地桥。
// 读取纪律：只在主动点击时读取当前 tab；解析失败返回 {ok:false}；绝不伪造内容。
//
// 选择器取证记录（2026-09-14，基于真实 douyin.com/video/<id> 页面 DOM）：
//   [data-e2e="video-detail"]            详情页容器
//   [data-e2e="detail-video-info"]       标题+正文信息区（H1=标题，innerText=完整文案）
//   [data-e2e="user-info"]               作者区（名称链接 a[href*="/user/"] 内首个 span=昵称，徽章为独立 DIV 不取）
//   [data-e2e="video-player-digg"]       点赞数
//   [data-e2e="feed-comment-icon"]       评论数
//   [data-e2e="video-player-collect"]    收藏数
//   [data-e2e="video-player-share"]      分享数
//   [data-e2e="detail-video-publish-time"] 发布时间
//   [data-e2e="comment-item"]            已加载评论条目

const BRIDGE_URL = 'http://localhost:8910/ingest';

// 注入到页面执行的提取函数（在抖音已登录会话的 DOM 上只读，不碰登录/风控）
function extractOnPage() {
  const q = (s) => document.querySelector(s);
  const qa = (s) => Array.from(document.querySelectorAll(s));
  const txt = (el) => (el && el.innerText ? el.innerText.trim() : '');

  const result = {
    ok: true,
    capturedAt: new Date().toISOString(),
    url: location.href,
    type: 'unknown',
    fields: {}
  };

  // 页面类型判断（只用于打标，不用于决定是否读取）
  const isVideo = /\/video\/\d+/.test(location.href) ||
    !!q('[data-e2e="video-detail"]') || !!q('[data-e2e="detail-video-info"]');
  const isProfile = !!q('[data-e2e="user-info"]') && !isVideo;
  result.type = isVideo ? 'video' : (isProfile ? 'profile' : 'unknown');

  // ---- 标题 / 正文（H1=标题；H1 父块=正文区，去掉"展开/收起"控件文案，排除底部统计块）----
  let caption = null;
  let description = null;
  const info = q('[data-e2e="detail-video-info"]');
  if (info) {
    const h1 = info.querySelector('h1');
    // 正文块取 H1 的父容器：真实页面上该容器只含标题/正文/话题，不含点赞等数字
    const block = h1 && h1.parentElement ? h1.parentElement : info;
    const clean = txt(block).replace(/^(展开|收起)\s*/, '').trim();
    caption = h1 ? txt(h1) : null;
    if (clean) {
      if (caption && clean.startsWith(caption)) {
        const rest = clean.slice(caption.length).replace(/^\s*\n+/, '').trim();
        description = rest || null;
      } else {
        description = clean;
      }
    }
  }
  // 兜底：meta description / document.title 仅在 URL 已确认是视频详情页时使用，
  // 避免在首页/搜索页等非视频页误报成功（读取纪律：读不到就明确返回"未读取内容"）
  const isVideoUrl = /\/video\/\d+|\/note\/\d+/.test(location.href);
  if (!caption && isVideoUrl) {
    const mc = q('meta[name="description"]');
    const content = mc ? (mc.getAttribute('content') || '').trim() : '';
    if (content) {
      caption = content.split('\n')[0].trim();
      if (!description) description = content;
    }
  }
  if (!caption && isVideoUrl) {
    const t = document.title ? document.title.split(' - ')[0].trim() : '';
    if (t && t !== '抖音') caption = t;
  }

  // ---- 作者（名称链接内首个 span；"认证徽章"是独立 DIV，不取）----
  let author = null;
  const ui = q('[data-e2e="user-info"]');
  if (ui) {
    const nameLink = qa('a[href*="/user/"]').filter(a => txt(a)).find(a => ui.contains(a));
    if (nameLink) {
      const span = nameLink.querySelector('span');
      const t = span ? txt(span) : '';
      if (t && t !== '认证徽章') {
        author = t;
      } else {
        author = txt(nameLink).split('认证徽章')[0].trim() || null;
      }
    }
    if (!author) {
      const first = txt(ui).replace(/认证徽章/g, '').split(/粉丝|获赞|关注/)[0].trim();
      author = first || null;
    }
  }

  // ---- 互动数据（点赞/评论/收藏/分享/发布时间）----
  const stats = {};
  const pick = (sels, key) => {
    for (const s of sels) {
      const t = txt(q(s));
      if (t) { stats[key] = t; return; }
    }
  };
  pick(['[data-e2e="video-player-digg"]'], 'likeCount');
  pick(['[data-e2e="feed-comment-icon"]', '[data-e2e="video-player-comment"]'], 'commentCount');
  pick(['[data-e2e="video-player-collect"]'], 'collectCount');
  pick(['[data-e2e="video-player-share"]'], 'shareCount');
  const pt = txt(q('[data-e2e="detail-video-publish-time"]'));
  if (pt) stats.publishTime = pt.replace(/^发布时间[:：]\s*/, '');

  // ---- 评论区（当前已加载的，取前 12 条原文）----
  const comments = qa('[data-e2e="comment-item"]')
    .slice(0, 12)
    .map(el => txt(el))
    .filter(Boolean);

  result.fields = { caption, description, author, stats, comments };

  // 读取纪律：关键字段全缺失即明确失败，绝不补点伪造
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
