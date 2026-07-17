# Etherscan Flow — Transports: MCP, CLI, and env-key details

> Part of the `etherscan-flow` skill. Read this when the run resolved to the MCP or CLI transport (credentials steps 2–3), or when checking `ETHERSCAN_API_KEY` (credentials step 4). Every Hard rule, the 100-call budget, and the validation rules in `SKILL.md` apply here unchanged.

Initialize the canonical query ledger and adaptive rate controller from `performance.md` before issuing transport calls. No transport may hard-code a global requests-per-second value: the effective limit belongs to the user's key/plan, endpoint, and transport.

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
- `nametag getaddresstag` accepts a **comma-separated address list**. Batch the surviving Step 2 entity set into as few calls as the endpoint accepts rather than calling once per address. If the transport reports a payload/address limit, split to that limit and cache each batch.
- **Pagination.** `--all` auto-paginates and returns only when it has fetched every page (capped by `--max-pages`, hidden flag, default `20`). It therefore cannot stop early. Use it only for **Step 3B** totals, where you want the whole window. For **Step 3** hop tracing, loop `--page {N} --offset 100` yourself so you can stop the moment you hit a CEX/mixer/bridge landmark or the per-address 20-page cap. Each `--all` invocation silently spends up to 20 calls of the 100-call run budget — count them.
- **Round trips.** When the harness supports grouped/parallel calls, send only independent requests in the current evidence wave together. Otherwise prefer a transport-native batch/subprocess that returns the wave in one tool call and writes fetch-log rows itself. Never batch dependent waves or expose the API key in argv/logs.
- **Rate ownership.** MCP/CLI may throttle internally. Use its reported limit/retry signal, do not add a fixed sleep, and reduce the next wave after a rate-limit response. If no signal exists, use the adaptive probing in `performance.md`.

If the CLI command fails because it is not installed, not logged in, or lacks a required endpoint, fall through to the next key source. If it fails because the API returns an error, record that API error in `_meta.gaps` and continue where possible.

**Separate the two failure modes — they are different facts and they are not each other's evidence.**

| What happened | How to tell | What to record |
|---------------|-------------|----------------|
| The API answered "no" | The command ran and returned an error body: plan-gated (`API Exclusive endpoint`), `NOTOK`, rate limit, bad params | A blocked gap quoting that body verbatim, with the `endpoint` (`references/output-spec.md` → *`_meta.gaps` entries*). Do not fall through — the key is fine, this endpoint is not for it |
| The transport did not answer | Non-zero exit with no API body, binary missing, timeout, no key resolved | Fall through to the next key source. Only if every source fails is it a blocked gap, quoting the transport's own error |

`nametag/getaddresstag` is **Pro Plus** and returns `Sorry, it looks like you are trying to access an API Exclusive endpoint` on keys without it. This is expected and benign: it means no curated Etherscan labels are available for this run, so every label must come from observed behaviour (Hard rule 3 applies unchanged). It is a plan fact about one endpoint — it is **not** evidence that the transport is broken, and it says nothing about any other endpoint's availability.

In particular, `contract/getsourcecode` carries no plan gate on a standard key and is the single highest-value classification call in a security case: verified source is what separates "the guard was missing" from "the guard passed because the attacker had become the authorized caller" — opposite root causes that produce identical logs. Never report source as unavailable without having called it and received an error to quote. Falling back to bytecode when the source was there for the asking produces a confidently-hedged wrong answer, which is worse than a slow right one.

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
