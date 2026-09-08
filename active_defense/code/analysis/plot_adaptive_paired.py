"""Adaptive-attack paired bars (Discussion.md Thread #10).

A 2-row x 5-col grid:
  * Row 0: Attack Utility (AU).
  * Row 1: Attack Success Rate (ASR).
  * Columns: the five applicability subsets
    (ASB-OPI, SkillInject, SCR CapFlow, MCPTox, MSB).

Within each subplot every defense gets two adjacent bars -- Original (light)
and Adaptive (dark, same Morandi hue) -- and the two bar tops are joined by a
thin line so the original->adaptive change is visible.  Ours is hatched.
Muted (Morandi) palette to match ``main_bars_tool``.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

SERIF = ["STIXGeneral", "Times New Roman", "Times", "DejaVu Serif"]


def pct(n: int, d: int) -> float:
    return 100.0 * n / d


# ---------------------------------------------------------------------------
# Data, verbatim from Discussion.md Thread #10 (DeepSeek target).
# DATA[bench][schema] = (au_orig, au_adp, asr_orig, asr_adp) in percent.
# ---------------------------------------------------------------------------
DATA: dict[str, dict[str, tuple[float, float, float, float]]] = {}


def add(bench, schema, au_o, au_a, asr_o, asr_a, den):
    DATA.setdefault(bench, {})[schema] = (
        pct(au_o, den), pct(au_a, den), pct(asr_o, den), pct(asr_a, den),
    )


# ---- ASB-OPI (400 cells) : AutoDojo-style T4 ----
add("ASB-OPI", "Ours", 344, 303, 0, 0, 400)
add("ASB-OPI", "Undefended", 333, 388, 164, 345, 400)
add("ASB-OPI", "MELON", 332, 335, 50, 45, 400)
add("ASB-OPI", "CaMeL", 304, 284, 43, 46, 400)
add("ASB-OPI", "DRIFT", 160, 147, 35, 34, 400)

# ---- SkillInject (44 pairs) : SkillJect fusion ----
add("SkillInject", "Ours", 37, 41, 0, 0, 44)
add("SkillInject", "Undefended", 33, 38, 10, 21, 44)
add("SkillInject", "ClawGuard", 12, 24, 0, 5, 44)
add("SkillInject", "Progent", 15, 19, 1, 4, 44)
add("SkillInject", "TaskShield", 18, 29, 0, 1, 44)

# ---- SCR CapFlow (150 cases) : SkillJect composition fusion ----
add("SCR CapFlow", "Ours", 149, 147, 0, 0, 150)
add("SCR CapFlow", "Undefended", 51, 21, 96, 125, 150)
add("SCR CapFlow", "ClawGuard", 49, 35, 98, 114, 150)
add("SCR CapFlow", "Progent", 56, 30, 92, 106, 150)
add("SCR CapFlow", "TaskShield", 75, 30, 63, 67, 150)

# ---- MCPTox Template-2 (455 cases) : MCP-ITP strong budget ----
add("MCPTox", "Ours", 370, 357, 0, 7, 455)
add("MCPTox", "Undefended", 167, 140, 145, 245, 455)
add("MCPTox", "MCPGuard", 240, 149, 1, 203, 455)
add("MCPTox", "ClawGuard", 197, 260, 71, 18, 455)
add("MCPTox", "StackOne", 68, 229, 9, 33, 455)
add("MCPTox", "Pipelock", 206, 131, 136, 241, 455)

# ---- MSB (212 applicable cases) : MCP-ITP payload-aware ----
add("MSB", "Ours", 175, 130, 0, 0, 212)
add("MSB", "Undefended", 174, 64, 80, 99, 212)
add("MSB", "MCPGuard", 157, 71, 40, 91, 212)
add("MSB", "ClawGuard", 166, 72, 80, 82, 212)
add("MSB", "StackOne", 165, 68, 49, 26, 212)
add("MSB", "Pipelock", 165, 62, 77, 100, 212)


# Per-benchmark defense order (Ours first).
SCHEMAS: dict[str, list[str]] = {
    "ASB-OPI": ["Ours", "Undefended", "MELON", "CaMeL", "DRIFT"],
    "SkillInject": ["Ours", "Undefended", "ClawGuard", "Progent", "TaskShield"],
    "SCR CapFlow": ["Ours", "Undefended", "ClawGuard", "Progent", "TaskShield"],
    "MCPTox": ["Ours", "Undefended", "MCPGuard", "ClawGuard", "StackOne", "Pipelock"],
    "MSB": ["Ours", "Undefended", "MCPGuard", "ClawGuard", "StackOne", "Pipelock"],
}

BENCHES = ["ASB-OPI", "MCPTox", "MSB", "SkillInject", "SCR CapFlow"]

# Morandi base hue per defense (from main_bars_tool).
COLORS = {
    "Ours": "#b0656b",
    "Undefended": "#a9a9a1",
    "MELON": "#8fa382",
    "CaMeL": "#c8a27c",
    "DRIFT": "#9a89a8",
    "Progent": "#c99fb0",
    "TaskShield": "#9fb8bf",
    "ClawGuard": "#cbb57e",
    "MCPGuard": "#d7bcc4",
    "StackOne": "#a892b0",
    "Pipelock": "#9a9b73",
}


def lighten(hexcolor: str, amount: float = 0.55) -> tuple[float, float, float]:
    """Blend towards white for the Original (lighter) bar."""
    r, g, b = mcolors.to_rgb(hexcolor)
    return (r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount)


def render() -> None:
    plt.rcParams.update({
        "font.family": "serif", "font.serif": SERIF,
        "mathtext.fontset": "stix", "font.size": 9,
    })
    fig, axes = plt.subplots(2, 5, figsize=(15.5, 3.0), constrained_layout=True)
    fig.set_constrained_layout_pads(h_pad=0.03, w_pad=0.04, hspace=0.05, wspace=0.06)

    ROWS = [("Attack Utility (AU)", 0), ("Attack Success Rate (ASR)", 2)]
    bar_w = 0.38
    letters = iter("abcdefghij")

    for ri, (row_name, base_idx) in enumerate(ROWS):
        for ci, bench in enumerate(BENCHES):
            ax = axes[ri][ci]
            schemas = SCHEMAS[bench]
            for xi, s in enumerate(schemas):
                vals = DATA[bench][s]
                v_orig = vals[base_idx]
                v_adp = vals[base_idx + 1]
                base = COLORS[s]
                light = lighten(base)
                is_ours = s == "Ours"

                xo = xi - bar_w / 2 - 0.02
                xa = xi + bar_w / 2 + 0.02

                # Original bar (light) + Adaptive bar (dark).
                ax.bar(xo, v_orig, width=bar_w, color=light,
                       edgecolor="#333" if is_ours else "#8a8a8a",
                       linewidth=0.9 if is_ours else 0.4,
                       hatch="//" if is_ours else None, zorder=3)
                ax.bar(xa, v_adp, width=bar_w, color=base,
                       edgecolor="#333" if is_ours else "none",
                       linewidth=1.0 if is_ours else 0.0,
                       hatch="//" if is_ours else None, zorder=3)

                # Horizontal value labels above each bar.
                for xx, vv in ((xo, v_orig), (xa, v_adp)):
                    ax.text(xx, vv + 1.8, f"{vv:.1f}", ha="center", va="bottom",
                            rotation=0, fontsize=6.6,
                            fontweight="bold" if is_ours else "normal",
                            color="#222", zorder=6)

            ax.set_xticks(range(len(schemas)))
            ax.set_xticklabels(schemas, rotation=22, ha="right", fontsize=7.4)
            ax.set_yticks(range(0, 101, 25))
            ax.tick_params(axis="y", labelsize=8)
            ax.set_ylim(0, 118)
            ax.set_xlim(-0.7, len(schemas) - 0.3)
            ax.set_axisbelow(True)
            for spine in ("top", "right"):
                ax.spines[spine].set_visible(False)
            if ri == 0:
                ax.set_title(bench, fontsize=11, fontweight="bold", pad=4)
            if ci == 0:
                ax.set_ylabel(row_name, fontsize=10)
            ax.text(0.5, -0.30, f"({next(letters)})", transform=ax.transAxes,
                    ha="center", va="top", fontsize=9, fontweight="bold",
                    color="#333")

    legend_handles = [
        Patch(facecolor="#bdbdbd", edgecolor="#8a8a8a", linewidth=0.4, label="Original attack"),
        Patch(facecolor="#6f6f6f", edgecolor="none", label="Adaptive attack"),
        Patch(facecolor="#b0656b", edgecolor="#333", hatch="//", label="Ours"),
    ]
    fig.legend(handles=legend_handles, loc="lower center", ncol=3, frameon=False,
               fontsize=10, columnspacing=1.6, handlelength=1.4,
               handletextpad=0.5, bbox_to_anchor=(0.5, -0.06))

    # Figure-level vertical dashed dividers between adjacent benchmark columns
    # (each column is one dataset).
    fig.canvas.draw()
    for ci in range(len(BENCHES) - 1):
        right = axes[0][ci].get_position().x1
        left = axes[0][ci + 1].get_position().x0
        xdiv = right + (left - right) * 0.28
        y0 = axes[-1][0].get_position().y0
        y1 = axes[0][0].get_position().y1
        line = plt.Line2D([xdiv, xdiv], [y0, y1], transform=fig.transFigure,
                          color="#888", linestyle="--", linewidth=0.9, zorder=0)
        fig.add_artist(line)

    outdir = Path("figures")
    outdir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(outdir / f"adaptive_paired_2x5.{ext}", dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("wrote figures/adaptive_paired_2x5.{pdf,svg,png}")


if __name__ == "__main__":
    render()
