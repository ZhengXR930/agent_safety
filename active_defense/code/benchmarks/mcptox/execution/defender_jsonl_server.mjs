#!/usr/bin/env node
import readline from 'node:readline';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../../../..');
const defenderRoot = path.join(repo, '../benchmarks/external/defender');
const { createPromptDefense } = await import(pathToFileURL(path.join(defenderRoot, 'dist/index.mjs')).href);
const defense = createPromptDefense({ blockHighRisk: true });
const input = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of input) {
  try {
    const request = JSON.parse(line);
    const result = await defense.defendToolResult({ content: request.text }, request.tool_name ?? 'unknown');
    process.stdout.write(`${JSON.stringify({ allowed: result.allowed, score: result.tier2Score, risk_level: result.riskLevel })}\n`);
  } catch (error) {
    process.stdout.write(`${JSON.stringify({ error: String(error), allowed: true })}\n`);
  }
}
