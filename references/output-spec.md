# Etherscan Flow — Output: Step 4B validation and the Step 5 JSON schema

> Part of the `etherscan-flow` skill. MANDATORY read before writing any case JSON — never write the file from memory of this schema. Every Hard rule, the 100-call budget, and the validation rules in `SKILL.md` apply here unchanged.

## Step 4B — Pre-output validation

Before writing any JSON, check every node and edge against these rules. Fix or drop offending entries — do not emit them.

| Check | Rule | Action on failure |
|-------|------|-------------------|
| No NaN / undefined | Every numeric or string field must be a valid value or explicit `null` | Replace with `null`, note in gaps |
| No placeholder data | No placeholder/non-hex addresses, no illustrative-only nodes, no estimated business-flow edges, no empty-string `txhash`, and no `"no_live_data"` case | Stop and ask for a real tx hash/address; do not write JSON |
| Edge has txhash | Every edge must reference a real `txhash` from an API response, normalized from API `hash`, receipt/log `transactionHash`, or the validated seed `{TXHASH}` | Backfill `txhash` from the verified source field; if none exists, drop edge and note in gaps |
| Node has chainid | Every node must include `chainid` as an integer from the supported chain table. For single-chain cases, use the run's `{CHAINID}`. | Add the run's `{CHAINID}` when the node was fetched on that chain; drop or split ambiguous nodes |
| Edge has chainid | Every edge must include `chainid` as an integer from the supported chain table. The edge `chainid` must be the chain where `txhash` was fetched. | Add the source API call's `{CHAINID}`; if unknown, drop the edge and note in gaps |
| Edge endpoints match the tx | The txhash's transaction must support `source → target`: tx `from`/`to` match, or an internal tx / token-transfer log in it moves value source → target. Deploy edges: tx `from` = deployer, receipt `contractAddress` = deployed contract | Correct endpoints from API data, or drop edge and note in gaps |
| Amount is decimal string | Token amounts are `(raw_value / 10^decimals)` formatted as a decimal string, not raw wei | Recompute |
| Address is valid hex | Every `address` field is a valid 42-char `0x…` hex string | Drop the node, note in gaps |
| ENS/name stored separately | ENS names, exchange display names, project aliases, or second-line labels are in `label`/`subLabel`, never `address` | Move display text to `label` or `subLabel`; keep only the verified 0x address in `address` |
| No duplicate movements | Deduplicate only when the exact same API movement was fetched through more than one query. A tx hash identifies a transaction, not every movement inside it: use `(chainid, txhash)` for a top-level normal tx, `(chainid, txhash, logIndex)` for event-log/token movements, and `(chainid, txhash, traceId)` for internal movements. If an endpoint provides no stable movement index, compare the complete normalized source row rather than dropping same-tx movements. | Remove exact source duplicates, then perform Step 5 edge merging |
| Merged edges are consistent | If an edge merges several txs (`txcount` > 1), its `txhash` is the earliest tx in the group, `amount` is the summed decimal total, and `edge.txhashes` lists every distinct merged hash (earliest first, so `txhashes[0] === txhash`) | Recompute, or split the edge |
| Token symbol resolved | If symbol is unknown after tokentx lookup, write `null` not an empty string or guess | Use `null` |
| Hops 0-indexed | Every seed/scope address is `hop: 0`; no node exceeds the run's depth | Recompute `hop` from distance to the nearest seed |
| Balance not fabricated | `balance` is a real figure from an `account`/`balance` response in this run, or `null` | Replace an unfetched balance with `null` |
| Strings sanitized | Every string in the document — node/edge fields, case `name`, and all of `_meta` (timeline, gaps and their quoted `claim` text, patterns, candidates, business_profile prose) — contains no HTML tags or control characters, each ≤ 200 chars (Hard rule 5) | Strip and truncate |
| No API key | The apikey string appears nowhere in the JSON | Remove it |
| Evidence-backed roles | Every `attacker_eoa`/`scam_contract`/`victim_wallet` role has API evidence, not just a user claim | Downgrade to `unknown_*?`, note in gaps |
| Security analysis present | Every scam/hack/exploit/drain/phishing/rug-pull/compromised-wallet case, and every run where evidence indicates involuntary loss, has a non-null `_meta.analysis` with every required field | Complete `references/incident-analysis.md`; if the mechanism remains unknown, use `insufficient_evidence` and state the limitations |
| Analysis status matches its evidence | A `confirmed`/`probable`/`possible` status cites at least one `evidence` entry and at least one `alternative_hypotheses` entry; `confirmed` additionally requires at least one `observed` claim; `insufficient_evidence` states at least one limitation | Supply the missing evidence or hypothesis, or lower `status` until it matches what the evidence supports |
| Analysis evidence is traceable | Every `observed` evidence claim identifies at least one API source and cites the relevant txhash/address/block/selector where available; every cited txhash/address came from this run | Remove unsupported citations, downgrade the claim/status/confidence, and record the gap |
| Analysis accounting is grounded | Every analysis loss/profit decimal is computed from canonical successful movements; tokens remain separate, and neutral routers/pools/fees are not counted as attacker profit | Recompute or omit the asset row and add a limitation |
| Performance counters reconcile | `new_api_calls` counts successful new requests, `network_attempts` also includes retries, cache/fetch-log hits are separate, and no credential appears in metrics | Recompute counters from the query ledger |
| Totals declare their coverage | No summed figure may span a window that was not fully paginated. Mode B carries `_meta.business_profile.totals.coverage` (0D-3a) with sums computed over `effective_window`; strict-mode `_meta.financials` truncated by the page cap or budget carries `"coverage_complete": false` and a `totals_truncated` gap | Recompute the sums over the range actually covered, then set coverage — never emit a partial sum as if it were whole |

