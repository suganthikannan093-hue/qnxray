// Copy the Python CLI (../cli/qnxray) into the extension so the .vsix is self-contained.
const fs = require('fs'), path = require('path');
const src = path.join(__dirname, '..', '..', 'cli', 'qnxray'), dst = path.join(__dirname, '..', 'cli', 'qnxray');
fs.rmSync(path.join(__dirname, '..', 'cli'), { recursive: true, force: true });
fs.cpSync(src, dst, { recursive: true, filter: s => !s.includes('__pycache__') });
console.log('bundled CLI ->', dst);
