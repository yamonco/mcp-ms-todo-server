#!/usr/bin/env node
// Minimal MCP JSON-RPC client for quick calls
// Usage:
//   node client/mcp-client.mjs --url http://localhost:8081 --key <USER_API_KEY> --method tools/list
//   node client/mcp-client.mjs --url http://localhost:8081 --key <USER_API_KEY> --method tools/call --name todo.lists.get --params '{}'

import { argv, exit } from 'node:process';

function parseArgs() {
  const out = {};
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const k = a.slice(2);
      const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : 'true';
      out[k] = v;
    }
  }
  return out;
}

async function main() {
  const args = parseArgs();
  const url = args.url || `http://localhost:${process.env.PORT || '8081'}`;
  const key = args.key || process.env.USER_API_KEY;
  const method = args.method || 'initialize';
  const id = args.id || 'cli';
  const name = args.name;
  const paramsJson = args.params || args['params-json'] || '{}';
  let params = {};
  try { params = JSON.parse(paramsJson); } catch (e) { console.error('[ERR] invalid --params JSON'); exit(2); }
  if (method === 'tools/call') {
    if (!name) { console.error('[ERR] --name required for tools/call'); exit(2); }
    params = { name, arguments: params };
  }
  const body = { jsonrpc: '2.0', id, method, params };
  const headers = { 'content-type': 'application/json' };
  if (key) headers['x-api-key'] = key;
  const r = await fetch(`${url.replace(/\/$/,'')}/mcp`, { method: 'POST', headers, body: JSON.stringify(body) });
  const txt = await r.text();
  try { console.log(JSON.stringify(JSON.parse(txt), null, 2)); } catch { console.log(txt); }
}

main().catch(e => { console.error('[ERR]', e); exit(1); });

