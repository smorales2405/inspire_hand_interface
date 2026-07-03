#!/usr/bin/env python3
"""Extrae cada <svg> de las figuras HTML a SVG standalone (vector, para la tesis).

Los SVG resultantes son autocontenidos (xmlns + width/height + fuentes) y se
pueden embeber en LaTeX/Word o convertir a PNG con inkscape/rsvg-convert.
Correr desde la raíz del repo:  .venv/bin/python characterization/figures_to_svg.py
"""
import os
import re

STYLE = ('<style>text{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;}'
         '.mono{font-family:ui-monospace,"SF Mono",Menlo,monospace;}'
         '.b{font-weight:600;}.ey{letter-spacing:.14em;}</style>')

# HTML -> nombres de cada <svg> en orden de aparición
JOBS = [
    ('characterization/figures/exp1_step_response.html',
     ['exp1_overlay_pos_vs_t', 'exp1_slope_vs_speed', 'exp1_latency_vs_speed']),
    ('characterization/figures/exp2_force_overshoot.html',
     ['exp2_overshoot_bars', 'exp2_hybrid_comparison']),
]


def main():
    outdir = 'characterization/figures'
    for html, names in JOBS:
        if not os.path.exists(html):
            print("(falta)", html); continue
        src = open(html).read()
        svgs = re.findall(r'<svg\b.*?</svg>', src, re.S)
        for i, svg in enumerate(svgs):
            name = names[i] if i < len(names) else f'chart_{i}'
            m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svg)
            w, h = (m.group(1), m.group(2)) if m else ('760', '400')
            svg = svg.replace('<svg ', f'<svg xmlns="http://www.w3.org/2000/svg" '
                                       f'width="{w}" height="{h}" ', 1)
            svg = svg.replace('>', '>' + STYLE, 1)   # inyecta <style> tras el <svg ...>
            path = os.path.join(outdir, name + '.svg')
            open(path, 'w').write(svg)
            print("svg:", path)


if __name__ == '__main__':
    main()
