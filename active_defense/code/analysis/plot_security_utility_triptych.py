"""Compact security-utility triptych for the paper.

Panels: ASB-OPI (Tool), MSB (MCP), and SkillInject (Skill).
X axis is attack utility, Y axis is security = 100 - ASR.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from code.analysis.plot_main_bars import COLORS, DATA, SCHEMA_ORDER, legend_label


SERIF = ["STIXGeneral", "Times New Roman", "Times", "DejaVu Serif"]

PANELS = [
    ("Tool", "ASB-OPI"),
    ("MCP", "MSB"),
    ("Skill", "SkillInject"),
]

APEX_FACE = "#d88f8f"  # light Morandi red
APEX_EDGE = "#9f5b5b"
EDGE = "#545454"
OFFSET_SCALE = 0.68

LABELS = {
    "Ours": "APEX",
    "Tool Filter": "Tool\nFilter",
    "AgentShield": "Agent\nShield",
    "TaskShield": "Task\nShield",
    "MCPGuard": "MCP\nGuard",
    "ClawGuard": "Claw\nGuard",
    "DynamicGuardian": "Dynamic\nGuardian",
}

LABEL_OFFSETS = {
    "ASB-OPI": {
        "Undefended": (8, -9, "left"),
        "Spotlighting": (12, -10, "left"),
        "Tool Filter": (-6, 25, "center"),
        "MELON": (10, 14, "left"),
        "CaMeL": (12, -16, "left"),
        "DRIFT": (-4, 22, "right"),
        "Progent": (-4, -4, "right"),
        "AgentShield": (8, 0, "left"),
        "TaskShield": (-10, -14, "right"),
        "Ours": (13, 13, "left"),
    },
    "MCPTox": {
        "Undefended": (-8, -13, "right"),
        "ClawGuard": (-8, 0, "right"),
        "MCPGuard": (8, 8, "left"),
        "StackOne": (-4, -13, "right"),
        "Pipelock": (8, -11, "left"),
        "Ours": (8, 8, "left"),
    },
    "MSB": {
        "Undefended": (-7, -22, "right"),
        "ClawGuard": (8, 11, "left"),
        "MCPGuard": (-8, 18, "right"),
        "StackOne": (-12, -9, "right"),
        "Pipelock": (9, -11, "left"),
        "Ours": (-6, 20, "right"),
    },
    "SkillInject": {
        "Undefended": (8, -13, "left"),
        "Progent": (-9, -12, "right"),
        "TaskShield": (-6, 24, "center"),
        "ClawGuard": (-18, -2, "right"),
        "DynamicGuardian": (8, -4, "left"),
        "Ours": (8, 10, "left"),
    },
}


def display_label(schema: str) -> str:
    return LABELS.get(schema, legend_label(schema))


def scaled_offset(offset: tuple[int, int, str]) -> tuple[float, float, str]:
    dx, dy, ha = offset
    return dx * OFFSET_SCALE, dy * OFFSET_SCALE, ha


def panel_points(benchmark: str):
    for schema in SCHEMA_ORDER:
        values = DATA.get(benchmark, {}).get(schema)
        if not values:
            continue
        _bu, au, asr = values
        if au is None or asr is None:
            continue
        yield schema, au, 100.0 - asr


def render(stem: str = "security_utility_triptych") -> None:
    plt.rcParams.update({
        "font.family": "serif",
        "font.serif": SERIF,
        "mathtext.fontset": "stix",
        "font.size": 5.2,
        "axes.linewidth": 0.5,
        "xtick.major.width": 0.45,
        "ytick.major.width": 0.45,
        "xtick.major.size": 1.8,
        "ytick.major.size": 1.8,
    })

    # Single-column width for a two-column paper.
    fig, axes = plt.subplots(1, 3, figsize=(3.45, 1.72))

    for ax, (surface, benchmark) in zip(axes, PANELS):
        apex_point = None
        for schema, au, security in panel_points(benchmark):
            if schema == "Ours":
                apex_point = (schema, au, security)
                continue
            color = COLORS.get(schema, "#9a9a9a")
            ax.scatter(
                au, security,
                s=18,
                marker="o",
                facecolor=color,
                edgecolor=EDGE,
                linewidth=0.38,
                alpha=0.9,
                zorder=2,
            )
            dx, dy, ha = scaled_offset(
                LABEL_OFFSETS[benchmark].get(schema, (7, 7, "left")))
            ax.annotate(
                display_label(schema),
                (au, security),
                xytext=(dx, dy),
                textcoords="offset points",
                ha=ha,
                va="center",
                fontsize=4.25,
                color="#303030",
                linespacing=0.82,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.72, pad=0.16),
                arrowprops=dict(
                    arrowstyle="-",
                    color="#777777",
                    lw=0.26,
                    shrinkA=0.6,
                    shrinkB=2.0,
                ),
                zorder=5,
            )

        if apex_point is not None:
            schema, au, security = apex_point
            ax.scatter(
                au, security,
                s=76,
                marker="*",
                facecolor=APEX_FACE,
                edgecolor=APEX_EDGE,
                linewidth=0.48,
                zorder=4,
            )
            dx, dy, ha = scaled_offset(
                LABEL_OFFSETS[benchmark].get("Ours", (8, 8, "left")))
            ax.annotate(
                display_label(schema),
                (au, security),
                xytext=(dx, dy),
                textcoords="offset points",
                ha=ha,
                va="center",
                fontsize=4.95,
                color=APEX_EDGE,
                fontweight="bold",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.76, pad=0.16),
                arrowprops=dict(
                    arrowstyle="-",
                    color=APEX_EDGE,
                    lw=0.3,
                    shrinkA=0.6,
                    shrinkB=2.6,
                ),
                zorder=6,
            )

        ax.set_title(f"{surface}: {benchmark}", fontsize=6.15, pad=2)
        ax.set_xlim(-2, 108)
        ax.set_ylim(25, 122)
        ax.set_xticks([0, 25, 50, 75, 100])
        ax.set_yticks([25, 50, 75, 100])
        ax.grid(False)
        ax.set_box_aspect(1.34)
        ax.tick_params(labelsize=5.0, pad=1.1)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        if ax is not axes[0]:
            ax.set_yticklabels([])

    fig.supxlabel("Attack Utility (%)", fontsize=6.15, y=0.035)
    fig.supylabel("Security = 1 - ASR (%)", fontsize=6.15, x=0.034)

    fig.subplots_adjust(left=0.09, right=0.995, bottom=0.205, top=0.835, wspace=0.14)

    outdir = Path("figures")
    outdir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "svg", "png"):
        fig.savefig(
            outdir / f"{stem}.{ext}",
            dpi=360,
            bbox_inches="tight",
            pad_inches=0.01,
        )
    plt.close(fig)
    print(f"wrote figures/{stem}.{{pdf,svg,png}}")


if __name__ == "__main__":
    render()