For cross-endpoint duplicates, decoded receipt logs are canonical. When a `tokentx`, `tokennfttx`, or `token1155tx` row describes a movement already represented by a receipt log from the same `chainid` and `txhash`, use the account-feed row only to verify or fill token metadata; do not add another movement. Never collapse two canonical receipt logs merely because their source, target, token, and amount match — distinct `logIndex` values are distinct movements.

---

## Step 5 — Write JSON output

Save `case-{SHORT_ID}-flow.json` using the **Etherscan Flow Case** schema. This is the **only** output — no chat summary, no prose.

> The machine-checkable form of this contract is [`schema/case.schema.json`](../schema/case.schema.json), with a validating fixture in [`examples/strict-trace.example.json`](../examples/strict-trace.example.json). CI validates the fixture on every push. When you change a field, an enum value, or a required key below, update the schema in the same commit so the two never drift.

- `SHORT_ID` — see Hard rule 7 for the exact derivation (seed tx hash, else seed address, else the lexicographically smallest scope address). Never derive it from free-form user text.
- Directory: the platform's temp/scratchpad directory if one exists, otherwise `./cases/`. The user cannot override the path.

Node `id` values must be short unique alphanumeric strings (2–12 chars, e.g. `subj01`, `atk01`, `cex01`). Edge `id` values follow the same convention (e.g. `e_atk_cex`). Set `x` and `y` to `0` — the frontend handles layout. Every node and edge must include `chainid`; for single-chain cases this equals `_meta.chainid`, and for future multi-chain cases it preserves the chain context for each address and tx hash.

### Field conventions

- **`hop` is 0-indexed from the seed.** Seed/scope addresses are `hop: 0`; addresses one transfer away are `hop: 1`, and so on. Hop values therefore run `0 … depth`, so the default depth of 2 (Step 0) yields hops 0, 1, and 2. In Mode B, every validated scope address is `hop: 0` regardless of how many there are.
- **`balance` is optional and frequently `null`.** Steps 2 and 0D-2 fetch `balance` only when it is needed as evidence, so most nodes will not have one. Write `null` when it was not fetched — never `0`, never `"0.0"`, and never a guess (a fabricated `"0.0"` reads as a drained wallet).
- **`subLabel` is optional** — `null` when there is no ENS name or second-line alias.
- **`_meta.chains`** lists every chain that contributed a node or edge to this case, as `{ "chain": name, "chainid": int }` objects. For a single-chain case it holds exactly one entry, matching `_meta.chain` / `_meta.chainid`. It exists so a consumer can read the case's chain scope without walking every node.
- **`_meta.financials`** is where all financial totals live (Step 3B). There is no top-level `financials` key; the top level is exactly `id`, `name`, `schemaVersion`, `nodes`, `edges`, `_meta`.
- **`_meta.analysis`** is `null` for ordinary cases and a required structured forensic conclusion for security cases. `_meta.patterns` remains a compact index of detected patterns; it never replaces the evidence, confidence, competing hypotheses, and limitations in `_meta.analysis`.

