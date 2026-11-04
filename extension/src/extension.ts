import * as vscode from 'vscode';
import { watch, run, Snapshot } from './cli';
import { ChildProcess } from 'child_process';
import { dashboardHtml } from './dashboard';

let proc: ChildProcess | undefined;
let panel: vscode.WebviewPanel | undefined;
const state = { last: undefined as Snapshot | undefined, snapshots: 0, errors: [] as string[] };

export function activate(ctx: vscode.ExtensionContext) {
  const out = vscode.window.createOutputChannel('QNXray');
  ctx.subscriptions.push(out,
    vscode.commands.registerCommand('qnxray.openDashboard', () => openDashboard(ctx, out)),
    vscode.commands.registerCommand('qnxray.explainCrash', async (bin?: string) => {
      if (!bin) {
        const pick = await vscode.window.showOpenDialog({ title: 'QNX binary to run on the target (cancel = last/mock crash)' });
        bin = pick?.[0]?.fsPath;
      }
      const txt = await run(ctx, ['explain-crash', ...(bin ? [bin] : []), '--json']);
      const doc = await vscode.workspace.openTextDocument({ content: txt, language: 'markdown' });
      await vscode.window.showTextDocument(doc, vscode.ViewColumn.One);
      return txt;
    }),
    vscode.commands.registerCommand('qnxray.timeline', async (match?: string) => {
      match ??= await vscode.window.showInputBox({ prompt: 'Process name filter (empty = all)' }) || undefined;
      const tl = JSON.parse(await run(ctx, ['timeline', '--seconds', '1', '--json', ...(match ? ['--match', match] : [])]));
      panel?.webview.postMessage({ kind: 'timeline', data: tl });
      return tl;
    }),
    vscode.commands.registerCommand('qnxray.ci', async () => {
      const txt = await run(ctx, ['ci', '--seconds', '3']);
      const rep = JSON.parse(txt);
      (rep.exit_code ? vscode.window.showErrorMessage : vscode.window.showInformationMessage)(
        `QNXray CI: ${rep.status} (${rep.crashes.length} crashes, ${rep.inversions.length} inversions)`);
      return rep;
    }),
    vscode.commands.registerCommand('qnxray.build', async () => {
      const f = vscode.window.activeTextEditor?.document.fileName;
      if (!f) { return; }
      try { vscode.window.showInformationMessage('Built ' + (await run(ctx, ['build', f]))); }
      catch (e: any) { vscode.window.showErrorMessage(e.message); }
    }));
  return { state }; // test/automation API
}

function openDashboard(ctx: vscode.ExtensionContext, out: vscode.OutputChannel) {
  panel?.dispose();
  panel = vscode.window.createWebviewPanel('qnxray', 'QNXray', vscode.ViewColumn.Two, { enableScripts: true, retainContextWhenHidden: true });
  panel.webview.html = dashboardHtml();
  panel.webview.onDidReceiveMessage(m => { if (m.cmd) { vscode.commands.executeCommand(m.cmd, ...(m.args || [])); } });
  proc?.kill();
  proc = watch(ctx, s => { state.last = s; state.snapshots++; panel?.webview.postMessage({ kind: 'snapshot', data: s }); },
    e => { state.errors.push(e); out.append(e); });
  panel.onDidDispose(() => { proc?.kill(); panel = undefined; });
}

export function deactivate() { proc?.kill(); }
