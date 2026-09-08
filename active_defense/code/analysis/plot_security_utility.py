"""Generate security-utility SVG plots from frozen paper tables.

The script uses the values recorded in Discussion.md Thread #9 and Thread #10.
It intentionally avoids plotting libraries so the figure can be regenerated in
the minimal project environment.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape


@dataclass(frozen=True)
class Point:
    benchmark: str
    schema: str
    utility: float
    security: float


def pct(numerator: int, denominator: int) -> float:
    return 100.0 * numerator / denominator


ORIGINAL: list[Point] = [
    # AgentDojo
    Point("AgentDojo", "Ours", pct(505, 629), 100 - pct(0, 629)),
    Point("AgentDojo", "Undefended", pct(464, 629), 100 - pct(107, 629)),
    Point("AgentDojo", "DRIFT", pct(384, 629), 100 - pct(12, 629)),
    Point("AgentDojo", "CaMeL", pct(471, 629), 100 - pct(7, 629)),
    Point("AgentDojo", "Progent", pct(489, 629), 100 - pct(4, 629)),
    Point("AgentDojo", "MELON", pct(245, 629), 100 - pct(4, 629)),
    Point("AgentDojo", "Tool Filter", pct(141, 629), 100 - pct(1, 629)),
    Point("AgentDojo", "Spotlighting", pct(547, 629), 100 - pct(1, 629)),
    Point("AgentDojo", "AgentShield", pct(502, 629), 100 - pct(3, 629)),
    # ASB-OPI
    Point("ASB-OPI", "Ours", pct(1735, 2040), 100 - pct(0, 2040)),
    Point("ASB-OPI", "Undefended", pct(1453, 2040), 100 - pct(1220, 2040)),
    Point("ASB-OPI", "CaMeL", pct(1471, 2040), 100 - pct(281, 2040)),
    Point("ASB-OPI", "DRIFT", pct(776, 2040), 100 - pct(200, 2040)),
    Point("ASB-OPI", "MELON", pct(1640, 2040), 100 - pct(275, 2040)),
    Point("ASB-OPI", "Spotlighting", pct(1266, 2040), 100 - pct(1043, 2040)),
    Point("ASB-OPI", "Tool Filter", pct(1038, 2040), 100 - pct(312, 2040)),
    Point("ASB-OPI", "Progent", pct(962, 2040), 100 - pct(291, 2040)),
    Point("ASB-OPI", "AgentShield", pct(1252, 2040), 100 - pct(867, 2040)),
    # SkillInject
    Point("SkillInject", "Ours", pct(142, 180), 100 - pct(1, 180)),
    Point("SkillInject", "Undefended", pct(150, 180), 100 - pct(52, 180)),
    Point("SkillInject", "ClawGuard", pct(82, 180), 100 - pct(13, 180)),
    Point("SkillInject", "Progent", pct(113, 180), 100 - pct(28, 180)),
    Point("SkillInject", "TaskShield", pct(105, 180), 100 - pct(10, 180)),
    # SCR, aggregated over CapFlow/AuthBlur/TrustLift when present.
    Point("SCR", "Ours", pct(149 + 116 + 401, 150 + 116 + 401), 100 - pct(0, 667)),
    Point("SCR", "Undefended", pct(93 + 116 + 401, 667), 100 - pct(90 + 84 + 401, 667)),
    Point("SCR", "TaskShield", pct(75 + 115 + 315, 667), 100 - pct(63 + 82 + 315, 667)),
    # MCPTox
    Point("MCPTox", "Ours", pct(1015, 1348), 100 - pct(0, 1348)),
    Point("MCPTox", "Undefended", pct(556, 1348), 100 - pct(488, 1348)),
    Point("MCPTox", "MCPGuard", pct(704, 1348), 100 - pct(1, 1348)),
    Point("MCPTox", "ClawGuard", pct(618, 1348), 100 - pct(218, 1348)),
    Point("MCPTox", "StackOne", pct(179, 1348), 100 - pct(13, 1348)),
    Point("MCPTox", "Pipelock", pct(608, 1348), 100 - pct(414, 1348)),
    # MSB
    Point("MSB", "Ours", pct(343, 415), 100 - pct(0, 622)),
    Point("MSB", "Undefended", pct(376, 415), 100 - pct(303, 622)),
    Point("MSB", "MCPGuard", pct(308, 415), 100 - pct(71, 622)),
    Point("MSB", "ClawGuard", pct(367, 415), 100 - pct(237, 622)),
    Point("MSB", "StackOne", pct(327, 415), 100 - pct(101, 622)),
    Point("MSB", "Pipelock", pct(367, 415), 100 - pct(301, 622)),
]


ADAPTIVE: list[Point] = [
    # ASB-OPI AutoDojo-style T4
    Point("ASB-OPI", "Undefended", pct(388, 400), 100 - pct(345, 400)),
    Point("ASB-OPI", "Ours", pct(303, 400), 100 - pct(0, 400)),
    Point("ASB-OPI", "MELON", pct(335, 400), 100 - pct(45, 400)),
    Point("ASB-OPI", "CaMeL", pct(284, 400), 100 - pct(46, 400)),
    Point("ASB-OPI", "DRIFT", pct(147, 400), 100 - pct(34, 400)),
    # SkillInject SkillJect fusion
    Point("SkillInject", "Ours", pct(41, 44), 100 - pct(0, 44)),
    Point("SkillInject", "Undefended", pct(38, 44), 100 - pct(21, 44)),
    Point("SkillInject", "ClawGuard", pct(24, 44), 100 - pct(5, 44)),
    Point("SkillInject", "Progent", pct(19, 44), 100 - pct(4, 44)),
    Point("SkillInject", "TaskShield", pct(29, 44), 100 - pct(1, 44)),
    # SCR CapFlow SkillJect composition fusion
    Point("SCR CapFlow", "Ours", pct(147, 150), 100 - pct(0, 150)),
    Point("SCR CapFlow", "Undefended", pct(21, 150), 100 - pct(125, 150)),
    Point("SCR CapFlow", "ClawGuard", pct(35, 150), 100 - pct(114, 150)),
    Point("SCR CapFlow", "Progent", pct(30, 150), 100 - pct(106, 150)),
    Point("SCR CapFlow", "TaskShield", pct(30, 150), 100 - pct(67, 150)),
    # MCPTox MCP-ITP
    Point("MCPTox", "Ours", pct(357, 455), 100 - pct(7, 455)),
    Point("MCPTox", "Undefended", pct(140, 455), 100 - pct(245, 455)),
    Point("MCPTox", "MCPGuard", pct(149, 455), 100 - pct(203, 455)),
    Point("MCPTox", "ClawGuard", pct(260, 455), 100 - pct(18, 455)),
    Point("MCPTox", "StackOne", pct(229, 455), 100 - pct(33, 455)),
    Point("MCPTox", "Pipelock", pct(131, 455), 100 - pct(241, 455)),
    # MSB MCP-ITP
    Point("MSB", "Ours", pct(130, 212), 100 - pct(0, 212)),
    Point("MSB", "Undefended", pct(64, 212), 100 - pct(99, 212)),
    Point("MSB", "MCPGuard", pct(71, 212), 100 - pct(91, 212)),
    Point("MSB", "ClawGuard", pct(72, 212), 100 - pct(82, 212)),
    Point("MSB", "StackOne", pct(68, 212), 100 - pct(26, 212)),
    Point("MSB", "Pipelock", pct(62, 212), 100 - pct(100, 212)),
]


COLORS = {
    "Ours": "#ef3b2c",
    "Undefended": "#666666",
    "DRIFT": "#7b3294",
    "CaMeL": "#f97316",
    "Progent": "#db2777",
    "MELON": "#16a34a",
    "Tool Filter": "#a16207",
    "Spotlighting": "#2563eb",
    "AgentShield": "#334155",
    "ClawGuard": "#f59e0b",
    "TaskShield": "#0891b2",
    "MCPGuard": "#fb7185",
    "StackOne": "#8b5cf6",
    "Pipelock": "#65a30d",
}

MARKERS = {
    "AgentDojo": "circle",
    "ASB-OPI": "square",
    "SkillInject": "triangle",
    "SCR": "diamond",
    "SCR CapFlow": "diamond",
    "MCPTox": "cross",
    "MSB": "plus",
}

SURFACE_GROUPS = [
    ("Tool", ["AgentDojo", "ASB-OPI"], ""),
    ("MCP", ["MCPTox", "MSB"], "7 4"),
    ("Skill", ["SkillInject", "SCR", "SCR CapFlow"], "2 4"),
]


def grouped(points: list[Point]) -> dict[str, list[Point]]:
    out: dict[str, list[Point]] = {}
    for point in points:
        out.setdefault(point.schema, []).append(point)
    return out


def marker_svg(shape: str, x: float, y: float, color: str, size: int = 8) -> str:
    if shape == "circle":
        return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{size/2}" fill="{color}" stroke="#111" stroke-width="1"/>'
    if shape == "square":
        h = size / 2
        return f'<rect x="{x-h:.2f}" y="{y-h:.2f}" width="{size}" height="{size}" fill="{color}" stroke="#111" stroke-width="1"/>'
    if shape == "triangle":
        h = size * 0.62
        pts = [(x, y - h), (x - size / 2, y + h / 2), (x + size / 2, y + h / 2)]
        points = " ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
        return f'<polygon points="{points}" fill="{color}" stroke="#111" stroke-width="1"/>'
    if shape == "diamond":
        h = size / 1.35
        pts = [(x, y - h), (x - h, y), (x, y + h), (x + h, y)]
        points = " ".join(f"{px:.2f},{py:.2f}" for px, py in pts)
        return f'<polygon points="{points}" fill="{color}" stroke="#111" stroke-width="1"/>'
    if shape == "cross":
        h = size / 2
        return (
            f'<line x1="{x-h:.2f}" y1="{y-h:.2f}" x2="{x+h:.2f}" y2="{y+h:.2f}" stroke="{color}" stroke-width="2"/>'
            f'<line x1="{x-h:.2f}" y1="{y+h:.2f}" x2="{x+h:.2f}" y2="{y-h:.2f}" stroke="{color}" stroke-width="2"/>'
        )
    h = size / 2
    return (
        f'<line x1="{x-h:.2f}" y1="{y:.2f}" x2="{x+h:.2f}" y2="{y:.2f}" stroke="{color}" stroke-width="2"/>'
        f'<line x1="{x:.2f}" y1="{y-h:.2f}" x2="{x:.2f}" y2="{y+h:.2f}" stroke="{color}" stroke-width="2"/>'
    )


def label_offsets(schema: str, panel: str) -> tuple[float, float]:
    offsets = {
        "Tool": {
            "Ours": (8, -10),
            "DRIFT": (8, 6),
            "CaMeL": (8, 14),
            "Progent": (8, -12),
            "MELON": (8, -2),
            "Tool Filter": (8, 12),
            "Spotlighting": (8, -12),
            "AgentShield": (8, 8),
        },
        "MCP": {
            "Ours": (8, -8),
            "MCPGuard": (8, -10),
            "ClawGuard": (8, 10),
            "StackOne": (8, -8),
            "Pipelock": (8, 10),
        },
        "Skill": {
            "Ours": (8, -10),
            "ClawGuard": (8, 8),
            "Progent": (8, -8),
            "TaskShield": (8, 10),
        },
    }
    return offsets.get(panel, {}).get(schema, (8, 0))


def make_surface_plot(points: list[Point], benchmark_order: list[str], title: str, output: Path) -> None:
    width, height = 680, 690
    left, right, top, bottom = 66, 116, 54, 56
    panel_gap = 24
    plot_w = width - left - right
    panel_h = (height - top - bottom - panel_gap * 2) / 3
    x_min, x_max = 0.0, 100.0
    y_min, y_max = 20.0, 105.0

    def panel_top(idx: int) -> float:
        return top + idx * (panel_h + panel_gap)

    def sx(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * plot_w

    def sy(value: float, idx: int) -> float:
        return panel_top(idx) + (y_max - value) / (y_max - y_min) * panel_h

    order_index = {name: idx for idx, name in enumerate(benchmark_order)}
    points = [p for p in points if p.schema != "Undefended"]
    lines: list[str] = []
    lines.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">')
    lines.append('<rect width="100%" height="100%" fill="#ffffff"/>')
    lines.append(f'<text x="{width/2:.2f}" y="34" text-anchor="middle" font-family="Arial, sans-serif" font-size="24" font-weight="700">{escape(title)}</text>')

    for panel_idx, (surface, benchmarks, _dasharray) in enumerate(SURFACE_GROUPS):
        ptop = panel_top(panel_idx)
        panel_points = [p for p in points if p.benchmark in benchmarks]
        active_benchmarks = [b for b in benchmarks if any(p.benchmark == b for p in panel_points)]

        lines.append(f'<text x="{left+4}" y="{ptop+18:.2f}" font-family="Arial, sans-serif" font-size="16" font-weight="700">{escape(surface)}</text>')
        lines.append(f'<text x="{left+72}" y="{ptop+18:.2f}" font-family="Arial, sans-serif" font-size="11" fill="#666">{escape(" / ".join(active_benchmarks))}</text>')

        for tick in range(20, 101, 20):
            y = sy(tick, panel_idx)
            lines.append(f'<text x="{left-12}" y="{y+4:.2f}" text-anchor="end" font-family="Arial, sans-serif" font-size="12" fill="#333">{tick}</text>')
        for tick in range(0, 101, 25):
            x = sx(tick)
            if panel_idx == len(SURFACE_GROUPS) - 1:
                lines.append(f'<text x="{x:.2f}" y="{ptop+panel_h+22:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="12" fill="#333">{tick}</text>')

        lines.append(f'<line x1="{left}" y1="{ptop+panel_h:.2f}" x2="{left+plot_w}" y2="{ptop+panel_h:.2f}" stroke="#222" stroke-width="1.3"/>')
        lines.append(f'<line x1="{left}" y1="{ptop}" x2="{left}" y2="{ptop+panel_h:.2f}" stroke="#222" stroke-width="1.3"/>')

        if not active_benchmarks:
            lines.append(f'<text x="{left+plot_w/2:.2f}" y="{ptop+panel_h/2:.2f}" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" fill="#777">No result</text>')
            continue

        by_schema = grouped(panel_points)
        for schema in sorted(by_schema, key=lambda s: (s != "Ours", s)):
            seq = sorted(by_schema[schema], key=lambda p: order_index.get(p.benchmark, 999))
            color = COLORS.get(schema, "#000000")
            coords = [(sx(p.utility), sy(p.security, panel_idx)) for p in seq]
            if len(coords) > 1:
                path = " ".join(f"{x:.2f},{y:.2f}" for x, y in coords)
                lines.append(f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="{3.2 if schema == "Ours" else 2.2}" opacity="0.86"/>')
            for point, (x, y) in zip(seq, coords):
                lines.append(marker_svg(MARKERS.get(point.benchmark, "circle"), x, y, color, 10 if schema == "Ours" else 8))
                lines.append(
                    f'<title>{escape(schema)} / {escape(surface)} / {escape(point.benchmark)}: '
                    f'AU={point.utility:.1f}%, Security={point.security:.1f}%</title>'
                )

            if not coords:
                continue
            label_x, label_y = coords[-1]
            dx, dy = label_offsets(schema, surface)
            anchor = "start"
            if label_x + dx > width - 52:
                dx = -8
                anchor = "end"
            lines.append(
                f'<text x="{label_x+dx:.2f}" y="{label_y+dy:.2f}" text-anchor="{anchor}" '
                f'font-family="Arial, sans-serif" font-size="{13 if schema == "Ours" else 11}" '
                f'font-weight="{700 if schema == "Ours" else 500}" fill="{color}">{escape(schema)}</text>'
            )

    lines.append(f'<text x="{left+plot_w/2:.2f}" y="{height-28}" text-anchor="middle" font-family="Arial, sans-serif" font-size="15">Utility, AU (%)</text>')
    lines.append(f'<text transform="translate(24 {top + (height - top - bottom) / 2:.2f}) rotate(-90)" text-anchor="middle" font-family="Arial, sans-serif" font-size="15">Security = 1 - ASR (%)</text>')

    legend_x = left + plot_w + 28
    legend_y = top + 14
    used_benchmarks = [b for b in benchmark_order if any(p.benchmark == b for p in points)]
    lines.append(f'<text x="{legend_x}" y="{legend_y}" font-family="Arial, sans-serif" font-size="13" font-weight="700">Benchmarks</text>')
    for idx, benchmark in enumerate(used_benchmarks):
        y = legend_y + 22 + idx * 20
        lines.append(marker_svg(MARKERS.get(benchmark, "circle"), legend_x + 9, y - 4, "#ffffff", 8))
        lines.append(f'<text x="{legend_x+26}" y="{y}" font-family="Arial, sans-serif" font-size="11" fill="#222">{escape(benchmark)}</text>')

    lines.append("</svg>")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    original_order = ["AgentDojo", "ASB-OPI", "SkillInject", "SCR", "MCPTox", "MSB"]
    adaptive_order = ["ASB-OPI", "SkillInject", "SCR CapFlow", "MCPTox", "MSB"]
    make_surface_plot(
        ORIGINAL,
        original_order,
        "Original Security-Utility",
        Path("figures/security_utility_original.svg"),
    )
    make_surface_plot(
        ADAPTIVE,
        adaptive_order,
        "Adaptive Security-Utility",
        Path("figures/security_utility_adaptive.svg"),
    )


if __name__ == "__main__":
    main()