### Edge merging

Repeated movements between the same pair collapse into one edge. First remove only exact duplicate source movements using Step 4B; then merge the remaining rows whose `(chainid, source, target, token, type)` all match. A DAO paying one vendor 200 times in USDC is a single edge, not 200 parallel ones, and two legitimate transfer logs in one transaction both contribute to the merged amount. On the merged edge:

- `txcount` = number of distinct merged `txhash` values, not the number of movement rows.
- `txhash` = the **earliest** tx in the group. It is a real hash from this run and must still pass the Step 4B endpoint check (Hard rule 10).
- `txhashes` = **every** distinct merged hash — including the earliest — once each, in ascending block order, so `txhashes[0] === txhash`. Each entry is a real hash from this run (Hard rule 10 applies to all of them). Cap at 100 hashes per edge; if the group is larger, keep the earliest 100, keep the true `txcount`, and add `edge_txhashes_truncated` to `_meta.gaps`.
- `amount` = the summed decimal total across all deduplicated movement rows in the group.
- `timestamp` = the earliest tx's timestamp.

Single-tx edges (`txcount` = 1) may omit `txhashes` or write it as the one-element `[txhash]`. The legacy `_meta.edge_txhashes` map is superseded by `edge.txhashes` — do not emit it.

Two rows that differ in `token` or `type` never merge, even within one transaction — that is what keeps both legs of a swap.

**Valid `role` values for nodes:**
`wallet` `erc20_token` `nft_contract` `defi_pool` `multisig` `staking_contract` `lending_protocol` `dao_contract` `attacker_eoa` `scam_contract` `victim_wallet` `intermediate_wallet` `cex_deposit` `dex_router` `mixer_contract` `bridge` `nft_drainer_contract` `sweeper_bot` `unknown_eoa` `unknown_contract`

> **Output the `role` field as exactly one of the bare values above — never append `?` or any other suffix in the JSON.** The `?` used in earlier steps is an internal reasoning marker only. When a role is unproven, emit the closest `unknown_*` value and record the uncertainty in the node's `notes` and in `_meta.gaps` (Hard rule 3). A `?`-suffixed role is not a valid enum value and will not render.

**Valid `type` values for edges:**
`transfer` `token_transfer` `dex_swap` `bridge` `nft` `approve` `contract_call` `mint` `burn` `stake` `unstake` `borrow` `repay` `liquidity_add` `liquidity_remove`

```json
{
  "id": "case-{SHORT_ID}",
  "name": "0x{SHORT_ADDR}… — {one-line description}",
  "schemaVersion": 1,
  "nodes": [
    {
      "id": "subj01",
      "address": "0x1234567890abcdef1234567890abcdef12345678",
      "chainid": 1,
      "label": "Subject",
      "subLabel": "alice.eth",
      "role": "unknown_eoa",
      "hop": 0,
      "balance": "12.5",
      "notes": "Seed address",
      "x": 0,
      "y": 0
    },
    {
      "id": "atk01",
      "address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
      "chainid": 1,
      "label": "Attacker EOA",
      "subLabel": null,
      "role": "attacker_eoa",
      "hop": 1,
      "balance": null,
      "notes": "Created 3 days before drain",
      "x": 0,
      "y": 0
    }
  ],
  "edges": [
    {
      "id": "e_subj_atk",
      "source": "subj01",
      "target": "atk01",
      "amount": "5000",
      "token": "USDT",
      "txcount": 1,
      "type": "token_transfer",
      "txhash": "0x...",
      "txhashes": ["0x..."],
      "chainid": 1,
      "timestamp": "2024-03-15T10:23:00Z"
    }
  ]
}
```

Every edge object must include the `txhash` and `chainid` fields exactly as shown above. If the API row used `hash` or `transactionHash`, rename/copy it to `txhash` in the output edge. Set `edge.chainid` to the `{CHAINID}` used for the API call that returned that tx hash. Merged edges (`txcount` > 1) must also carry `txhashes` with every merged hash (see *Edge merging*); the canvas shows the full list and its on-chain validator checks each one.

