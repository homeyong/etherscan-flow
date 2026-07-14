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
| Strings sanitized | Every string in the document — node/edge fields, case `name`, and all of `_meta` (timeline, gaps and their quoted `claim` text, patterns, candidates, business_profile prose) — contains no HTML tags or control characters, each ≤ 200 chars (Hard rule 5) | Strip and truncate |
| No API key | The apikey string appears nowhere in the JSON | Remove it |
| Evidence-backed roles | Every `attacker_eoa`/`scam_contract`/`victim_wallet` role has API evidence, not just a user claim | Downgrade to `unknown_*?`, note in gaps |

For cross-endpoint duplicates, decoded receipt logs are canonical. When a `tokentx`, `tokennfttx`, or `token1155tx` row describes a movement already represented by a receipt log from the same `chainid` and `txhash`, use the account-feed row only to verify or fill token metadata; do not add another movement. Never collapse two canonical receipt logs merely because their source, target, token, and amount match — distinct `logIndex` values are distinct movements.

---

## Step 5 — Write JSON output

Save `case-{SHORT_ID}-flow.json` using the **Etherscan Flow Case** schema. This is the **only** output — no chat summary, no prose.

- `SHORT_ID` — see Hard rule 7 for the exact derivation (seed tx hash, else seed address, else the lexicographically smallest scope address). Never derive it from free-form user text.
- Directory: the platform's temp/scratchpad directory if one exists, otherwise `./cases/`. The user cannot override the path.

Node `id` values must be short unique alphanumeric strings (6–10 chars, e.g. `subj01`, `atk01`, `cex01`). Edge `id` values follow the same convention (e.g. `e_atk_cex`). Set `x` and `y` to `0` — the frontend handles layout. Every node and edge must include `chainid`; for single-chain cases this equals `_meta.chainid`, and for future multi-chain cases it preserves the chain context for each address and tx hash.

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
      "hop": 1,
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
      "hop": 2,
      "balance": "0.0",
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
    "business_profile": null,
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
