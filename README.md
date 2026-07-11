# Etherscan Flow — Agent Skill

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)

An installable [Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview) that maps **any** on-chain money flow. Give it a **transaction hash**, a **wallet address**, or a resolvable **business/entity scope**, and it calls the **Etherscan API V2** to trace the flow and write a single **Etherscan Flow Case** JSON (`nodes` + `edges`) you can import straight into the [Etherscan Flow](https://etherscan.io) canvas.

Use it for a plain transfer, a token launch, a DeFi swap route, an NFT mint — or a full scam/hack investigation (victim → attacker → laundering hops → CEX deposit).

Output is **JSON only** — every node and edge is grounded in a real API response, never invented.

The skill has two modes, plus a document-import path:

- **Strict trace mode:** start from a tx hash or address and follow the money.
- **Business/entity profile mode:** start from a DAO/protocol/project/business scope, resolve it to verified addresses, then summarize income, spending, categories, and totals inside the JSON.
- **Document import (into hypothesis validation):** paste a draft case, notes, or any link you typed yourself — a gist, a tweet/X post, a news article, a blog post, a forum thread. The skill extracts the addresses and flow claims from it and validates every one against the live API — nothing from the document is copied into the output unverified. The URL fetch is read-only, never carries your API key, and only ever hits links *you* typed (it never crawls links found inside a page). If a page can't be read (login wall, JS-only), it asks you to paste the text instead of stopping.

Named entities such as `ENS DAO` are treated as scope hypotheses, not evidence. The skill resolves them to real `0x...` addresses from user-provided addresses, API-resolved ENS names, or its known-entity scope table — which ships with the well-known ENS DAO candidates (treasury timelock, registrar controllers, token, governor) so `show ENS DAO as a business` works out of the box. Every table candidate is still validated live before it appears in a case.

## How it works

```mermaid
flowchart LR
    A["You paste a tx hash<br/>or wallet address"] --> B["etherscan-flow skill<br/>(runs inside your agent)"]
    B --> C["Etherscan API V2<br/>or Etherscan MCP"]
    C --> D["Trace flow · classify<br/>entities · follow hops"]
    D --> E["Etherscan Flow Case JSON<br/>nodes + edges"]
    E --> F["Import into the<br/>Etherscan Flow canvas"]
```

Supported chains: **Ethereum** (default), BNB Chain, Polygon, Arbitrum, Optimism, Base, Avalanche, Fantom.

The skill ships as a lean `SKILL.md` (hard rules, routing, credential order) plus `references/*.md` files the agent reads on demand per step (progressive disclosure — keeps context small so any skills-capable model handles it well). Install the whole folder; `SKILL.md` alone is not the complete skill.

## Quick start

Pick your tool. Steps are given for **macOS**, **Linux**, and **Windows**.

<details open>
<summary><b>Claude Code (CLI)</b></summary>

Clone into your personal skills folder, then invoke `/etherscan-flow`.

**macOS / Linux**
```bash
git clone https://github.com/homeyong/etherscan-flow.git ~/.claude/skills/etherscan-flow
```

**Windows (PowerShell)**
```powershell
git clone https://github.com/homeyong/etherscan-flow.git "$env:USERPROFILE\.claude\skills\etherscan-flow"
```

Then in Claude Code: `/etherscan-flow trace this scam 0x…`
</details>

<details>
<summary><b>Codex CLI</b></summary>

Codex reads skills from `~/.codex/skills/` (support added Dec 2025). Clone into it, and Codex auto-discovers the skill from `SKILL.md`'s name + description.

**macOS / Linux**
```bash
git clone https://github.com/homeyong/etherscan-flow.git ~/.codex/skills/etherscan-flow
```

**Windows (PowerShell)**
```powershell
git clone https://github.com/homeyong/etherscan-flow.git "$env:USERPROFILE\.codex\skills\etherscan-flow"
```

Prefer to scope it to one project? Clone into `.codex/skills/etherscan-flow` in your repo instead.
</details>

<details>
<summary><b>Claude.ai — the web chat UI</b></summary>

> **Note:** "Claude.ai" here means the **web chat interface** at [claude.ai](https://claude.ai), *not* the Claude Code CLI.

1. Download this repo as a ZIP (green **Code** button → **Download ZIP**).
2. Go to **claude.ai/customize/skills** and upload it.
3. On paid plans, allowlist `api.etherscan.io` in the skill's network settings so it can reach the API.

⚠️ On the web UI you can only supply a key by **pasting it in chat** or via a **connector** — see the note below on what that means for privacy.
</details>

## Your Etherscan API key — and how private it really is

Etherscan API V2 requires a key — there is no anonymous or demo tier. A key is read-only and rate-limited, so leaking one is low-stakes, but keep it out of the chat transcript where you reasonably can. The skill picks a key source in this order, first match wins:

**inline `apikey=` → Etherscan MCP → Etherscan CLI → `ETHERSCAN_API_KEY` env var → local key file**

First match wins and the order is binding: an inline `apikey=` anywhere in your prompt **always** takes precedence — the skill must use it and must not go probing the CLI or demanding `ETHERSCAN_API_KEY` when you've already pasted a key. If none resolve, the skill stops and asks for a key. It never writes a case file without live API data.

**Where the key actually goes depends on where you run it:**

```mermaid
flowchart LR
    subgraph L["🖥️ Local agent — Claude Code / Codex CLI"]
        k1["key in env var / file /<br/>local MCP server"]:::safe -->|referenced by name in a shell command| c1["API call"]
        c1 -->|"request + results only"| ai1["AI provider"]
    end
    subgraph W["🌐 claude.ai web chat UI"]
        inl["paste apikey= in chat"]:::warn -->|"key sits in the transcript"| ai2["AI provider"]
        conn["MCP connector"]:::safe -->|"key held server-side"| ai2
    end
    classDef safe fill:#dcfce7,stroke:#16a34a,color:#065f46;
    classDef warn fill:#fee2e2,stroke:#dc2626,color:#7f1d1d;
```

| Where you run it | How you give the key | Does the key value reach the AI provider? |
|---|---|---|
| **Claude Code / Codex** (local) | env var, local file, or local MCP | **No** — a shell command references it by name; the model only sees the request and the API results |
| **Any tool** | inline `apikey=…` | **Yes** — it's in the chat. Use a throwaway free-tier key |
| **claude.ai web** | MCP / connector | **No** — the connector holds it server-side |
| **claude.ai web** | inline `apikey=…` | **Yes** — it's in the transcript |

**Be honest with yourself about the boundary:** the local paths keep the *secret key* off the wire — but they do **not** make the investigation private. The addresses, hashes, and Etherscan responses still travel through your AI provider (Anthropic / OpenAI) as normal model context, exactly like any other prompt. So the guarantee is *"your key stays on your machine,"* not *"nothing leaves your machine."* Full local privacy would require running a local model too, which is out of scope here.

Get a free key at [etherscan.io/apis](https://etherscan.io/apis).

## Usage

Paste a hash or address and ask to investigate:

```
trace this scam 0x<txhash>
follow the money from this victim wallet 0x<address>
this is the scammer address 0x<address>, find the victims
build a case for this hack 0x<address> apikey=YOUR_KEY
```

Or profile a DAO/protocol/business from a verified scope:

```
show ENS DAO as a business
show ENS DAO as a business using these treasury, controller, and timelock addresses: 0x<address> 0x<address>
map income and spending for this protocol treasury 0x<address>
show where this DAO gets income and how it spends money, with totals, apikey=YOUR_KEY 0x<address>
```

Or import a draft, notes, or any link and have every claim verified on-chain:

```
extract the flows from this gist and build the case: https://gist.github.com/<user>/<id> apikey=YOUR_KEY
someone reported this scam on X — verify it and build the case: https://x.com/<user>/status/<id>
build a case from the addresses in this article: https://<news-site>/<path>
here's my draft case JSON — validate it and produce a verified version: <pasted draft>
```

You get a JSON file. Open [Etherscan Flow](https://etherscan.io), choose **Import**, and paste it — the schema maps one-to-one, no reformatting.

## Optional: Use Etherscan CLI Instead of MCP

If MCP setup is inconvenient, install the official
[Etherscan CLI](https://github.com/etherscan/etherscan-cli) and log in once:

```bash
etherscan login
```

After that, `etherscan-flow` can use the CLI as a local read-only transport. The
API key stays in the CLI's env/config/keyring, and the skill calls commands such
as:

```bash
etherscan account txlist 0x... --chain ethereum --all --max-pages 20 --json
etherscan account tokentx 0x... --chain ethereum --all --max-pages 20 --json
etherscan proxy eth_getTransactionByHash 0x... --chain ethereum --json
```

Transport preference is:

```text
inline apikey= -> Etherscan MCP -> Etherscan CLI -> ETHERSCAN_API_KEY -> local key file
```

## Stop it asking permission for every call

A single trace makes **many** API calls (up to 100). If your agent asks you to approve each one, that's the agent's **permission system**, not the skill — every call is a read-only `GET` to one host (`api.etherscan.io`), so it's safe to allowlist once and let the whole trace run uninterrupted.

<details open>
<summary><b>Claude Code (CLI)</b></summary>

Fastest: the first time it prompts, choose **"Yes, and don't ask again for curl commands"** (or WebFetch to `api.etherscan.io`).

Or set it up ahead of time — run `/permissions` and add the rules, or add them to your **user** settings at `~/.claude/settings.json` (this is where an installed skill runs from):

```json
{
  "permissions": {
    "allow": [
      "WebFetch(domain:api.etherscan.io)",
      "Bash(curl:*)"
    ]
  }
}
```

`Bash(curl:*)` allows all `curl` invocations; the skill's Hard rule 2 already restricts it to the single Etherscan host. If you'd rather not allow `curl` globally, keep just the `WebFetch` rule and tell the agent to "use WebFetch, not curl."
</details>

<details>
<summary><b>Codex CLI</b></summary>

Enable workspace writes, outbound network access, and unattended approvals in `~/.codex/config.toml`:

```toml
approval_policy = "never"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
```

Then run the trace normally:

```bash
codex "trace this scam 0x…"
```

`workspace-write` does not enable outbound access by itself; `network_access = true` is required for the Etherscan calls. Scope this configuration to trusted use — `never` stops all approval prompts, not just Etherscan ones, and network access applies to every command in that Codex session.
</details>

<details>
<summary><b>Claude.ai (web)</b></summary>

There are no per-call prompts here; instead, on paid plans you must **allowlist `api.etherscan.io`** once in the skill's network settings (see Quick start) or the calls are blocked outright.
</details>

## If your AI's safety filter flags a trace

Fund-flow investigations legitimately mention mixers, laundering, and stolen funds — which can pattern-match a provider's cybersecurity safeguards even though the work is read-only forensics on public data. (Anthropic says its current safeguards are "intentionally broad" and may flag routine security work; other providers have equivalents.) The skill is built to make this a bump, not a wall:

- **It states its purpose up front** — read-only public-ledger forensics, no exploit tooling — and keeps investigative narrative inside the JSON instead of chat commentary, which is where false positives are most often triggered.
- **Nothing is lost on interruption.** Every API response is appended to a scratchpad fetch log as it arrives; relaunching the same trace resumes from the log instead of re-spending your API budget.
- **It will not try to evade the filter** — no rewording, no encoding tricks. If the safeguard fires, that's between you and the provider, and the honest fixes are below.

If you hit a false positive on Claude: report it via `/feedback`, and if you do security or forensics work regularly, apply to Anthropic's [Cyber Verification Program](https://support.claude.com/en/articles/14604842-real-time-cyber-safeguards-on-claude) for vetted access to security-sensitive capabilities.

## Output schema

```json
{
  "id": "case-a1b2c3d4",
  "name": "0xabcd… — approval drain traced to Binance 14",
  "schemaVersion": 1,
  "nodes": [ { "id": "victim01", "address": "0x…", "chainid": 1, "role": "victim_wallet", "hop": 0, "label": "Victim", "notes": "…" } ],
  "edges": [ { "id": "e1", "source": "victim01", "target": "atk01", "amount": "5000", "token": "USDT", "type": "token_transfer", "txhash": "0x…", "chainid": 1 } ],
  "_meta": { "chain": "ethereum", "chainid": 1, "chains": [{ "chain": "ethereum", "chainid": 1 }], "patterns": [], "gaps": [], "disclaimer": "…" }
}
```

Roles, labels, and notes are AI inference over public Etherscan data — **not** Etherscan verdicts, accusations, or legal findings.

## Optional: Connect the Etherscan MCP

`etherscan-flow` can call Etherscan directly, but an MCP connection is cleaner
because the API key can live in the MCP client config instead of the prompt. The
hosted MCP endpoint is:

```text
https://mcp.kennydev.xyz/mcp
```

It is bring-your-own-key: each user sends their own Etherscan V2 API key in the
`Authorization` header.

Codex config (`~/.codex/config.toml`):

```toml
[mcp_servers.etherscan]
url = "https://mcp.kennydev.xyz/mcp"

[mcp_servers.etherscan.headers]
Authorization = "Bearer YOUR_ETHERSCAN_API_KEY"
```

Codex CLI:

```bash
export ETHERSCAN_API_KEY=YOUR_ETHERSCAN_API_KEY
codex mcp add etherscan --url https://mcp.kennydev.xyz/mcp \
  --bearer-token-env-var ETHERSCAN_API_KEY
```

On Windows PowerShell:

```powershell
$env:ETHERSCAN_API_KEY="YOUR_ETHERSCAN_API_KEY"
codex mcp add etherscan --url https://mcp.kennydev.xyz/mcp `
  --bearer-token-env-var ETHERSCAN_API_KEY
```

Claude Code CLI:

```bash
claude mcp add --transport http etherscan https://mcp.kennydev.xyz/mcp \
  --header "Authorization: Bearer YOUR_ETHERSCAN_API_KEY"
```

Claude Desktop / Claude Code MCP JSON using `mcp-remote`:

```json
{
  "mcpServers": {
    "etherscan": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://mcp.kennydev.xyz/mcp",
        "--header",
        "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "AUTH_HEADER": "Bearer YOUR_ETHERSCAN_API_KEY"
      }
    }
  }
}
```

The no-space `Authorization:${AUTH_HEADER}` form also avoids argument escaping problems in Claude Desktop on Windows.

Quick checks:

```bash
curl -s https://mcp.kennydev.xyz/health
curl -s -X POST https://mcp.kennydev.xyz/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer YOUR_ETHERSCAN_API_KEY" \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}'
```

Replace `YOUR_ETHERSCAN_API_KEY` with your own Etherscan key. Do not paste a shared
production key into public docs, screenshots, or support messages.

## Tool coverage

| Tool | v1 |
|---|---|
| Claude Code | ✅ |
| Codex CLI | ✅ |
| Claude.ai (web) | ✅ |
| Gemini CLI, others | later — [open an issue](https://github.com/homeyong/etherscan-flow/issues) if you want one |

Coverage grows with demand — tell us what you use.

## License

[MIT](./LICENSE)
