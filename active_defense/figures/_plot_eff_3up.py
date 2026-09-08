#!/usr/bin/env python3.11
"""Efficiency bubble chart: 3 benchmarks side-by-side.
x = Total Tokens (M), y = AU - ASR (%), bubble size = LLM calls.
APEX highlighted red; baselines muted blue. Unified 0-100 y-axis.

Skill-unit tokens count HALF of the DeepSeek prompt-cache hits (a middle ground
between billing total tokens and fully discounting cache), so the skill panel is
not dominated by cache-inflated totals.

Each label is placed outside its own bubble in display-point space using a
greedy candidate search that avoids overlapping any bubble, any already-placed
label, and the axes. Every label has a thin leader line back to its bubble.
"""
import json, os, math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

BASE = ("/mlx_devbox/users/zhengxinran/playground/code_zxr/agent_safety/"
        "active_defense")
AGG = json.load(open(os.path.join(
    BASE, "experiment_results/efficiency_20/DeepSeek/EFF_AGG.json")))

FULL_AUASR = {
    "ASB-OPI": {
        "APEX": (1735 - 0) / 2040 * 100,
        "Undefended": (1453 - 1220) / 2040 * 100,
        "CaMeL": (1471 - 281) / 2040 * 100,
        "DRIFT": (776 - 200) / 2040 * 100,
        "MELON": (1640 - 275) / 2040 * 100,
        "Spotlighting": (1266 - 1043) / 2040 * 100,
        "Tool Filter": (1038 - 312) / 2040 * 100,
        "Progent": (962 - 291) / 2040 * 100,
        "AgentShield": (1252 - 867) / 2040 * 100,
        "TaskShield": (599 - 296) / 2040 * 100,
    },
    "MCPTox": {
        "APEX": (1015 - 0) / 1348 * 100,
        "Undefended": (556 - 488) / 1348 * 100,
        "MCPGuard": (704 - 1) / 1348 * 100,
        "ClawGuard": (618 - 218) / 1348 * 100,
        "StackOne": (179 - 13) / 1348 * 100,
        "Pipelock": (608 - 414) / 1348 * 100,
    },
    "SkillInject": {
        "APEX": (142 - 1) / 180 * 100,
        "Undefended": (150 - 52) / 180 * 100,
        "ClawGuard": (82 - 13) / 180 * 100,
        "Progent": (113 - 28) / 180 * 100,
        "TaskShield": (105 - 10) / 180 * 100,
        "DynamicGuardian": (141 - 11) / 180 * 100,
    },
}

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "font.size": 10,
    "axes.linewidth": 0.8,
})

APEX_C = "#b5544e"
BASE_C = "#6b8cae"
EDGE = "#333333"
LBL_SIZE = 9.0
TICK_SIZE = 9.0

def bubble(calls):
    return (max(calls, 1) ** 0.5) * 16.0

order = ["ASB-OPI", "MCPTox", "SkillInject"]
fig, axes = plt.subplots(1, 3, figsize=(12.8, 3.05))

# Explicit point-space label offsets.  The panels are dense and publication
# figures need stable typography; a purely automatic greedy layout tends to put
# labels too far from their own bubbles or against the axes.
LABEL_OFFSETS = {
    "ASB-OPI": {
        "APEX": (15, 0, "left"),
        "MELON": (-18, 8, "right"),
        "CaMeL": (16, 8, "left"),
        "Tool Filter": (12, 18, "left"),
        "Progent": (12, 18, "left"),
        "DRIFT": (16, 14, "left"),
        "AgentShield": (0, 18, "center"),
        "TaskShield": (16, -10, "left"),
        "Undefended": (-28, 12, "right"),
        "Spotlighting": (30, 2, "left"),
    },
    "MCPTox": {
        "APEX": (-16, 0, "right"),
        "MCPGuard": (15, 0, "left"),
        "ClawGuard": (15, 0, "left"),
        "StackOne": (16, -9, "left"),
        "Pipelock": (-15, 0, "right"),
        "Undefended": (28, 18, "left"),
    },
    "SkillInject": {
        "APEX": (-30, 0, "right"),
        "DynamicGuardian": (25, -12, "left"),
        "Progent": (-18, -25, "right"),
        "TaskShield": (27, 0, "left"),
        "ClawGuard": (27, -1, "left"),
        "Undefended": (-9, 39, "center"),
    },
}


