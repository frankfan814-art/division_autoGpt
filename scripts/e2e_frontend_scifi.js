#!/usr/bin/env node
/**
 * End-to-end runner: start backend + frontend, drive UI via Playwright,
 * trigger generation of a ~2000-word sci-fi novel, and export the result.
 *
 * Prerequisites:
 *   1) Backend dependencies installed + venv ready
 *   2) Frontend dependencies installed (`npm install` in frontend)
 *   3) Playwright installed (`npm install -D playwright` in frontend)
 *
 * Usage (from repo root):
 *   node scripts/e2e_frontend_scifi.js
 *   # or
 *   (cd frontend && npm run e2e:scifi)
 */

import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';
import { setTimeout as wait } from 'timers/promises';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

// Resolve playwright from frontend's node_modules to avoid global install assumptions.
const require = createRequire(new URL('../frontend/package.json', import.meta.url));
const { chromium } = require('playwright');

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const FRONTEND_DIR = path.join(ROOT, 'frontend');
const TEST_RESULTS_DIR = path.join(ROOT, 'test_results');

const BACKEND_PORT = 8000;
const FRONTEND_PORT = 4173;
const TARGET_WORDS = 2000;
const MAX_RUN_MS = 15 * 60 * 1000; // 15 minutes guard

function spawnProc(command, options = {}) {
  const child = spawn('bash', ['-lc', command], {
    stdio: 'inherit',
    env: { ...process.env, ...options.env },
    cwd: options.cwd || ROOT,
  });
  return child;
}

async function waitForHttp(url, timeoutMs = 120000) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const res = await fetch(url, { method: 'GET' });
      if (res.ok) return true;
    } catch (err) {
      // ignore until timeout
    }
    await wait(1500);
  }
  throw new Error(`Timed out waiting for ${url}`);
}

async function exportNovel(sessionId) {
  const res = await fetch(`http://localhost:${BACKEND_PORT}/sessions/${sessionId}/export`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ format: 'txt', include_metadata: true }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Export failed: ${res.status} ${text}`);
  }
  return await res.text();
}

async function main() {
  const backendCmd = `cd ${ROOT} && source venv/bin/activate && uvicorn creative_autogpt.api.main:app --host 0.0.0.0 --port ${BACKEND_PORT}`;
  const frontendCmd = `cd ${FRONTEND_DIR} && VITE_API_BASE_URL=http://localhost:${BACKEND_PORT} npm run dev -- --host --port ${FRONTEND_PORT}`;

  const backend = spawnProc(backendCmd, { env: { PYTHONPATH: path.join(ROOT, 'src') } });
  await waitForHttp(`http://localhost:${BACKEND_PORT}/health`);

  const frontend = spawnProc(frontendCmd, { cwd: FRONTEND_DIR });
  await waitForHttp(`http://localhost:${FRONTEND_PORT}/`);

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage({ viewport: { width: 1280, height: 800 } });

  let sessionId = null;
  const startedAt = Date.now();

  try {
    await page.goto(`http://localhost:${FRONTEND_PORT}/create`, { waitUntil: 'networkidle' });

    await page.getByLabel('项目标题').fill('科幻 E2E 2000 字');
    await page.getByLabel('创作模式').selectOption('novel');
    await page.getByLabel('章节数量').selectOption('4');
    await page.getByLabel('类型/流派').fill('科幻');
    await page.getByLabel('写作风格').fill('硬科幻，宏大史诗，冷静理性');
    await page.getByLabel('创作要求').fill(`目标约 ${TARGET_WORDS} 字，围绕星际探索与人工智能，保持严谨科学细节与史诗感。`);

    await page.getByRole('button', { name: '创建项目' }).click();
    await page.waitForURL('**/workspace/*', { timeout: 120000 });

    const url = page.url();
    sessionId = url.split('/').pop();
    if (!sessionId) throw new Error('未获取到 sessionId');

    console.log(`➡️  Session created: ${sessionId}`);

    // Start generation via WebSocket in the page context
    await page.evaluate(
      (sid) => {
        return new Promise((resolve, reject) => {
          const ws = new WebSocket('ws://localhost:8000/ws/ws');
          let startedConfirmed = false;
          const startTimer = setTimeout(() => {
            if (!startedConfirmed) {
              ws.close();
              reject(new Error('WebSocket start confirmation timeout'));
            }
          }, 30 * 1000); // 30 seconds for start confirmation
          
          const completionTimer = setTimeout(() => {
            ws.close();
            reject(new Error('Generation completion timeout after 15 minutes'));
          }, 15 * 60 * 1000); // 15 minutes for completion

          ws.onopen = () => {
            console.log('WS opened, sending subscribe+start');
            ws.send(JSON.stringify({ event: 'subscribe', session_id: sid }));
            ws.send(JSON.stringify({ event: 'start', session_id: sid }));
          };

          ws.onmessage = (event) => {
            try {
              const msg = JSON.parse(event.data);
              console.log('WS message:', msg.event);
              
              if (msg.event === 'started') {
                clearTimeout(startTimer);
                startedConfirmed = true;
                console.log('Start confirmed, waiting for completion...');
              }
              
              if (msg.event === 'completed') {
                clearTimeout(completionTimer);
                ws.close();
                console.log('Generation completed');
                resolve(msg);
              }
              
              if (msg.event === 'failed') {
                clearTimeout(startTimer);
                clearTimeout(completionTimer);
                ws.close();
                reject(new Error(msg.error || 'Generation failed'));
              }
              
              if (msg.event === 'error') {
                clearTimeout(startTimer);
                clearTimeout(completionTimer);
                ws.close();
                reject(new Error(msg.message || 'WebSocket error'));
              }
            } catch (err) {
              clearTimeout(startTimer);
              clearTimeout(completionTimer);
              ws.close();
              reject(err);
            }
          };

          ws.onerror = (err) => {
            clearTimeout(startTimer);
            clearTimeout(completionTimer);
            ws.close();
            reject(err instanceof Error ? err : new Error('WebSocket error'));
          };
        });
      },
      sessionId,
    );

    console.log('✅ WebSocket reported completion, exporting novel...');

    const novel = await exportNovel(sessionId);
    const outfile = path.join(TEST_RESULTS_DIR, `frontend_scifi_${Date.now()}.txt`);
    fs.writeFileSync(outfile, novel, 'utf8');

    console.log(`✅ 导出完成: ${outfile}`);
    const elapsed = ((Date.now() - startedAt) / 1000).toFixed(1);
    console.log(`耗时: ${elapsed} 秒`);
  } finally {
    await browser.close();
    backend.kill('SIGTERM');
    frontend.kill('SIGTERM');
  }
}

main().catch((err) => {
  console.error('❌ E2E 运行失败:', err);
  process.exit(1);
});
