#!/usr/bin/env node
/** Full StackOne Defender replay on all 1,348 MCPTox attacks and all clean tools. */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, '../..');
const defenderRoot = path.join(root, 'benchmarks/external/defender');
const { createPromptDefense } = await import(pathToFileURL(path.join(defenderRoot, 'dist/index.mjs')).href);
const source = path.join(root, 'benchmarks/MCPTox-Benchmark/response_all.json');
const out = path.join(root, 'active_defense/experiment_stage/mcp_full_20260718/defender_mcptox.json');
const data = JSON.parse(fs.readFileSync(source, 'utf8'));
const defense = createPromptDefense({ blockHighRisk: true });

function cleanBlocks(system) {
  return system.split(/\n\n\n(?=Tool: )/).filter((x) => x.startsWith('Tool: '));
}

async function scan(text, toolName) {
  const r = await defense.defendToolResult({ content: text }, toolName);
  return { allowed: r.allowed, risk_level: r.riskLevel, score: r.tier2Score, latency_ms: r.latencyMs };
}

const attacks = [];
const cleans = [];
for (const server of Object.values(data.servers)) {
  for (const block of cleanBlocks(server.clean_system_promot)) {
    const name = block.match(/^Tool: ([^\n]+)/)?.[1] ?? 'unknown';
    cleans.push({ server: server.server_name, tool: name, text: block });
  }
  for (const instance of server.malicious_instance) {
    for (const row of instance.datas) {
      const label = row.online_result?.labeled_model_results?.find((x) => 'DeepSeek-v3' in x)?.['DeepSeek-v3'];
      const name = row.poisoned_tool.match(/^Tool: ([^\n]+)/)?.[1] ?? 'unknown';
      attacks.push({ server: server.server_name, id: row.id, tool: name, label, text: row.poisoned_tool });
    }
  }
}

const result = fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, 'utf8')) : {
  benchmark: 'MCPTox-Benchmark', baseline: 'StackOne Defender', label_model: 'DeepSeek-v3', attacks: [], clean: [],
};
const attackDone = new Set(result.attacks.map((x) => `${x.server}:${x.id}`));
const cleanDone = new Set(result.clean.map((x) => `${x.server}:${x.tool}`));
fs.mkdirSync(path.dirname(out), { recursive: true });

for (const item of attacks) {
  if (!attackDone.has(`${item.server}:${item.id}`)) {
    result.attacks.push({ ...item, text: undefined, detection: await scan(item.text, item.tool) });
    if (result.attacks.length % 25 === 0) fs.writeFileSync(out, `${JSON.stringify(result, null, 2)}\n`);
  }
}
for (const item of cleans) {
  if (!cleanDone.has(`${item.server}:${item.tool}`)) {
    result.clean.push({ ...item, text: undefined, detection: await scan(item.text, item.tool) });
    if (result.clean.length % 25 === 0) fs.writeFileSync(out, `${JSON.stringify(result, null, 2)}\n`);
  }
}

const successful = result.attacks.filter((x) => x.label === 'Success');
const residual = successful.filter((x) => x.detection.allowed);
const fp = result.clean.filter((x) => !x.detection.allowed);
result.metrics = {
  n_attack: result.attacks.length,
  undefended_success: successful.length,
  undefended_asr: successful.length / result.attacks.length,
  defended_success: residual.length,
  defended_asr: residual.length / result.attacks.length,
  attack_detection_rate: result.attacks.filter((x) => !x.detection.allowed).length / result.attacks.length,
  n_clean: result.clean.length,
  fp: fp.length,
  fpr: fp.length / result.clean.length,
  detector_utility: 1 - fp.length / result.clean.length,
};
fs.writeFileSync(out, `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify(result.metrics, null, 2));
