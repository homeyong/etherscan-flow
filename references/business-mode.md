# Etherscan Flow — Business/entity profile mode: Step 0D

> Part of the `etherscan-flow` skill. Read this when Mode B was selected (a DAO / protocol / project / company asked about as a business). ENS resolution is in `references/ens-resolution.md`; Steps 1–4 are in `references/trace-steps.md`. Every Hard rule, the 100-call budget, and the validation rules in `SKILL.md` apply here unchanged.

## Mode B output requirements

Business/entity profile mode must produce:

- A `_meta.business_profile` object with `entity_name`, `scope_addresses`, `income_categories`, `spending_categories`, `totals`, `plain_english_summary`, and `confidence_notes`.
- Nodes for the verified entity addresses and major counterparties.
- Edges only for real transfers, token transfers, internal transfers, or contract calls with a real `txhash`.
- Totals only from paginated API rows fetched in this run, with timeframe and budget limits stated in `_meta.gaps`.

## Step 0D — Business/entity profile mode

Use this when the user wants to understand a DAO/protocol/project as a business: where money comes from, how much came in, where money goes, and how much was spent.

### 0D-1. Resolve the entity scope

Build a candidate address list in this order:

1. **Prompt addresses.** Extract every valid `0x...` address from the user prompt.
2. **Prompt ENS names.** If the prompt contains ENS names, resolve them through Step 0E. Never put the ENS name in an `address` field.
3. **Known entity scope table.** If the entity name exactly matches an entry in the maintained table below, add those candidate addresses.
4. **No candidates.** If the list is empty, stop and ask once: "Which treasury, timelock, controller, registrar, multisig, or revenue addresses should I include for this entity?"

Every candidate is still only a hypothesis until validated by API data in this run.

### 0D-2. Validate candidate addresses

For each candidate address, call:

```
GET https://api.etherscan.io/v2/api?chainid={CHAINID}&module=proxy&action=eth_getCode&address={ADDRESS}&apikey={APIKEY}
GET https://api.etherscan.io/v2/api?chainid={CHAINID}&module=account&action=balance&address={ADDRESS}&tag=latest&apikey={APIKEY}
GET https://api.etherscan.io/v2/api?chainid={CHAINID}&module=account&action=txlist&address={ADDRESS}&startblock=0&endblock=99999999&page=1&offset=25&sort=desc&apikey={APIKEY}
GET https://api.etherscan.io/v2/api?chainid={CHAINID}&module=account&action=tokentx&address={ADDRESS}&page=1&offset=25&sort=desc&apikey={APIKEY}
```

For contracts, also call:

```
GET https://api.etherscan.io/v2/api?chainid={CHAINID}&module=contract&action=getsourcecode&address={ADDRESS}&apikey={APIKEY}
```

Optionally call nametag if available under Step 2 rules. Include a candidate in the final scope only if at least one API response confirms the address exists or has transaction/balance/code evidence. If a known table label is not supported by sourcecode/nametag/transaction behavior, keep the address but mark the label as a hypothesis in `notes` and `_meta.business_profile.confidence_notes`.

### 0D-3. Choose the business window

If the user gives a date range, use its start and end timestamps as `{WINDOW_START_TIMESTAMP}` / `{WINDOW_END_TIMESTAMP}`. Otherwise inspect the validated scope addresses' recent transaction rows, take the latest confirmed activity timestamp as `{WINDOW_END_TIMESTAMP}`, and set `{WINDOW_START_TIMESTAMP}` to 7 days earlier. If no scope address has a transaction or transfer row, no edge can survive Step 4B: stop without writing a case.

Step 3 converts these timestamps to block numbers once for the run. State the effective block/time window in both `_meta.trace_window` and `_meta.business_profile.timeframe`; add `timeframe_limited` to `_meta.gaps` whenever the selected window does not cover the entity's full history.

### 0D-4. Classify income and spending

For each validated scope address, paginate normal and token transfers using the Step 3 pagination rules, bounded by the chosen business window and the call budget. Classify rows:

