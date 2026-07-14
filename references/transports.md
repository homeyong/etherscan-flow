# Etherscan Flow — Transports: MCP, CLI, and env-key details

> Part of the `etherscan-flow` skill. Read this when the run resolved to the MCP or CLI transport (credentials steps 2–3), or when checking `ETHERSCAN_API_KEY` (credentials step 4). Every Hard rule, the 100-call budget, and the validation rules in `SKILL.md` apply here unchanged.

## Transport call mapping

> **MCP transport:** if you resolved to the Etherscan MCP server (credentials step 2), ignore the raw HTTP URLs in Steps 1–4. For each `module={M}&action={A}` call below, invoke the Etherscan MCP tool that performs the same operation (matching module/action — e.g. `account`/`txlist`, `account`/`tokentx`, `account`/`txlistinternal`, `proxy`/`eth_getTransactionByHash`, `proxy`/`eth_getTransactionReceipt`, `nametag`/`getaddresstag`, `contract`/`getsourcecode`), passing the same `chainid`, `address`/`txhash`, and pagination parameters. Do not pass a key — the MCP server supplies it. Every data-integrity, budget (Hard rule 8), and validation rule applies identically on all transports.

> **CLI transport:** if you resolved to the official `etherscan` CLI (credentials step 3), ignore the raw HTTP URLs in Steps 1–4 and call the equivalent read-only CLI command with `--json`, `--chain {CHAIN_NAME_OR_ID}`, and pagination flags where applicable. The CLI owns API-key storage through `etherscan login`, `ETHERSCAN_API_KEY`, or its config/keyring. Do not pass `--api-key`: it places the key in `argv`, where it is visible to process listings and shell history (Hard rule 6). If the user gave `apikey=` for this run, set `ETHERSCAN_API_KEY` for that single invocation instead. Every data-integrity, budget (Hard rule 8), and validation rule applies identically on all transports.

## CLI transport — command table and behaviour (credentials step 3)

Map API calls to CLI commands:

| API call | CLI command shape |
|----------|-------------------|
| `account` / `balance` | `etherscan account balance {ADDRESS} --chain {CHAIN} --json` |
| `account` / `txlist` | `etherscan account txlist {ADDRESS} --chain {CHAIN} --page {N} --offset 100 --sort {asc\|desc} --json` |
| `account` / `tokentx` | `etherscan account tokentx {ADDRESS} --chain {CHAIN} --page {N} --offset 100 --sort {asc\|desc} --json` |
| `account` / `tokennfttx` | `etherscan account tokennfttx {ADDRESS} --chain {CHAIN} --page {N} --offset 20 --sort desc --json` |
| `account` / `token1155tx` | `etherscan account token1155tx {ADDRESS} --chain {CHAIN} --page {N} --offset 20 --sort desc --json` |
| `account` / `txlistinternal` by address | `etherscan account txlistinternal --address {ADDRESS} --chain {CHAIN} --page {N} --offset 100 --json` |
| `account` / `txlistinternal` by txhash | `etherscan account txlistinternal --txhash {TXHASH} --chain {CHAIN} --json` |
| `proxy` / `eth_getTransactionByHash` | `etherscan proxy eth_getTransactionByHash {TXHASH} --chain {CHAIN} --json` |
| `proxy` / `eth_getTransactionReceipt` | `etherscan proxy eth_getTransactionReceipt {TXHASH} --chain {CHAIN} --json` |
| `proxy` / `eth_getCode` | `etherscan proxy eth_getCode {ADDRESS} --chain {CHAIN} --json` |
| `proxy` / `eth_getBlockByNumber` | `etherscan proxy eth_getBlockByNumber --tag {HEX_BLOCK} --boolean false --chain {CHAIN} --json` |
| `proxy` / `eth_call` | `etherscan proxy eth_call --to {ADDRESS} --data {CALLDATA} --tag latest --chain {CHAIN} --json` |
| `contract` / `getsourcecode` | `etherscan contract getsourcecode {ADDRESS} --chain {CHAIN} --json` |
| `nametag` / `getaddresstag` | `etherscan nametag getaddresstag {ADDR1,ADDR2,…} --chain {CHAIN} --json` |

**`chainlist` on non-HTTP transports.** The chain-support check in *Chain resolution* (`GET https://api.etherscan.io/v2/chainlist`) is a plain keyless GET to the one allowed host. If the MCP server or CLI exposes an equivalent (e.g. a supported-chains tool or `etherscan chainlist`), use it; otherwise issue this one HTTP GET directly even on the MCP/CLI transport — it carries no key, so no credential handling is involved, and it still counts against the 100-call budget.

Notes on CLI behaviour that the skill depends on:

- `--boolean false` is **required** on `eth_getBlockByNumber`; omitting it returns `json-rpc error -32700: parse error`.
- `nametag getaddresstag` accepts a **comma-separated address list**. Batch the Step 2 entity set into as few calls as the rate limit allows rather than calling once per address — the run budget is 100 calls (Hard rule 8).
- **Pagination.** `--all` auto-paginates and returns only when it has fetched every page (capped by `--max-pages`, hidden flag, default `20`). It therefore cannot stop early. Use it only for **Step 3B** totals, where you want the whole window. For **Step 3** hop tracing, loop `--page {N} --offset 100` yourself so you can stop the moment you hit a CEX/mixer/bridge landmark or the per-address 20-page cap. Each `--all` invocation silently spends up to 20 calls of the 100-call run budget — count them.

If the CLI command fails because it is not installed, not logged in, or lacks a required endpoint, fall through to the next key source. If it fails because the API returns an error, record that API error in `_meta.gaps` and continue where possible.

## `ETHERSCAN_API_KEY` — per-shell check and reference syntax (credentials step 4)

**POSIX shells (bash/zsh — macOS, Linux):**
```bash
test -n "$ETHERSCAN_API_KEY" && echo SET || echo UNSET
```
If SET, reference it **by name** in every request (`…&apikey=$ETHERSCAN_API_KEY`) so the shell expands it at execution.

**PowerShell (Windows, or pwsh anywhere):**
```powershell
if ($env:ETHERSCAN_API_KEY) { 'SET' } else { 'UNSET' }
```
If SET, reference it by name as `$env:ETHERSCAN_API_KEY` — e.g. build the URL with `"...&apikey=$env:ETHERSCAN_API_KEY"` so PowerShell expands it at execution.

**Windows cmd.exe:** `if defined ETHERSCAN_API_KEY (echo SET) else (echo UNSET)`; reference as `%ETHERSCAN_API_KEY%`.

In every case the variable is expanded **by the shell at call time** so the literal key never enters your context or the transcript. Never `echo`, `printenv`, `Write-Host $env:ETHERSCAN_API_KEY`, or otherwise print its value. Picking the wrong shell's syntax (e.g. `test -n` in PowerShell) silently reports UNSET and wrongly abandons a key that was there all along — match the shell.
