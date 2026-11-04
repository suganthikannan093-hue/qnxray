// Integration test inside a real VS Code: dashboard streams snapshots from QNXRAY_TARGET (mock or live).
import * as assert from 'assert';
import * as vscode from 'vscode';
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
export async function run() {
  const target = process.env.QNXRAY_TARGET || 'mock';
  await vscode.workspace.getConfiguration('qnxray').update('target', target, vscode.ConfigurationTarget.Global);
  if (process.env.QNXRAY_SOURCE) await vscode.workspace.getConfiguration('qnxray').update('source', process.env.QNXRAY_SOURCE, vscode.ConfigurationTarget.Global);
  const ext = vscode.extensions.all.find(e => e.packageJSON.name === 'qnxray')!;
  const api: any = await ext.activate();
  const hold = Number(process.env.QNXRAY_DEMO_HOLD || 0);   // demo recording: keep the UI up
  if (hold) { await vscode.commands.executeCommand('workbench.action.closeAllEditors'); await vscode.commands.executeCommand('workbench.action.closeSidebar'); await vscode.commands.executeCommand('workbench.action.closePanel'); for (const c of ['workbench.action.closeAuxiliaryBar', 'notifications.clearAll']) { await vscode.commands.executeCommand(c).then(undefined, () => undefined); } }
  await vscode.commands.executeCommand('qnxray.openDashboard');
  if (hold) { await vscode.commands.executeCommand('workbench.action.editorLayoutSingle'); await vscode.commands.executeCommand('workbench.action.toggleMaximizeEditorGroup').then(undefined, () => undefined); }
  for (let i = 0; i < 60 && api.state.snapshots < 2; i++) { await sleep(1000); }
  const s = api.state.last;
  assert.ok(s, 'no snapshot received: ' + api.state.errors.join(''));
  console.log(`[qnxray-test] target=${target} source=${s.source} processes=${s.processes.length} inversions=${(s.inversions || []).length}`);
  assert.ok(s.processes.length > 3);
  if (hold) { await vscode.commands.executeCommand('notifications.clearAll').then(undefined, () => undefined); console.log('[qnxray-demo] dashboard-live'); await sleep(hold * 1000); }
  if (process.env.QNXRAY_EXPECT_INVERSION) {
    for (let i = 0; i < 20 && !(api.state.last.inversions || []).length; i++) { await sleep(1000); }
    assert.ok(api.state.last.inversions.length > 0, 'expected a live priority inversion');
    console.log('[qnxray-test] inversion:', JSON.stringify(api.state.last.inversions[0]));
    const x: any = await vscode.commands.executeCommand('qnxray.explainInversion');
    console.log('[qnxray-test] ai:', x.mode, x.model || '', (x.summary || x.text || '').slice(0, 120));
    if (hold) { console.log('[qnxray-demo] ai-shown'); await sleep(hold * 1000); }
  }
  if (target !== 'mock') {
    const tl: any = await vscode.commands.executeCommand('qnxray.timeline', 'inversion');
    if (hold) { console.log('[qnxray-demo] timeline-shown'); await sleep(hold * 1000); }
    console.log(`[qnxray-test] timeline ${tl.duration_s}s threads=${Object.keys(tl.threads).length}`);
  }
  if (process.env.QNXRAY_FIX_SOURCE) {
    console.log('[qnxray-demo] fix-start');
    const r: any = await vscode.commands.executeCommand('qnxray.fixVerify', process.env.QNXRAY_FIX_SOURCE);
    console.log(`[qnxray-test] fix ${r.status} ${r.before_s}s -> ${r.after_s}s (${r.fix?.mode})`);
    assert.strictEqual(r.status, 'verified');
    if (hold) { console.log('[qnxray-demo] fix-shown'); await sleep(hold * 1000); }
  }
}
