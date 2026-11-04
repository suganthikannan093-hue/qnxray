import * as vscode from 'vscode';
import { watch, run, Snapshot } from './cli';
import { ChildProcess } from 'child_process';

let proc: ChildProcess | undefined;

export function activate(ctx: vscode.ExtensionContext) {
  ctx.subscriptions.push(
    vscode.commands.registerCommand('qnxray.openDashboard', () => openDashboard(ctx)),
    vscode.commands.registerCommand('qnxray.explainCrash', async () => {
      const txt = await run(ctx, ['explain-crash']);
      const doc = await vscode.workspace.openTextDocument({ content: txt, language: 'markdown' });
      vscode.window.showTextDocument(doc);
    }),
    vscode.commands.registerCommand('qnxray.build', async () => {
      const f = vscode.window.activeTextEditor?.document.fileName;
      if (!f) { return; }
      try { vscode.window.showInformationMessage('Built ' + (await run(ctx, ['build', f]))); }
      catch (e: any) { vscode.window.showErrorMessage(e.message); }
    }));
}

function openDashboard(ctx: vscode.ExtensionContext) {
  const panel = vscode.window.createWebviewPanel('qnxray', 'QNXray', vscode.ViewColumn.Two, { enableScripts: true });
  panel.webview.html = html();
  proc?.kill();
  proc = watch(ctx, (s: Snapshot) => panel.webview.postMessage(s));
  panel.onDidDispose(() => proc?.kill());
}

function html(): string {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
  body{font-family:var(--vscode-font-family);color:var(--vscode-foreground)}
  table{border-collapse:collapse;width:100%} td,th{padding:2px 6px;text-align:left}
  .RUNNING{color:#4caf50}.READY{color:#ffc107}.MUTEX,.SEND,.REPLY{color:#f44336}
  </style></head><body><h2>QNXray <small id="src"></small></h2>
  <table><thead><tr><th>pid</th><th>process</th><th>tid</th><th>prio</th><th>state</th><th>blocked on</th><th>cpu</th></tr></thead><tbody id="t"></tbody></table>
  <script>
  window.addEventListener('message', e => { const s = e.data; document.getElementById('src').textContent = '(' + s.source + ')';
    document.getElementById('t').innerHTML = s.processes.flatMap(p => p.threads.map(t =>
      '<tr><td>'+p.pid+'</td><td>'+p.name+'</td><td>'+t.tid+'</td><td>'+t.priority+t.policy+'</td><td class="'+t.state+'">'+t.state+'</td><td>'+(t.blocked_on??'')+'</td><td>'+(t.cpu??'')+'</td></tr>')).join(''); });
  </script></body></html>`;
}

export function deactivate() { proc?.kill(); }