| Direction | Category | Rule |
|-----------|----------|------|
| Inbound | `user_revenue` | Many inbound payments from diverse wallets into a controller/revenue contract, or ETH/token value accompanying user-facing contract calls |
| Inbound | `treasury_funding` | Inbound transfer to a treasury, multisig, timelock, or DAO contract |
| Inbound | `unknown_income` | Money came in, but API evidence does not support a business purpose |
| Outbound | `treasury_spending` | Outbound transfer from treasury/multisig/timelock |
| Outbound | `grant_or_contributor_payment` | Repeated outbound payments to wallets/contracts that look like program or contributor payments; mark uncertain unless labels support it |
| Outbound | `vendor_or_service_payment` | Outbound payments to named vendor/service addresses from nametag/sourcecode evidence |
| Outbound | `market_or_treasury_management` | DEX, bridge, CEX, liquidity, custody, or treasury-management movements |
| Outbound | `unknown_spending` | Money went out, but API evidence does not support a business purpose |

### 0D-5. Summarize business profile inside JSON

Populate `_meta.business_profile`:

```json
{
  "entity_name": "ENS DAO",
  "mode": "business_entity_profile",
  "timeframe": "API-derived range or user-requested range",
  "scope_addresses": [
    {
      "address": "0x...",
      "chainid": 1,
      "label": "Treasury / registrar / controller / timelock",
      "evidence": "sourcecode, nametag, balance, txlist, tokentx, or known table validated by API",
      "confidence": "high|medium|low"
    }
  ],
  "income_categories": [],
  "spending_categories": [],
  "totals": {
    "inbound_by_token": {},
    "outbound_by_token": {},
    "net_by_token": {}
  },
  "plain_english_summary": [],
  "confidence_notes": []
}
```

Then continue to Step 2, Step 3, Step 4, Step 4B, and Step 5 with the validated scope addresses as seeds. Do not use scam-specific labels unless the API evidence supports them.

### Maintained known entity scopes

This table is optional and conservative. Entries are candidate scopes, not final truth. Each address must still be validated through Etherscan API calls in this run before it appears in the JSON. Match entity names case-insensitively against the entity key and its aliases.

| Entity key | Aliases | Chain | Candidate scope |
|------------|---------|-------|-----------------|
| `ENS DAO` | `ENS`, `Ethereum Name Service`, `ensdao.eth` | Ethereum mainnet (chainid 1) | See ENS DAO candidate list below |

**ENS DAO candidates (chainid 1).** Every address below is a hypothesis until Step 0D-2 validates it in this run. Step 2's `nametag` (when available) is authoritative: if it disagrees with the expected identity, trust the nametag; if validation fails outright, drop the candidate and add `scope_candidate_failed` to `_meta.gaps`. Never present a table label as verified in the output — confidence comes from this run's API evidence only.

| Candidate address | Expected identity | Business relevance |
|-------------------|-------------------|--------------------|
| `0xFe89cc7aBB2C4183683ab71653C4cdc9B02D44b7` | ENS: DAO Wallet — treasury timelock (contract) | Treasury funding and spending |
| `0x253553366Da8546fC250F225fe3d25d0C782303b` | ETHRegistrarController (2023+) (contract) | User revenue — .eth registrations/renewals |
| `0x283Af0B28c62C092C9727F1Ee09c02CA627EB7F5` | ENS: Legacy ETH Registrar Controller (contract) | Historical user revenue (pre-2023) |
| `0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85` | ENS: Base Registrar — .eth NFT (contract) | Registry infrastructure |
| `0xC18360217D8F7Ab5e7c516566761Ea12Ce7F9D72` | ENS: Token — $ENS (contract) | Governance token flows |
| `0x323A76393544d5ecca80cd6ef2A560C6a395b7E3` | ENS: Governor (contract) | Proposal execution |
| `0x690F0581eCecCf8389c223170778cD9D029606F2` | ENS: Cold Wallet (verify via nametag before labeling) | Treasury reserves |

When adding a new entity to this table, follow the same discipline as the landmark table: prefer addresses confirmed by a `nametag` hit or the entity's own published documentation, record the expected identity so Step 0D-2 has something concrete to check, and never add a row you could not defend if the label were wrong.

---
