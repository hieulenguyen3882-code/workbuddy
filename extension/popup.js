// 弹窗：点「抓取当前页」→ 通知 background 抓取 → 显示结果
document.getElementById('cap').addEventListener('click', () => {
  document.getElementById('status').textContent = '抓取中…';
  document.getElementById('out').textContent = '';
  chrome.runtime.sendMessage({ type: 'CAPTURE' }, (resp) => {
    const ok = resp && resp.ok;
    document.getElementById('status').textContent = ok
      ? '已发送到中枢'
      : ('失败：' + ((resp && resp.reason) || '未知'));
    document.getElementById('out').textContent = JSON.stringify(resp, null, 2);
  });
});
