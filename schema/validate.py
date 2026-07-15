#!/usr/bin/env python3
"""Validate every examples/*.example.json against schema/case.schema.json.

Checks JSON Schema conformance plus the cross-field invariants the schema
cannot express (txhashes[0] == txhash, txcount == len(txhashes), edge
endpoints reference real node ids). Exit 0 on success, 1 on any failure.
Run locally or in CI: `python schema/validate.py`.
"""
import glob
import json
import os
import sys

from jsonschema import Draft202012Validator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_PATH = os.path.join(ROOT, "schema", "case.schema.json")


def invariants(case):
    """Return a list of invariant violations the schema can't catch."""
    problems = []
    node_ids = {n["id"] for n in case.get("nodes", [])}
    for e in case.get("edges", []):
        eid = e.get("id", "?")
        if e.get("source") not in node_ids:
            problems.append(f"edge {eid}: source '{e.get('source')}' is not a node id")
        if e.get("target") not in node_ids:
            problems.append(f"edge {eid}: target '{e.get('target')}' is not a node id")
        hashes = e.get("txhashes")
        if hashes:
            if hashes[0] != e.get("txhash"):
                problems.append(f"edge {eid}: txhashes[0] must equal txhash")
            if e.get("txcount") != len(hashes):
                problems.append(
                    f"edge {eid}: txcount ({e.get('txcount')}) != len(txhashes) ({len(hashes)})"
                )
    return problems


def main():
    schema = json.load(open(SCHEMA_PATH, encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    files = sorted(glob.glob(os.path.join(ROOT, "examples", "*.example.json")))
    if not files:
        print("no examples/*.example.json found", file=sys.stderr)
        return 1

    failed = False
    for path in files:
        rel = os.path.relpath(path, ROOT)
        case = json.load(open(path, encoding="utf-8"))
        errors = sorted(validator.iter_errors(case), key=lambda e: list(e.path))
        problems = [f"{list(e.path)}: {e.message}" for e in errors] + invariants(case)
        if problems:
            failed = True
            print(f"FAIL {rel}")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"ok   {rel}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
