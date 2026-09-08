"""Main-experiment bar charts (BU / AU / ASR) from Discussion.md Thread #9.

Three figures, each following the same row-by-benchmark layout:
  * ``main_bars_tool``  -- Tool surface (AgentDojo, ASB-OPI).
  * ``main_bars_mcp`` -- MCP surface (MCPTox, MSB).
  * ``main_bars_skill`` -- Skill surface (SkillInject, SCR).
Each benchmark cluster shows one bar per defense that reports that metric.
Muted (Morandi) palette, shared per-figure legend, two-column paper width.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

# Times-New-Roman-like serif.  Real Times is not installed on this box, so we
# use STIXGeneral (a Times-compatible serif bundled with matplotlib) and fall
# back to DejaVu Serif.
SERIF = ["STIXGeneral", "Times New Roman", "Times", "DejaVu Serif"]

# Shared font sizes so the three main bar figures are consistent.
FS_TITLE = 12.0
FS_VALUE = 6.8
FS_YTICK = 8.5
FS_XTICK = 8.5
FS_PANEL = 10.0
FS_LEGEND = 11.0


def pct(n: int, d: int) -> float:
    return 100.0 * n / d


# ---------------------------------------------------------------------------
# Data, taken verbatim from Discussion.md Thread #9 (DeepSeek target+defense).
# Each entry: benchmark -> schema -> (BU, AU, ASR) in percent; None = not reported.
# ---------------------------------------------------------------------------

DATA: dict[str, dict[str, tuple[float | None, float | None, float | None]]] = {}


def add(bench: str, schema: str, bu, au, asr):
    DATA.setdefault(bench, {})[schema] = (bu, au, asr)


# ---- Tool: AgentDojo ----
add("AgentDojo", "Ours", pct(84, 97), pct(505, 629), pct(0, 629))
add("AgentDojo", "Undefended", pct(86, 97), pct(464, 629), pct(107, 629))
add("AgentDojo", "DRIFT", pct(74, 97), pct(384, 629), pct(12, 629))
add("AgentDojo", "CaMeL", pct(74, 97), pct(471, 629), pct(7, 629))
add("AgentDojo", "Progent", pct(85, 97), pct(489, 629), pct(4, 629))
add("AgentDojo", "MELON", pct(50, 97), pct(245, 629), pct(4, 629))
add("AgentDojo", "Tool Filter", pct(21, 97), pct(141, 629), pct(1, 629))
add("AgentDojo", "Spotlighting", pct(92, 97), pct(547, 629), pct(1, 629))
add("AgentDojo", "AgentShield", pct(81, 97), pct(502, 629), pct(3, 629))
add("AgentDojo", "TaskShield", pct(42, 97), pct(313, 629), pct(2, 629))

# ---- Tool: ASB-OPI ----
add("ASB-OPI", "Ours", pct(46, 51), pct(1735, 2040), pct(0, 2040))
add("ASB-OPI", "Undefended", pct(45, 51), pct(1453, 2040), pct(1220, 2040))
add("ASB-OPI", "CaMeL", pct(45, 51), pct(1471, 2040), pct(281, 2040))
add("ASB-OPI", "DRIFT", pct(24, 51), pct(776, 2040), pct(200, 2040))
add("ASB-OPI", "MELON", pct(43, 51), pct(1640, 2040), pct(275, 2040))
add("ASB-OPI", "Spotlighting", pct(47, 51), pct(1266, 2040), pct(1043, 2040))
add("ASB-OPI", "Tool Filter", pct(24, 51), pct(1038, 2040), pct(312, 2040))
add("ASB-OPI", "Progent", pct(27, 51), pct(962, 2040), pct(291, 2040))
add("ASB-OPI", "AgentShield", pct(42, 51), pct(1252, 2040), pct(867, 2040))
add("ASB-OPI", "TaskShield", pct(40, 51), pct(599, 2040), pct(296, 2040))

# ---- MCP: MCPTox ----
add("MCPTox", "Ours", pct(231, 357), pct(1015, 1348), pct(0, 1348))
add("MCPTox", "Undefended", pct(247, 357), pct(556, 1348), pct(488, 1348))
add("MCPTox", "MCPGuard", pct(184, 357), pct(704, 1348), pct(1, 1348))
add("MCPTox", "ClawGuard", pct(207, 357), pct(618, 1348), pct(218, 1348))
add("MCPTox", "StackOne", pct(49, 357), pct(179, 1348), pct(13, 1348))
add("MCPTox", "Pipelock", pct(243, 357), pct(608, 1348), pct(414, 1348))

# ---- MCP: MSB (no BU reported) ----
add("MSB", "Ours", None, pct(343, 415), pct(0, 622))
add("MSB", "Undefended", None, pct(376, 415), pct(303, 622))
add("MSB", "MCPGuard", None, pct(308, 415), pct(71, 622))
add("MSB", "ClawGuard", None, pct(367, 415), pct(237, 622))
add("MSB", "StackOne", None, pct(327, 415), pct(101, 622))
add("MSB", "Pipelock", None, pct(367, 415), pct(301, 622))

# ---- Skill: SkillInject ----
add("SkillInject", "Ours", pct(146, 180), pct(142, 180), pct(1, 180))
add("SkillInject", "Undefended", pct(148, 180), pct(150, 180), pct(52, 180))
add("SkillInject", "ClawGuard", pct(82, 180), pct(82, 180), pct(13, 180))
add("SkillInject", "Progent", pct(115, 180), pct(113, 180), pct(28, 180))
add("SkillInject", "TaskShield", pct(96, 180), pct(105, 180), pct(10, 180))
add("SkillInject", "DynamicGuardian", pct(136, 180), pct(141, 180), pct(11, 180))

# ---- Skill: SCR (aggregate the 3 suites per schema over the suites it appears in) ----
# CapFlow (den 150), AuthBlur (den 116), TrustLift (den 401)
SCR = {
    # schema: list of (BU_n, AU_n, ASR_n, den)
    "Ours": [(127, 149, 0, 150), (115, 116, 0, 116), (401, 401, 0, 401)],
    "Undefended": [(120, 93, 90, 150), (116, 116, 84, 116), (401, 401, 401, 401)],
    "TaskShield": [(118, 75, 63, 150), (116, 115, 82, 116), (325, 315, 315, 401)],
    "ClawGuard": [(0, 131, 0, 150), (26, 26, 26, 401)],
    "Progent": [(144, 56, 92, 150), (401, 401, 401, 401)],
    "DynamicGuardian": [(147, 38, 110, 150), (116, 116, 68, 116),
                        (401, 401, 401, 401)],
}
for schema, rows in SCR.items():
    bu_n = sum(r[0] for r in rows)
    au_n = sum(r[1] for r in rows)
    asr_n = sum(r[2] for r in rows)
    den = sum(r[3] for r in rows)
    add("SCR", schema, pct(bu_n, den), pct(au_n, den), pct(asr_n, den))


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

SURFACES = [
    ("Tool", ["AgentDojo", "ASB-OPI"]),
    ("MCP", ["MCPTox", "MSB"]),
    ("Skill", ["SkillInject", "SCR"]),
]

# Global schema order + colors (shared legend).
SCHEMA_ORDER = [
    "Ours",
    "Undefended",
    "Spotlighting",
    "Tool Filter",
    "MELON",
    "CaMeL",
    "DRIFT",
    "Progent",
    "AgentShield",
    "TaskShield",
    "ClawGuard",
    "MCPGuard",
    "StackOne",
    "Pipelock",
    "DynamicGuardian",
]
COLORS = {
    "Ours": "#b0656b",          # muted rose
    "Undefended": "#a9a9a1",     # warm grey
    "Spotlighting": "#8090a8",   # dusty blue
    "Tool Filter": "#a89878",    # taupe
    "MELON": "#8fa382",          # sage green
    "CaMeL": "#c8a27c",          # muted tan
    "DRIFT": "#9a89a8",          # muted mauve
    "Progent": "#c99fb0",        # dusty pink
    "AgentShield": "#7fa39a",    # muted teal
    "TaskShield": "#9fb8bf",     # pale slate blue
    "ClawGuard": "#cbb57e",      # muted gold
    "MCPGuard": "#d7bcc4",       # pale rose
    "StackOne": "#a892b0",       # soft purple
    "Pipelock": "#9a9b73",       # olive
    "DynamicGuardian": "#8a8fa3",  # muted indigo
}

METRICS = [
    ("Benign Utility (BU)", 0, "%"),
    ("Attack Utility (AU)", 1, "%"),
    ("Attack Success Rate (ASR)", 2, "%"),
]


def render(surfaces: list[tuple[str, list[str]]], stem: str, width: float) -> None:
    """Render one BU/AU/ASR figure for the given surface groups."""
    plt.rcParams.update({"font.family": "serif", "font.serif": SERIF, "mathtext.fontset": "stix", "font.size": 9})
    fig, axes = plt.subplots(1, 3, figsize=(width, 3.7), constrained_layout=True)

    bar_w = 0.9
    cluster_gap = 1.6
    surface_gap = 2.6

    # schemas used anywhere in this figure -> for the shared legend
    used_schemas: list[str] = []

    for ax, (mname, midx, ylabel) in zip(axes, METRICS):
        x = 0.0
        xticks: list[float] = []
        xticklabels: list[str] = []
        divider_x: list[float] = []
        region_centers: list[tuple[str, float]] = []

        for si, (surface, benches) in enumerate(surfaces):
            region_start_ticks = len(xticks)
            for bench in benches:
                schemas = [s for s in SCHEMA_ORDER if s in DATA[bench]
                           and DATA[bench][s][midx] is not None]
                start = x
                for s in schemas:
                    if s not in used_schemas:
                        used_schemas.append(s)
                    val = DATA[bench][s][midx]
                    is_ours = s == "Ours"
                    ax.bar(
                        x, val, width=bar_w,
                        color=COLORS[s],
                        edgecolor="#333333" if is_ours else "none",
                        linewidth=1.1 if is_ours else 0.0,
                        hatch="//" if is_ours else None,
                        zorder=3,
                    )
                    ax.text(
                        x, val + 1.2, f"{val:.0f}",
                        ha="center", va="bottom", rotation=90,
                        fontsize=6.2,
                        fontweight="bold" if is_ours else "normal",
                        color="#222", zorder=4,
                    )
                    x += bar_w
                center = (start + x - bar_w) / 2
                xticks.append(center)
                xticklabels.append(bench)
                x += cluster_gap
            centers = xticks[region_start_ticks:]
            region_centers.append((surface, sum(centers) / len(centers)))
            if si < len(surfaces) - 1:
                divider_x.append(x - cluster_gap / 2)
                x += surface_gap

        for dx in divider_x:
            ax.axvline(dx, color="#555", linestyle="--", linewidth=1.0, zorder=1)

        ax.set_xticks(xticks)
        ax.set_xticklabels(xticklabels, rotation=20, ha="right", fontsize=8.5)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(mname, fontsize=12, fontweight="bold")
        ax.set_yticks(range(0, 101, 20))
        ax.grid(axis="y", linestyle=":", color="#d5d5d5", zorder=0)
        ax.set_axisbelow(True)
        ax.margins(x=0.02)
        ax.set_ylim(0, 116)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)

        if len(surfaces) > 1:
            for surface, cx in region_centers:
                ax.text(cx, 110, surface, ha="center", va="bottom",
                        fontsize=10, fontweight="bold", color="#333")

    handles = [Patch(facecolor=COLORS[s], edgecolor="#333333" if s == "Ours" else "none",
                     hatch="//" if s == "Ours" else None, label=s)
               for s in SCHEMA_ORDER if s in used_schemas]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False,
               fontsize=7.6, columnspacing=1.0, handlelength=1.3,
               handletextpad=0.4, bbox_to_anchor=(0.5, -0.045))

    outdir = Path("figures")
    outdir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(outdir / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote figures/{stem}.{{pdf,svg,png}}")


def render_grid(benches: list[str], stem: str, width: float, row_h: float) -> None:
    """Render a (len(benches) x 3) grid: rows = benchmarks, cols = metrics.

    Columns are the three metrics (Utility no-attack / under-attack / ASR),
    separated by figure-level vertical dashed dividers.  Subplots are labelled
    (a)-(f); the benchmark identity is left to the caption.  Value labels are
    horizontal with two decimals.  Rows are compressed.
    """
    plt.rcParams.update({"font.family": "serif", "font.serif": SERIF, "mathtext.fontset": "stix", "font.size": 9})
    nrows = len(benches)
    fig, axes = plt.subplots(
        nrows, 3, figsize=(width, row_h * nrows),
        constrained_layout=True, sharex="col",
    )
    fig.set_constrained_layout_pads(h_pad=0.02, w_pad=0.04, hspace=0.02, wspace=0.03)
    if nrows == 1:
        axes = axes.reshape(1, 3)

    bar_w = 0.82
    used_schemas: list[str] = []
    panel_letters = iter("abcdefghijkl")

    for ri, bench in enumerate(benches):
        for ci, (mname, midx, ylabel) in enumerate(METRICS):
            ax = axes[ri][ci]
            schemas = [s for s in SCHEMA_ORDER if s in DATA[bench]
                       and DATA[bench][s][midx] is not None]
            if not schemas:
                ax.text(
                    0.5, 0.5, "N/A",
                    transform=ax.transAxes,
                    ha="center", va="center",
                    fontsize=FS_TITLE,
                    color="#666",
                    zorder=4,
                )
            for xi, s in enumerate(schemas):
                if s not in used_schemas:
                    used_schemas.append(s)
                val = DATA[bench][s][midx]
                is_ours = s == "Ours"
                ax.bar(
                    xi, val, width=bar_w,
                    color=COLORS[s],
                    edgecolor="#333333" if is_ours else "none",
                    linewidth=1.0 if is_ours else 0.0,
                    hatch="//" if is_ours else None,
                    zorder=3,
                )
                ax.text(
                    xi, val + 1.5, f"{val:.2f}",
                    ha="center", va="bottom", rotation=0,
                    fontsize=FS_VALUE,
                    fontweight="bold" if is_ours else "normal",
                    color="#222", zorder=4,
                )
            ax.set_xticks(range(len(schemas)))
            ax.set_xticklabels([])
            ax.set_yticks(range(0, 101, 25))
            ax.tick_params(axis="y", labelsize=FS_YTICK)
            ax.set_axisbelow(True)
            ax.set_ylim(0, 118)
            ax.margins(x=0.02)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            if ri == 0:
                ax.set_title(mname, fontsize=FS_TITLE, pad=2)
            # (a)-(f) subplot label, centered below each subplot
            ax.text(0.5, -0.11, f"({next(panel_letters)})",
                    transform=ax.transAxes, ha="center", va="top",
                    fontsize=FS_PANEL, fontweight="bold", color="#333")

    # figure-level vertical dashed dividers between the three metric columns,
    # placed just right of each left column so they never cross tick labels.
    fig.canvas.draw()
    for ci in range(len(METRICS) - 1):
        right = axes[0][ci].get_position().x1
        left = axes[0][ci + 1].get_position().x0
        xdiv = right + (left - right) * 0.16
        y0 = axes[-1][ci].get_position().y0
        y1 = axes[0][ci].get_position().y1
        line = plt.Line2D([xdiv, xdiv], [y0, y1], transform=fig.transFigure,
                          color="#777", linestyle="--", linewidth=0.9)
        fig.add_artist(line)

    handles = [Patch(facecolor=COLORS[s], edgecolor="#333333" if s == "Ours" else "none",
                     hatch="//" if s == "Ours" else None, label=s)
               for s in SCHEMA_ORDER if s in used_schemas]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False,
               fontsize=FS_LEGEND, columnspacing=1.0, handlelength=1.3,
               handletextpad=0.4, bbox_to_anchor=(0.5, -0.14))

    outdir = Path("figures")
    outdir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(outdir / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote figures/{stem}.{{pdf,svg,png}}")


def render_surface_grid(surfaces: list[tuple[str, list[str]]], stem: str,
                        width: float, row_h: float) -> None:
    """Render a (len(surfaces) x 3) grid where each cell holds two benchmark
    clusters for one surface.

    Rows = surfaces (e.g. MCP, Skill); columns = the three metrics.  Within a
    cell the two benchmarks are drawn as separate defense-bar clusters, with a
    small gap and the benchmark name below each cluster.  Same muted style,
    (a)-(f) subplot labels, shared legend as the Tool figure.
    """
    plt.rcParams.update({"font.family": "serif", "font.serif": SERIF, "mathtext.fontset": "stix", "font.size": 9})
    nrows = len(surfaces)
    fig, axes = plt.subplots(
        nrows, 3, figsize=(width, row_h * nrows), constrained_layout=True,
    )
    fig.set_constrained_layout_pads(h_pad=0.02, w_pad=0.04, hspace=0.02, wspace=0.10)
    if nrows == 1:
        axes = axes.reshape(1, 3)

    bar_w = 0.82
    cluster_gap = 1.4
    used_schemas: list[str] = []
    panel_letters = iter("abcdefghijkl")

    # per-bench reserved slot (max bars across metrics) and a single global
    # x-extent shared by every cell, so bar widths are uniform across all rows.
    row_slots: dict[int, dict[str, int]] = {}
    global_extent = 0.0
    for ri, (surface, benches) in enumerate(surfaces):
        bench_slot = {
            bench: max(
                (sum(1 for s in SCHEMA_ORDER
                     if s in DATA[bench] and DATA[bench][s][mi] is not None)
                 for _, mi, _ in METRICS),
                default=0,
            )
            for bench in benches
        }
        row_slots[ri] = bench_slot
        extent = (sum(bench_slot.values()) * bar_w
                  + cluster_gap * (len(benches) - 1))
        global_extent = max(global_extent, extent)

    for ri, (surface, benches) in enumerate(surfaces):
        bench_slot = row_slots[ri]
        row_extent = global_extent
        for ci, (mname, midx, ylabel) in enumerate(METRICS):
            ax = axes[ri][ci]
            x = 0.0
            xticks: list[float] = []
            xticklabels: list[str] = []
            for bench in benches:
                schemas = [s for s in SCHEMA_ORDER if s in DATA[bench]
                           and DATA[bench][s][midx] is not None]
                slot = bench_slot[bench]
                start = x
                for s in schemas:
                    if s not in used_schemas:
                        used_schemas.append(s)
                    val = DATA[bench][s][midx]
                    is_ours = s == "Ours"
                    ax.bar(
                        x, val, width=bar_w,
                        color=COLORS[s],
                        edgecolor="#333333" if is_ours else "none",
                        linewidth=1.0 if is_ours else 0.0,
                        hatch="//" if is_ours else None,
                        zorder=3,
                    )
                    ax.text(
                        x, val + 1.5, f"{val:.2f}",
                        ha="center", va="bottom", rotation=0,
                        fontsize=FS_VALUE,
                        fontweight="bold" if is_ours else "normal",
                        color="#222", zorder=4,
                    )
                    x += bar_w
                # pad to the reserved slot width so the cluster centre and the
                # overall x-range match the other metric cells
                x = start + slot * bar_w
                center = start + (slot * bar_w - bar_w) / 2
                xticks.append(center)
                xticklabels.append(bench)
                x += cluster_gap

            ax.set_xticks(xticks)
            ax.set_xticklabels(xticklabels, fontsize=FS_XTICK)
            ax.set_xlim(-0.5 * bar_w - 0.3, row_extent - 0.5 * bar_w + 0.3)
            ax.set_yticks(range(0, 101, 25))
            ax.tick_params(axis="y", labelsize=FS_YTICK)
            ax.set_axisbelow(True)
            ax.set_ylim(0, 118)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            if ri == 0:
                ax.set_title(mname, fontsize=FS_TITLE, pad=2)
            ax.text(0.5, -0.13, f"({next(panel_letters)})",
                    transform=ax.transAxes, ha="center", va="top",
                    fontsize=FS_PANEL, fontweight="bold", color="#333")

    # figure-level vertical dashed dividers between the three metric columns
    fig.canvas.draw()
    for ci in range(len(METRICS) - 1):
        right = axes[0][ci].get_position().x1
        left = axes[0][ci + 1].get_position().x0
        xdiv = right + (left - right) * 0.5
        y0 = axes[-1][ci].get_position().y0
        y1 = axes[0][ci].get_position().y1
        line = plt.Line2D([xdiv, xdiv], [y0, y1], transform=fig.transFigure,
                          color="#777", linestyle="--", linewidth=0.9)
        fig.add_artist(line)

    handles = [Patch(facecolor=COLORS[s], edgecolor="#333333" if s == "Ours" else "none",
                     hatch="//" if s == "Ours" else None, label=s)
               for s in SCHEMA_ORDER if s in used_schemas]
    fig.legend(handles=handles, loc="lower center", ncol=len(handles), frameon=False,
               fontsize=FS_LEGEND, columnspacing=1.0, handlelength=1.3,
               handletextpad=0.4, bbox_to_anchor=(0.5, -0.13))

    outdir = Path("figures")
    outdir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(outdir / f"{stem}.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote figures/{stem}.{{pdf,svg,png}}")


def main() -> None:
    render_grid(
        ["AgentDojo", "ASB-OPI"],
        "main_bars_tool",
        width=11.0,
        row_h=1.35,
    )
    render_grid(
        ["MCPTox", "MSB"],
        "main_bars_mcp",
        width=11.0,
        row_h=1.35,
    )
    render_grid(
        ["SkillInject", "SCR"],
        "main_bars_skill",
        width=11.0,
        row_h=1.35,
    )


if __name__ == "__main__":
    main()
