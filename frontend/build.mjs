import { cp, mkdir, rm } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve, sep } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));
const source = join(root, 'site');
const output = join(root, 'dist');
if (!resolve(output).startsWith(resolve(root) + sep)) throw new Error('Invalid frontend output path');
await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(source, output, { recursive: true });
console.log('AgentOS research frontend built to frontend/dist');
