"""Audit version-pinned official MCP schemas against MCPTox's exposed surface."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from code.run_mcp_pilot import MCPTox


UNAVAILABLE = {
    "12306-mcp": ("3ba060e8711d92494c1f5549554b0fbd7e5e746b",
                  "startup downloads live station data; upstream request fails before MCP initialization"),
    "AdFin": ("514608efcf57c680a26ce31d6280f982aec83a77",
              "tool registration downloads a live OpenAPI document whose historical JSON endpoint is no longer available"),
    "BaiduMap": ("aca9b28924112106e261786abc2dadfc1b39dda4",
                 "pinned repository contains installation documentation but no server implementation"),
    "DoDo Payments": ("7809499d1b1ab2770bf4387e35a3b4af29588e6f",
                       "monorepo source is pinned, but generated endpoint bundle requires the complete SDK build"),
    "E2B": ("1d48a3fcb3af800303c5ccafbaf4c3ea46eee5f3",
            "source is pinned but released server requires sandbox credentials/configuration before discovery"),
    "GoogleDrive": ("9be4674d1ddf8c469e6461a27a337eeb65f76c2e",
                    "server loads an OAuth credential file before MCP initialization"),
    "OP.GG": ("40bd0a79993d4ae1c309e2beeb4d948315344f3c",
              "official package is only a proxy to the remote MCP endpoint, which closed during tools/list"),
    "Redis": ("9be4674d1ddf8c469e6461a27a337eeb65f76c2e",
              "server requires a live Redis connection before MCP initialization"),
    "gNucleus Text to CAD": ("1c739b7e78415497e091ede070b2303e084b6910",
                              "pinned source is available but its legacy server closed during protocol negotiation"),
    "wechat": ("d4a05bd2208449423198e66d7edd3d298668b306",
               "server imports Windows-only wxauto and attaches to a local WeChat session before initialization"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--schemas", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--ours-clean", type=Path)
    parser.add_argument("--undefended-clean", type=Path)
    args = parser.parse_args()
    benchmark = json.loads(MCPTox.read_text(encoding="utf-8"))
    servers, trusted_tools = [], []
    for server in benchmark["servers"].values():
        name = server["server_name"]
        expected = set(map(str, server.get("tool_names") or []))
        path = args.schemas / f"{name}.json"
        if path.exists():
            snapshot = json.loads(path.read_text(encoding="utf-8"))
            by_name = {str(tool["name"]): tool for tool in snapshot["tools"]}
            present = expected & set(by_name)
            missing, extra = sorted(expected - set(by_name)), sorted(set(by_name) - expected)
            status = "complete" if not missing else "partial"
            trusted_tools.extend({"server": name, **by_name[tool]} for tool in sorted(present))
            servers.append({
                "server": name, "status": status, "source_url": snapshot["source_url"],
                "source_commit": snapshot["source_commit"], "schema_hash": snapshot["schema_hash"],
                "benchmark_tool_count": len(expected), "official_tool_count": len(by_name),
                "matched_tool_count": len(present), "missing_tools": missing, "extra_tools": extra,
            })
        else:
            commit, reason = UNAVAILABLE.get(name, (None, "not collected"))
            servers.append({
                "server": name, "status": "unavailable", "source_url": server["server_url"],
                "source_commit": commit, "benchmark_tool_count": len(expected),
                "official_tool_count": 0, "matched_tool_count": 0,
                "missing_tools": sorted(expected), "extra_tools": [], "reason": reason,
            })
    summary = {
        "server_total": len(servers),
        "server_complete": sum(row["status"] == "complete" for row in servers),
        "server_partial": sum(row["status"] == "partial" for row in servers),
        "server_unavailable": sum(row["status"] == "unavailable" for row in servers),
        "benchmark_tool_total": sum(row["benchmark_tool_count"] for row in servers),
        "official_tool_matched": sum(row["matched_tool_count"] for row in servers),
    }
    loss_coverage = None
    if bool(args.ours_clean) != bool(args.undefended_clean):
        parser.error("--ours-clean and --undefended-clean must be supplied together")
    if args.ours_clean:
        ours = json.loads(args.ours_clean.read_text(encoding="utf-8"))["clean"]
        undefended = json.loads(args.undefended_clean.read_text(encoding="utf-8"))["clean"]
        undefended_by_cell = {
            (row["server"], row["query"]): row for row in undefended if row["status"] == "ok"
        }
        trusted_names = {(tool["server"], tool["name"]) for tool in trusted_tools}
        losses = []
        for row in ours:
            peer = undefended_by_cell.get((row["server"], row["query"]))
            if row["status"] != "ok" or not peer or not peer.get("task_complete") or row.get("utility"):
                continue
            proposals = row.get("proposals") or []
            call = (proposals[0].get("call") if proposals else None) or row.get("call") or {}
            method = str(call.get("tool") or "")
            losses.append({
                "server": row["server"], "method": method, "query": row["query"],
                "official_schema_exact": (row["server"], method) in trusted_names,
            })
        loss_coverage = {
            "loss_total": len(losses),
            "official_schema_exact": sum(row["official_schema_exact"] for row in losses),
            "official_schema_missing": sum(not row["official_schema_exact"] for row in losses),
            "cells": losses,
        }
        summary["utility_loss_total"] = loss_coverage["loss_total"]
        summary["utility_loss_official_schema_exact"] = loss_coverage["official_schema_exact"]
        summary["utility_loss_official_schema_missing"] = loss_coverage["official_schema_missing"]
    result = {"cutoff": "2025-12-03T07:30:47Z", "summary": summary,
              "servers": servers, "trusted_tools": trusted_tools,
              "utility_loss_coverage": loss_coverage}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# MCPTox Official Schema Registry", "", json.dumps(summary, ensure_ascii=False), "",
             "| Server | Status | Benchmark tools | Matched official | Missing | Commit |", 
             "|---|---:|---:|---:|---:|---|"]
    for row in servers:
        lines.append(f"| {row['server']} | {row['status']} | {row['benchmark_tool_count']} | "
                     f"{row['matched_tool_count']} | {len(row['missing_tools'])} | "
                     f"{(row.get('source_commit') or 'N/A')[:12]} |")
    lines += ["", "## Unavailable or partial", ""]
    for row in servers:
        if row["status"] != "complete":
            lines.append(f"- **{row['server']}**: {row.get('reason', 'official snapshot misses: ' + ', '.join(row['missing_tools']))}")
    if loss_coverage:
        lines += ["", "## Current clean utility-loss coverage", "",
                  f"Exact official schema: **{loss_coverage['official_schema_exact']}/"
                  f"{loss_coverage['loss_total']}**; unavailable or version-mismatched: "
                  f"**{loss_coverage['official_schema_missing']}/{loss_coverage['loss_total']}**.", "",
                  "| Server | Method | Official schema exact |", "|---|---|---:|"]
        for row in loss_coverage["cells"]:
            lines.append(f"| {row['server']} | `{row['method']}` | "
                         f"{'yes' if row['official_schema_exact'] else 'no'} |")
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
