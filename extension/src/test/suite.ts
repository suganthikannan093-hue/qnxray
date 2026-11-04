// Integration test inside a real VS Code: dashboard streams snapshots from QNXRAY_TARGET (mock or live).
import * as assert from 'assert';
import * as vscode from 'vscode';
const sleep = (ms: number) => new Promise(r => setTimeout(r, ms));
export async function run() {
  const target = process.env.QNXRAY_TARGET || 'mock';
  await vscode.workspace.getConfiguration('qnxray').update('target', target, vscode.ConfigurationTarget.Global);
  const ext = vscode.extensions.all.find(e => e.packageJSON.name === 'qnxray')!;
  const api: any = await ext.activate();
  await vscode.commands.executeCommand('qnxray.openDashboard');
  for (let i = 0; i < 60 && api.state.snapshots < 2; i++) { await sleep(1000); }
  const s = api.state.last;
  assert.ok(s, 'no snapshot received: ' + api.state.errors.join(''));
  console.log(`[qnxray-test] target=${target} source=${s.source} processes=${s.processes.length} inversions=${(s.inversions || []).length}`);
  assert.ok(s.processes.length > 3);
  if (process.env.QNXRAY_EXPECT_INVERSION) {
    for (let i = 0; i < 20 && !(api.state.last.inversions || []).length; i++) { await sleep(1000); }
    assert.ok(api.state.last.inversions.length > 0, 'expected a live priority inversion');
    console.log('[qnxray-test] inversion:', JSON.stringify(api.state.last.inversions[0]));
  }
  if (target !== 'mock') {
    const tl: any = await vscode.commands.executeCommand('qnxray.timeline', 'inversion');
    console.log(`[qnxray-test] timeline ${tl.duration_s}s threads=${Object.keys(tl.threads).length}`);
  }
}
