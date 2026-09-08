import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["DejaVu Serif"],
    "mathtext.fontset": "dejavuserif",
    "axes.linewidth": 0.9,
})

# (name, AU, ASR, calls, total_tokens, label dx(pts), dy(pts), ha)
data = [
    ("Ours",         75.0, 0.0,  162, 125491,   0,  20, "center"),
    ("Undefended",   60.0, 55.0, 102, 124397,  10, -20, "left"),
    ("MELON",        75.0, 10.0,  96, 119721, -18,  10, "right"),
    ("CaMeL",        65.0, 10.0, 104, 137136,  16,  10, "left"),
    ("Tool Filter",  50.0,  5.0, 104,  99622,  10,  16, "left"),
    ("Progent",      40.0, 20.0,  99, 125564, -16,  12, "right"),
    ("DRIFT",        20.0,  5.0, 121, 130466,  14,  12, "left"),
    ("Spotlighting", 55.0, 45.0,  93, 123932, -16,   4, "right"),
    ("AgentShield",  45.0, 20.0,  93, 159899,   0,  18, "center"),
    ("TaskShield",   15.0,  5.0, 198, 174655,   0, -20, "center"),
]

MUTED_BLUE = "#6b8cae"
OURS_RED   = "#b5544e"

fig, ax = plt.subplots(figsize=(5.2, 3.6), constrained_layout=True)

for name, au, asr, calls, tok, dx, dy, ha in data:
    x = tok / 1e6
    y = au - asr
    ours = name == "Ours"
    ax.scatter(x, y, s=calls * 4.5,
               facecolor=OURS_RED if ours else MUTED_BLUE,
               alpha=0.9 if ours else 0.6,
               edgecolors="#333333", linewidths=0.9, zorder=3)
    # leader line from bubble edge toward label
    ax.annotate(
        name, (x, y), xytext=(dx, dy), textcoords="offset points",
        ha=ha, va="center", fontsize=8.5,
        fontweight="bold" if ours else "normal",
        color="#7a2f2b" if ours else "#2b2b2b",
        arrowprops=dict(arrowstyle="-", lw=0.6, color="#999999",
                        shrinkA=0, shrinkB=3),
        zorder=4)

ax.set_xlabel("Total Tokens (M)", fontsize=10.5)
ax.set_ylabel(r"AU $-$ ASR", fontsize=10.5)
ax.set_title("ASB-OPI", fontsize=11)
ax.set_ylim(-8, 92)
ax.set_xlim(0.090, 0.185)
ax.tick_params(labelsize=9)
for spine in ("top", "right"):
    ax.spines[spine].set_visible(False)
ax.grid(True, ls=":", lw=0.5, alpha=0.4)

fig.savefig("figures/eff_asb_opi.png", dpi=220)
fig.savefig("figures/eff_asb_opi.pdf")
print("saved")
