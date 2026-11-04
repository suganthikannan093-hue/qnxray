import * as path from 'path';
import { runTests } from '@vscode/test-electron';
(async () => {
  const extensionDevelopmentPath = path.resolve(__dirname, '../..');
  const extensionTestsPath = path.resolve(__dirname, './suite');
  await runTests({ extensionDevelopmentPath, extensionTestsPath, launchArgs: ['--disable-extensions', '--no-sandbox'] });
})().catch(e => { console.error(e); process.exit(1); });