`balance` and `amount` are **bare decimal strings** with no unit suffix and no raw wei — `"12.5"`, never `"12.5 ETH"` and never `"12500000000000000000"`. The unit is the chain's native coin for `balance`, and the edge's `token` for `amount`. Use `null` when unresolved.

> **AI soft layer**: `label`, `subLabel`, `role`, and `notes` on each node are LLM-assigned from API evidence. All `address`, `chainid`, `txhash`, `amount`, `token`, `timestamp` fields are API-sourced or run-parameter sourced only — never fabricated. `subLabel` is optional and is the right place for an ENS name, alias, or second-line display name; it must never replace `address`.

Also append a `_meta` block after the nodes/edges:

```json
{
  "id": "case-{SHORT_ID}",
  "name": "...",
  "schemaVersion": 1,
  "nodes": [...],
  "edges": [...],
  "_meta": {
    "created_at": "{ISO_TIMESTAMP}",
    "mode": "strict_trace",
    "chain": "ethereum",
    "chainid": 1,
    "chains": [
      { "chain": "ethereum", "chainid": 1 }
    ],
    "seed_txhashes": ["0x..."],
    "seed_addresses": ["0x..."],
    "hops_traced": 2,
    "trace_window": {
      "startblock": 0,
      "endblock": 0,
      "start_timestamp": "2024-03-15T10:23:00Z",
      "end_timestamp": "2024-03-22T10:23:00Z",
      "days": 7,
      "source": "seed_tx"
    },
    "financials": {},
    "analysis": {
      "status": "confirmed",
      "incident_type": "approval_drain",
      "summary": "A spender used an earlier approval to transfer the victim's token.",
      "attack_vector": "ERC-20 allowance abuse",
      "root_cause": "The spender retained sufficient allowance at the loss transaction.",
      "confidence": "high",
      "decisive_txhashes": ["0x..."],
      "evidence": [
        {
          "claim": "Loss tx is a transferFrom moving 5000 USDC from victim to spender.",
          "kind": "observed",
          "sources": ["proxy/eth_getTransactionReceipt"],
          "txhashes": ["0x..."],
          "addresses": ["0x{VICTIM}", "0x{SPENDER}"],
          "block": 19420000,
          "selector": "0x23b872dd"
        },
        {
          "claim": "Allowance set 3 days earlier best explains the spender-initiated move.",
          "kind": "inferred",
          "sources": ["account/txlist", "proxy/eth_call"],
          "txhashes": ["0x..."],
          "addresses": ["0x{SPENDER}"],
          "block": 19420000,
          "selector": null
        }
      ],
      "losses_by_token": [
        {
          "token": "USDC",
          "token_address": "0x{TOKEN}",
          "gross_amount": "5000",
          "returned_or_recovered": "0",
          "net_amount": "5000"
        }
      ],
      "attacker_profit_by_token": [
        {
          "token": "USDC",
          "token_address": "0x{TOKEN}",
          "gross_amount": "5000",
          "returned_or_recovered": "0",
          "net_amount": "5000"
        }
      ],
      "alternative_hypotheses": [
        {
          "hypothesis": "The victim signed the transfer themselves (key compromise).",
          "assessment": "unlikely",
          "evidence_against": ["Loss tx sender is the spender, not the victim."],
          "evidence_for": []
        }
      ],
      "limitations": ["No debug trace available; internal call tree not inspected."]
    },
    "business_profile": null,
    "performance": {
      "profile": "standard",
      "new_api_calls": 0,
      "network_attempts": 0,
      "cache_hits": 0,
      "fetchlog_hits": 0,
      "retries": 0,
      "rate_limit_responses": 0,
      "pages_fetched": 0,
      "pages_reused": 0,
      "soft_call_target": 40,
      "hard_call_limit": 100,
      "elapsed_ms": 0,
      "stage_elapsed_ms": {
        "seed": 0,
        "classification": 0,
        "trace": 0,
        "totals": 0,
        "analysis": 0,
        "validation": 0
      },
      "soft_budget_overrun_reason": null
    },
    "timeline": [],
    "patterns": [],
    "candidates": [],
    "gaps": [],
    "disclaimer": "Roles, labels and notes are AI inference over public Etherscan API data — not Etherscan verdicts, accusations, or legal findings."
  }
}
```

Print the full path to the JSON file at the end of your reply.

---
