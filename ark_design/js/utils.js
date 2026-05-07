var _uidCounter = 0;
function uid() { return Date.now().toString(36) + (++_uidCounter).toString(36) + Math.random().toString(36).slice(2, 5); }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
function fmt(n) { return Number(n||0).toLocaleString('zh-CN'); }
function debounce(fn, ms) { var t; return function() { var a=arguments,ctx=this; clearTimeout(t); t=setTimeout(function(){fn.apply(ctx,a)},ms); }; }
function showToast(msg, type) {
  var el = document.getElementById('toast');
  if (!el) return;
  el.textContent = msg;
  el.className = 'toast show' + (type ? ' toast-' + type : '');
  clearTimeout(el._t);
  el._t = setTimeout(function() { el.className = 'toast'; }, 3000);
}
function formatDate(ts) {
  var d = new Date(ts);
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}
function formatDateTime(ts) {
  var d = new Date(ts);
  return formatDate(ts) + ' ' + String(d.getHours()).padStart(2,'0') + ':' + String(d.getMinutes()).padStart(2,'0');
}
