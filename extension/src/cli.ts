import { spawn, ChildProcess, execFile } from 'child_process';
import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

export interface Thread { tid: number; name: string; priority: number; policy: string; state: string; blocked_on: string | null; cpu: number | null; }
export interface Process { pid: number; name: string; threads: Thread[]; }
export interface Inversion { waiter: string; prio: number; state: string; owner: string; owner_pid: number; owner_max_prio: number; preempted_by: string[]; severity: string; }
export interface Snapshot { timestamp: number; source: string; processes: Process[]; inversions?: Inversion[]; }

function cfg() { return vscode.workspace.getConfiguration('qnxray'); }
export function cliDir(ctx: vscode.ExtensionContext) {
  // Packaged .vsix bundles the Python CLI under ./cli; in the monorepo it is ../cli
  const bundled = path.join(ctx.extensionPath, 'cli');
  return fs.existsSync(path.join(bundled, 'qnxray')) ? bundled : path.join(ctx.extensionPath, '..', 'cli');
}
function cliEnv(ctx: vscode.ExtensionContext) { return { ...process.env, PYTHONPATH: cliDir(ctx) }; }
function base(): string[] { return ['-m', 'qnxray', '--target', cfg().get<string>('target', 'mock')]; }
export function watch(ctx: vscode.ExtensionContext, onSnap: (s: Snapshot) => void, onErr: (e: string) => void): ChildProcess {
  const p = spawn(cfg().get<string>('python', 'python3'), [...base(), 'watch', '--interval', String(cfg().get<number>('interval', 1))], { env: cliEnv(ctx) });
  let buf = '';
  p.stdout.on('data', d => { buf += d; let i; while ((i = buf.indexOf('\n')) >= 0) { const line = buf.slice(0, i); buf = buf.slice(i + 1); try { onSnap(JSON.parse(line)); } catch { /* partial */ } } });
  p.stderr.on('data', d => onErr(String(d)));
  return p;
}
export function run(ctx: vscode.ExtensionContext, args: string[], timeout = 180000): Promise<string> {
  return new Promise((res, rej) => execFile(cfg().get<string>('python', 'python3'), [...base(), ...args],
    { env: cliEnv(ctx), timeout, maxBuffer: 64 << 20 },
    (e, out, err) => (e && !out) ? rej(new Error(err || e.message)) : res(out)));
}
