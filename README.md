# Etherscan Flow — Agent Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

An installable [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that turns any AI agent into an on-chain investigator. Give it a transaction hash or a wallet address, and it calls the **Etherscan API V2** to trace the full money flow — victim → attacker → laundering hops → CEX deposit — and writes a single **Etherscan Flow Case** JSON file (a `nodes` + `edges` graph) ready to drop into the [Etherscan Flow](https://etherscan.io) visualization canvas.

Works with Claude Code, Claude.ai, and other agents that support the skills format. Output is **JSON only** — no chat prose, no hallucinated edges: every node and edge is grounded in a real API response.

## What it does

1. **Validates** every address / tx hash / chain id before making a call.
2. **Resolves credentials** securely (see below) — the key never has to touch the chat.
3. **Traces the flow** via Etherscan API V2 (or an Etherscan MCP server): tx details, internal txs, ERC-20/721 transfers.
4. **Classifies** each address — victim, attacker, CEX deposit, mixer, bridge, DEX router, sweeper bot… — using API evidence, never a user's claim alone.
5. **Follows the money** up to N hops (default 2, cap 4), stopping at CEX deposits, mixers, and bridges.
6. **Detects patterns** — approval drains, flash-loan attacks, rug pulls, wash trading, rapid scatter, mixer usage, bridge hops, CEX fast deposits.
7. **Outputs** a single `case-{id}-flow.json` in the Etherscan Flow Case schema.

**Supported chains:** Ethereum (default), BNB Chain, Polygon, Arbitrum, Optimism, Base, Avalanche, Fantom.

## Installation

### Claude Code / CLI agents

Clone into your agent's skills directory:

```bash
git clone https://github.com/homeyong/etherscan-flow.git ~/.claude/skills/etherscan-flow
```

The skill is then available as `/etherscan-flow`.

### Claude.ai

Download this repository as a ZIP, then upload it at **claude.ai/customize/skills**. On paid plans, allowlist `api.etherscan.io` in your skill's network settings so it can reach the API.

## Providing your Etherscan API key

An Etherscan API key is read-only and rate-limited, but you should still keep it out of the chat transcript. The skill resolves credentials in this order — the first that applies wins:

1. **Inline override** — `apikey=YOUR_KEY` anywhere in your prompt (per-run override).
2. **Etherscan MCP server** — if Etherscan MCP tools are available, the skill uses them and never handles a key at all (most secure).
3. **Environment variable** — `export ETHERSCAN_API_KEY=…`; referenced by name in the shell so the value never enters the model's context.
4. **Local key file** — `~/.etherscan/key`.
5. **Demo key** — the rate-limited free tier, as a last resort.

Get a free key at [etherscan.io/apis](https://etherscan.io/apis).

## Usage

Trigger it by pasting a hash or address and asking to investigate:

```
trace this scam 0x<txhash>
follow the money from this victim wallet 0x<address>
build a case for this hack 0x<address> apikey=YOUR_KEY
this is the scammer address 0x<address>, find the victims
```

The result is a JSON file. Open the [Etherscan Flow](https://etherscan.io) tool, choose **Import**, and paste it — the schema maps one-to-one, no reformatting needed.

## Output schema

The skill emits the native **Etherscan Flow Case** schema:

```json
{
  "id": "case-a1b2c3d4",
  "name": "0xabcd… — approval drain traced to Binance 14",
  "schemaVersion": 1,
  "nodes": [ { "id": "victim01", "address": "0x…", "label": "Victim", "role": "victim_wallet", "hop": 0, "balance": "0.0 ETH", "notes": "…", "x": 0, "y": 0 } ],
  "edges": [ { "id": "e1", "source": "victim01", "target": "atk01", "amount": "5000", "token": "USDT", "txcount": 1, "type": "token_transfer", "txhash": "0x…", "timestamp": "2026-03-15T10:23:00Z" } ],
  "_meta": { "chain": "ethereum", "financials": {}, "timeline": [], "patterns": [], "gaps": [], "disclaimer": "…" }
}
```

Roles, labels, and notes are AI inference over public Etherscan data — **not** Etherscan verdicts, accusations, or legal findings. See the disclaimer in every `_meta` block.

## Files

| File | Purpose |
|------|---------|
| [`SKILL.md`](./SKILL.md) | The skill itself — instructions, API workflows, scoring tables, output contract |
| `LICENSE` | MIT |

## Support

Issues and feedback: please open a [GitHub issue](https://github.com/homeyong/etherscan-flow/issues).

## License

[MIT](./LICENSE)
