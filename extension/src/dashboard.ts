// Webview UI: target header, findings (priority inversions), per-CPU lanes, thread table, trace timeline.
export function dashboardHtml(): string {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body{font-family:var(--vscode-font-family);color:var(--vscode-foreground);font-size:12px}
h2{margin:4px 0} .muted{opacity:.6} .card{border:1px solid var(--vscode-panel-border);border-radius:6px;padding:6px;margin:6px 0}
table{border-collapse:collapse;width:100%} td,th{padding:1px 6px;text-align:left} tr:hover{background:var(--vscode-list-hoverBackground)}
.RUNNING{color:#4caf50}.READY{color:#ffc107}.MUTEX,.SEND,.REPLY{color:#f44336}.RECEIVE{opacity:.7}
.finding{border-left:4px solid #f44336;padding:4px 8px;margin:4px 0;background:rgba(244,67,54,.08)}
.finding.medium{border-color:#ffc107}.ok{border-left:4px solid #4caf50;padding:4px 8px}
.cpus{display:flex;gap:6px}.cpu{flex:1;border:1px solid var(--vscode-panel-border);border-radius:4px;padding:4px;min-height:40px}
.lane{display:flex;align-items:center;gap:6px;margin:1px 0}.lane .n{width:170px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis}
.bar{position:relative;flex:1;height:12px;background:rgba(128,128,128,.15)}.seg{position:absolute;top:0;height:12px;background:#4caf50}
button{background:var(--vscode-button-background);color:var(--vscode-button-foreground);border:0;padding:3px 8px;border-radius:3px;cursor:pointer}
input{background:var(--vscode-input-background);color:var(--vscode-input-foreground);border:1px solid var(--vscode-input-border)}
</style></head><body>
<h2>QNXray <span id="src" class="muted"></span></h2>
<div><button onclick="cmd('qnxray.timeline',[document.getElementById('m').value||undefined])">Capture trace (1s)</button>
<button onclick="cmd('qnxray.explainCrash')">Run &amp; explain crash</button> <button onclick="cmd('qnxray.ci')">Run CI gate</button>
 filter <input id="m" placeholder="process name" oninput="render()"></div>
<div class="card"><b>Findings</b><div id="find" class="muted">waiting for target…</div></div>
<div class="card"><b>CPUs</b> <span class="muted">(threads currently RUNNING)</span><div id="cpus" class="cpus"></div></div>
<div class="card"><b>Trace timeline</b> <span id="tlh" class="muted">not captured</span><div id="tl"></div></div>
<div class="card"><b>Threads</b> <span id="cnt" class="muted"></span><table><thead><tr><th>pid</th><th>process</th><th>tid</th><th>prio</th><th>state</th><th>blocked on</th><th>cpu</th></tr></thead><tbody id="t"></tbody></table></div>
<script>
const vs = acquireVsCodeApi(); let snap = null;
function cmd(c,a){ vs.postMessage({cmd:c,args:a||[]}); }
const esc = s => String(s??'').replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));
function render(){
  if(!snap) return; const f=(document.getElementById('m').value||'').toLowerCase();
  document.getElementById('src').textContent='('+snap.source+', '+snap.processes.length+' processes, '+new Date(snap.timestamp*1000).toLocaleTimeString()+')';
  const inv=snap.inversions||[];
  document.getElementById('find').innerHTML = inv.length ? inv.map(i=>'<div class="finding '+i.severity+'"><b>Priority inversion</b> ('+i.severity+'): '+esc(i.waiter)+' prio '+i.prio+' is '+i.state+'-blocked on '+esc(i.owner)+'['+i.owner_pid+'] running at prio '+i.owner_max_prio+(i.preempted_by.length?' — preempted by '+esc(i.preempted_by.join(', ')):'')+'</div>').join('') : '<div class="ok">No priority inversions</div>';
  const cpus={}; snap.processes.forEach(p=>p.threads.forEach(t=>{ if(t.state==='RUNNING'&&t.cpu!=null)(cpus[t.cpu]=cpus[t.cpu]||[]).push(p.name.split('/').pop()+'/'+t.tid+' @'+t.priority); }));
  const ncpu=Math.max(4,...Object.keys(cpus).map(Number).map(x=>x+1));
  document.getElementById('cpus').innerHTML=[...Array(ncpu).keys()].map(c=>'<div class="cpu"><b>CPU '+c+'</b><br>'+esc((cpus[c]||['idle / n.a.']).join('<br>'))+'</div>').join('');
  const rows=snap.processes.filter(p=>!f||p.name.toLowerCase().includes(f)).flatMap(p=>p.threads.map(t=>'<tr><td>'+p.pid+'</td><td>'+esc(p.name)+'</td><td>'+t.tid+'</td><td>'+t.priority+t.policy+'</td><td class="'+t.state+'">'+t.state+'</td><td>'+esc(t.blocked_on)+'</td><td>'+(t.cpu??'')+'</td></tr>'));
  document.getElementById('cnt').textContent=rows.length+' threads'; document.getElementById('t').innerHTML=rows.join('');
}
function timeline(tl){
  document.getElementById('tlh').textContent=tl.duration_s.toFixed(3)+'s, '+Object.keys(tl.threads).length+' threads (green = on CPU)';
  const segs={}; Object.values(tl.cpus).forEach(ss=>ss.forEach(s=>(segs[s.thread]=segs[s.thread]||[]).push(s)));
  const d=tl.duration_s||1;
  document.getElementById('tl').innerHTML=Object.entries(tl.threads).slice(0,60).map(([k,i])=>{
    const st=Object.entries(i.states_s).slice(0,2).map(([s,v])=>s+' '+v.toFixed(3)+'s').join(', ');
    return '<div class="lane"><span class="n" title="'+esc(i.name)+'">'+esc(k+' '+i.name.split('/').pop())+'</span><div class="bar">'+
      (segs[k]||[]).map(s=>'<div class="seg" style="left:'+(s.start/d*100)+'%;width:'+Math.max(.3,(s.end-s.start)/d*100)+'%"></div>').join('')+'</div><span class="muted">'+st+'</span></div>'; }).join('');
}
window.addEventListener('message', e => { const m=e.data; if(m.kind==='snapshot'){ snap=m.data; render(); } else if(m.kind==='timeline') timeline(m.data); });
</script></body></html>`;
}
