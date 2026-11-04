import * as path from 'path';
import { runTests } from '@vscode/test-electron';
(async () => {
  const extensionDevelopmentPath = path.resolve(__dirname, '../..');
  const extensionTestsPath = path.resolve(__dirname, './suite');
  const launchArgs = ['--disable-extensions', '--no-sandbox'];
  if (process.env.QNXRAY_DEMO_USERDIR) launchArgs.push('--user-data-dir', process.env.QNXRAY_DEMO_USERDIR);
  await runTests({ extensionDevelopmentPath, extensionTestsPath, launchArgs });
})().catch(e => { console.error(e); process.exit(1); });