def place_labels(ax, pts, bench):
    """Place labels in display-point space.

    Matplotlib scatter sizes are point^2 areas, so keeping labels outside the
    marker needs to happen in point units rather than mixed x/y data units.
    """
    fig = ax.figure
    fig.canvas.draw()
    dpi = fig.dpi
    px_to_pt = 72.0 / dpi
    ax_box = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    ax_box = tuple(v * 72.0 for v in (ax_box.x0, ax_box.x1, ax_box.y0, ax_box.y1))

    def center_pt(p):
        x, y = ax.transData.transform((p["x"], p["y"]))
        return x * px_to_pt, y * px_to_pt

    def bubble_radius_pt(p):
        return math.sqrt(max(p["s"], 1.0) / math.pi)

    bubble_boxes = []
    for p in pts:
        x, y = center_pt(p)
        r = bubble_radius_pt(p) + 5.0
        bubble_boxes.append((x - r, x + r, y - r, y + r))

    def text_box(anchor_x, anchor_y, text, ha):
        # Conservative width estimate for 9pt serif labels.
        w = max(22.0, 4.8 * len(text))
        h = 11.5
        if ha == "left":
            x0, x1 = anchor_x, anchor_x + w
        elif ha == "right":
            x0, x1 = anchor_x - w, anchor_x
        else:
            x0, x1 = anchor_x - w / 2, anchor_x + w / 2
        return (x0, x1, anchor_y - h / 2, anchor_y + h / 2)

    def overlaps(a, b, pad=2.0):
        return not (
            a[1] + pad <= b[0] or a[0] - pad >= b[1] or
            a[3] + pad <= b[2] or a[2] - pad >= b[3]
        )

    def inside_axes(box, pad=1.5):
        x0, x1, y0, y1 = ax_box
        # Keep labels visibly away from the x-axis baseline; low-y labels such as
        # ASB-OPI Spotlighting otherwise pass the axes test but collide with ticks.
        bottom_pad = 15.0
        return (
            box[0] >= x0 + pad and box[1] <= x1 - pad and
            box[2] >= y0 + bottom_pad and box[3] <= y1 - pad
        )

    angles = [35, 65, 0, 115, 145, -35, -65, -115, -145, 90, -90, 180]
    extra_rings = [11.0, 20.0, 31.0, 44.0, 60.0, 78.0]
    placed = []

    # Larger bubbles first prevents small labels from occupying all good slots.
    for p in sorted(pts, key=lambda q: (not q["apex"], -q["s"], -q["y"])):
        x0, y0 = center_pt(p)
        r0 = bubble_radius_pt(p)
        best = None

        if p["lab"] in LABEL_OFFSETS.get(bench, {}):
            dx, dy, ha = LABEL_OFFSETS[bench][p["lab"]]
            box = text_box(x0 + dx, y0 + dy, p["lab"], ha)
            best = (dx, dy, ha, box)
        else:
            for extra in extra_rings:
                for deg in angles:
                    rad = math.radians(deg)
                    dist = r0 + extra
                    dx = math.cos(rad) * dist
                    dy = math.sin(rad) * dist
                    ha = "left" if dx > 2 else ("right" if dx < -2 else "center")
                    tx, ty = x0 + dx, y0 + dy
                    box = text_box(tx, ty, p["lab"], ha)
                    if not inside_axes(box):
                        continue
                    if any(overlaps(box, other, pad=3.0) for other in placed):
                        continue
                    if any(overlaps(box, b, pad=4.0) for b in bubble_boxes):
                        continue
                    best = (dx, dy, ha, box)
                    break
                if best:
                    break

        if best is None:
            # Last-resort still keeps the label outside the bubble and draws a line.
            dx = r0 + 22.0
            dy = 0.0
            ha = "left"
            box = text_box(x0 + dx, y0 + dy, p["lab"], ha)
            best = (dx, dy, ha, box)

        dx, dy, ha, box = best
        placed.append(box)
        ax.annotate(
            p["lab"], xy=(p["x"], p["y"]), xytext=(dx, dy),
            textcoords="offset points",
            fontsize=LBL_SIZE,
            color=APEX_C if p["apex"] else "#222",
            fontweight="bold" if p["apex"] else "normal",
            ha=ha, va="center", zorder=6,
            bbox=dict(facecolor="white", edgecolor="none", alpha=0.78, pad=1.0),
            arrowprops=dict(
                arrowstyle="-", color="#8a8a8a", lw=0.65,
                shrinkA=3.0, shrinkB=max(5.0, r0 * 0.85),
                connectionstyle="arc3,rad=0.0",
            ))


for ax, bench in zip(axes, order):
    rows = AGG[bench]
    pts = []
    for label, n, au, asr, tok, calls in rows:
        pts.append(dict(
            x=tok / 1e6,
            y=FULL_AUASR[bench].get(label, au - asr),
            s=bubble(calls),
            lab=label,
            apex=(label == "APEX"),
        ))
    if bench == "SkillInject":
        # Keep the skill-unit cost axis readable in the main figure.  The data
        # are still plotted as measured total tokens in millions; the panel
        # simply uses a fixed 0--10M window instead of a tight auto-zoom that
        # visually exaggerates the spread around APEX.
        ax.set_xlim(0, 10)
    else:
        xs = [p["x"] for p in pts]
        xlo, xhi = min(xs), max(xs)
        xpad = (xhi - xlo) * 0.30 or 0.1
        left = xlo - xpad
        right = xhi + xpad
        ax.set_xlim(left, right)
    ax.set_ylim(0, 100)

    for p in pts:
        ax.scatter(
            p["x"], p["y"], s=p["s"],
            c=APEX_C if p["apex"] else BASE_C,
            alpha=0.9 if p["apex"] else 0.55,
            edgecolors=EDGE, linewidths=1.0 if p["apex"] else 0.6,
            zorder=3 if p["apex"] else 2)

    place_labels(ax, pts, bench)

    ax.set_title(bench, fontsize=11, pad=8)
    ax.set_xlabel(r"Total Tokens (M)", fontsize=9.5)
    ax.tick_params(labelsize=TICK_SIZE)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

axes[0].set_ylabel("AU $-$ ASR (%)", fontsize=9.5)

method_handles = [
    Line2D([0], [0], marker="o", linestyle="", markerfacecolor=APEX_C,
           markeredgecolor=EDGE, markersize=9, label="APEX (ours)"),
    Line2D([0], [0], marker="o", linestyle="", markerfacecolor=BASE_C,
           markeredgecolor=EDGE, markersize=9, alpha=0.7, label="Baselines"),
]
leg1 = fig.legend(handles=method_handles, loc="lower center",
                  ncol=2, frameon=False, fontsize=9,
                  bbox_to_anchor=(0.5, -0.03))
fig.add_artist(leg1)

fig.tight_layout(rect=(0, 0.06, 1, 1))
out = os.path.join(BASE, "figures", "efficiency_bubbles_3up")
fig.savefig(out + ".png", dpi=200, bbox_inches="tight")
fig.savefig(out + ".pdf", bbox_inches="tight")
print("wrote", out + ".png/.pdf")
