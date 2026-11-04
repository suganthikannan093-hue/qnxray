import { spawn, ChildProcess, execFile } from 'child_process';
import * as path from 'path';
import * as vscode from 'vscode';

export interface Thread { tid: number; name: string; priority: number; policy: string; state: string; blocked_on: string | null; cpu: number | null; }
export interface Process { pid: number; name: string; threads: Thread[]; }
export interface Snapshot { timestamp: number; source: string; processes: Process[]; }

function cfg() { return vscode.workspace.getConfiguration('qnxray'); }
function cliEnv(ctx: vscode.ExtensionContext) {
  // CLI lives next to the extension in the monorepo; packaged builds bundle it under ./cli
  const cliDir = path.join(ctx.extensionPath, '..', 'cli');
  return { ...process.env, PYTHONPATH: cliDir };
}
export function watch(ctx: vscode.ExtensionContext, onSnap: (s: Snapshot) => void): ChildProcess {
  const p = spawn(cfg().get<string>('python', 'python3'),
    ['-m', 'qnxray.cli', '--target', cfg().get<string>('target', 'mock'), 'watch', '--interval', String(cfg().get<number>('interval', 1))],
    { env: cliEnv(ctx) });
  let buf = '';
  p.stdout.on('data', d => { buf += d; let i; while ((i = buf.indexOf('\n')) >= 0) { const line = buf.slice(0, i); buf = buf.slice(i + 1); try { onSnap(JSON.parse(line)); } catch { /* ignore partial */ } } });
  return p;
}
export function run(ctx: vscode.ExtensionContext, args: string[]): Promise<string> {
  return new Promise((res, rej) => execFile(cfg().get<string>('python', 'python3'),
    ['-m', 'qnxray.cli', '--target', cfg().get<string>('target', 'mock'), ...args], { env: cliEnv(ctx) },
    (e, out, err) => e ? rej(new Error(err || e.message)) : res(out)));
}
