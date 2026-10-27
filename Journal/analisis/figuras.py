#!/usr/bin/env python3
"""Figuras de la sección Results del artículo para *Mechatronics*.

Uso:  python3 Journal/analisis/figuras.py [Figure_4 ...]   (desde la raíz del repo)

Lee los mismos archivos crudos que `resultados.py` (y su `resultados.json`) y
escribe PDF vectoriales al ancho exacto de `elsarticle` 5p: una columna 252 pt,
página completa 522 pt. Las fuerzas se dibujan en N (1 gf = 9.807 mN).

Colores (paleta validada; la identidad nunca va solo en el color):
  dedos     pulgar #2a78d6 · índice #eb6834 · medio #1baf7a
  brazos    lazo #4a3aa7 · firmware #898781
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
import numpy as np

REPO = Path(__file__).resolve().parents[2]
CAR, CTRL = REPO / "Caracterizacion", REPO / "Control"
EXP2, EXP3 = CAR / "exp2", CAR / "exp3" / "data"
OUT = Path("/home/utec/Documents/UTEC/2026-2/PI 2/Mechatronics Journal/figures")
sys.path.insert(0, str(CTRL))
from a2_hipotesis import lee_bitacora, lee_brazos, trials  # noqa: E402

R = json.loads((Path(__file__).with_name("resultados.json")).read_text())
G2N = 9.80665e-3
COL, PAG = 252 / 72.27, 522 / 72.27            # pulgadas

for f in fm.findSystemFonts():
    if "LiberationSans" in f:
        fm.fontManager.addfont(f)
TINTA, TINTA2, EJE, REJ = "#0b0b0b", "#52514e", "#c3c2b7", "#e6e5df"
PULGAR, INDICE, MEDIO = "#2a78d6", "#eb6834", "#1baf7a"
LAZO, FW = "#4a3aa7", "#898781"
matplotlib.rcParams.update({
    "font.family": "Liberation Sans", "font.size": 7, "axes.labelsize": 7, "axes.titlesize": 7,
    "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.titlepad": 3,
    "text.color": TINTA, "axes.labelcolor": TINTA2, "xtick.color": TINTA2, "ytick.color": TINTA2,
    "axes.edgecolor": EJE, "axes.linewidth": 0.6, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": REJ, "grid.linewidth": 0.4, "axes.axisbelow": True,
    "xtick.major.size": 2.5, "ytick.major.size": 2.5, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
    "lines.linewidth": 1.0, "legend.frameon": False, "pdf.fonttype": 42,
    "figure.facecolor": "white", "savefig.facecolor": "white",
    "mathtext.fontset": "custom", "mathtext.rm": "Liberation Sans", "mathtext.it": "Liberation Sans:italic",
    "mathtext.default": "regular", "mathtext.cal": "Liberation Sans",
})


def figura(w, h, **kw):
    return plt.subplots(figsize=(w, h), constrained_layout=True, **kw)


def guardar(fig, nombre):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / f"{nombre}.pdf")
    plt.close(fig)
    print(f"  {nombre}.pdf")


def leer(path, cols):
    out = {c: [] for c in cols}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            for c in cols:
                v = r.get(c, "")
                out[c].append(float(v) if v not in ("", None) else np.nan)
    return {c: np.array(v) for c, v in out.items()}


def cambios(t, x):
    m = ~np.isnan(x)
    t, x = t[m], x[m]
    i = np.nonzero(np.diff(x) != 0)[0] + 1
    return t[i]


def letra(ax, s):
    ax.set_title(s, loc="left", fontweight="bold")


# ── Fig. 4: temporización ─────────────────────────────────────────────────
def Figure_4():
    fig, (a, b) = figura(COL, 2.35, nrows=2, gridspec_kw={"height_ratios": [1.15, 1]})
    T = R["temporizacion"]["carga"]["mediana_ms"]
    bins = np.arange(0, 131, 2)
    for v, col, lab in ((25, "#a8a6a0", "$v$ = 25"), (1000, TINTA, "$v$ = 1000")):
        dt = []
        for f in sorted((EXP2 / f"data_dof4_tcp_bif_v{v}").glob("trace_*.csv")):
            s = leer(f, ["t_s", "pos_act", "force_g"])
            dt += list(np.diff(cambios(s["t_s"], s["pos_act"])) * 1e3)
            dt += list(np.diff(cambios(s["t_s"], s["force_g"])) * 1e3)
        h, _ = np.histogram(dt, bins)
        a.step(bins[:-1], h / h.sum(), where="post", color=col, lw=0.9, label=lab)
    for k in (1, 2, 3, 4):
        a.axvline(k * T, color=EJE, lw=0.6, ls=(0, (3, 2)), zorder=0)
    a.text(128, 0.10, f"dashed: multiples of\n$T_{{pub}}$ = {T:.1f} ms", ha="right", va="bottom",
           fontsize=6.5, color=TINTA2)
    a.set_xlim(0, 130)
    a.set_xlabel("interval between changes of the published value (ms)")
    a.set_ylabel("fraction")
    a.legend(loc="upper right", handlelength=1.4)
    letra(a, "(a)")
    rng = np.random.default_rng(3)
    for i, v in enumerate((25, 1000)):
        o = [int(r["onset_pos"]) for r in csv.DictReader(open(EXP2 / f"data_dof4_tcp_bif_v{v}" / "onset_trials.csv"))
             if r["onset_pos"]]
        b.plot(o, i + rng.uniform(-0.18, 0.18, len(o)), "o", ms=2.6, mfc="none",
               mec=TINTA if v == 1000 else "#7d7b75", mew=0.6)
    av = R["temporizacion"]["v1000"]["avance_por_refresco"]
    b.annotate("", xy=(921, 1.42), xytext=(921 - av, 1.42),
               arrowprops=dict(arrowstyle="<->", color=TINTA2, lw=0.6, shrinkA=0, shrinkB=0))
    b.text(921 - av / 2, 1.5, f"{av:.0f} counts = travel in one $T_{{pub}}$", ha="center", va="bottom",
           fontsize=6.5, color=TINTA2)
    b.set_yticks([0, 1], ["$v$ = 25", "$v$ = 1000"])
    b.set_ylim(-0.5, 1.95)
    b.set_xlabel("detected onset position, POS_ACT (counts)")
    b.grid(axis="y", visible=False)
    b.tick_params(axis="y", length=0)
    letra(b, "(b)")
    guardar(fig, "Figure_4")


# ── Fig. 5: sobreimpulso, rejilla y modo B ────────────────────────────────
def Figure_5():
    fig = plt.figure(figsize=(PAG, 2.45), constrained_layout=True)
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.05])
    cmap = LinearSegmentedColormap.from_list("seq", ["#f2f1fb", "#b9b2e3", "#7b6ec9", "#4a3aa7", "#241a63"])
    S = R["sobreimpulso"]
    speeds = [25, 50, 100, 250, 500, 750, 1000]
    fsets = [100, 250, 500, 750, 1000]
    vmax = np.log10(36)
    for j, (dedo, tit) in enumerate((("middle", "(a) Middle finger"), ("thumb", "(b) Thumb"))):
        ax = fig.add_subplot(gs[0, j])
        M = np.full((len(speeds), len(fsets)), np.nan)
        for i, v in enumerate(speeds):
            for k, F in enumerate(fsets):
                e = S[dedo]["celdas"].get(f"{v}_{F}")
                if e:
                    M[i, k] = e["mediana"] * G2N
        im = ax.imshow(np.log10(np.clip(M, 0.1, None)), cmap=cmap, vmin=-1, vmax=vmax, aspect="auto",
                       origin="lower")
        for i, v in enumerate(speeds):
            for k, F in enumerate(fsets):
                e = S[dedo]["celdas"].get(f"{v}_{F}")
                if not e:
                    continue
                val = e["mediana"] * G2N
                txt = (r"$\geq$" if e["cota_inferior"] else "") + (f"{val:.1f}" if val < 10 else f"{val:.0f}")
                oscuro = np.log10(max(val, 0.1)) > 0.6
                ax.text(k, i, txt, ha="center", va="center", fontsize=5.6,
                        color="white" if oscuro else TINTA)
                if e["abortos"]:
                    ax.plot(k + 0.36, i + 0.3, marker="o", ms=1.6, color="white" if oscuro else TINTA, mew=0)
        ax.set_xticks(range(len(fsets)), [f"{F * G2N:.2f}".rstrip("0").rstrip(".") for F in fsets])
        ax.set_yticks(range(len(speeds)), [str(v) for v in speeds])
        ax.set_xlabel(r"threshold $F_{th}$ (N)")
        if j == 0:
            ax.set_ylabel("speed command $v$")
        ax.grid(False)
        for s in ax.spines.values():
            s.set_visible(False)
        ax.tick_params(length=0)
        letra(ax, tit)
    ax = fig.add_subplot(gs[0, 2])
    B = R["modo_b"]
    x = np.arange(len(fsets))
    for dedo, col, dx, lab in (("middle", MEDIO, -0.12, "middle"), ("thumb", PULGAR, 0.12, "thumb")):
        for k, F in enumerate(fsets):
            e = B[dedo][str(F)]
            a_, b_ = e["modoA_v1000"] * G2N, e["mediana"] * G2N
            ax.plot([k + dx, k + dx], [b_, a_], color=col, lw=0.8, alpha=0.6)
            ax.plot(k + dx, b_, "o", ms=3.4, color=col, mec="white", mew=0.5)
            ax.plot(k + dx, a_, "^" if e["razon_cota_inferior"] else "s", ms=3.4, mfc="white", mec=col, mew=0.8)
        ax.plot([], [], "o", ms=3.4, color=col, label=f"{lab}, Mode B")
    ax.plot([], [], "s", ms=3.4, mfc="white", mec=TINTA2, mew=0.8, label="Mode A, $v$ = 1000")
    ax.plot([], [], "^", ms=3.4, mfc="white", mec=TINTA2, mew=0.8, label="lower bound (ceiling)")
    ax.set_yscale("log")
    ax.set_ylim(0.08, 400)
    ax.set_yticks([0.1, 1, 10], ["0.1", "1", "10"])
    ax.minorticks_off()
    ax.set_xticks(x, [f"{F * G2N:.2f}".rstrip("0").rstrip(".") for F in fsets])
    ax.set_xlabel(r"threshold $F_{th}$ (N)")
    ax.set_ylabel(r"overshoot $\Delta F$ (N)")
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper center", ncol=2, columnspacing=0.8, handletextpad=0.3, borderaxespad=0.0)
    letra(ax, "(c) Mode A vs Mode B")
    guardar(fig, "Figure_5")


# ── Fig. 6: restricciones en contacto sostenido ───────────────────────────
def Figure_6():
    fig = plt.figure(figsize=(PAG, 2.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 3, width_ratios=[1, 1.15, 1], height_ratios=[1, 0.62])
    # (a) cuanto de fuerza del escalón mínimo fiable
    ax = fig.add_subplot(gs[:, 0])
    P = R["contacto"]["paso_minimo"]
    dedos = (("thumb", PULGAR), ("index", INDICE), ("middle", MEDIO))
    for i, (d, col) in enumerate(dedos):
        for j, F0 in enumerate((250, 1000)):
            m = P[f"{d}_F{F0}"]["minimo"]
            for s, mk in (("cerrar", "o"), ("abrir", "D")):
                if s in m:
                    y = m[s]["cuanto_g"] * G2N
                    xx = i + (j - 0.5) * 0.36 + (0.06 if s == "abrir" else -0.06)
                    ax.plot(xx, y, mk, ms=3.6, color=col if F0 == 250 else "white", mec=col, mew=0.9)
    ax.plot([], [], "o", ms=3.6, color=TINTA2, label="filled: $F_0$ = 2.45 N")
    ax.plot([], [], "o", ms=3.6, color="white", mec=TINTA2, mew=0.9, label="open: $F_0$ = 9.81 N")
    ax.plot([], [], "o", ms=3.6, color=TINTA2, label="circle: closing step")
    ax.plot([], [], "D", ms=3.2, color=TINTA2, label="diamond: opening step")
    ax.set_xticks(range(3), [d for d, _ in dedos])
    ax.set_ylabel("force change of the minimum\nreliable step (N)")
    ax.set_ylim(0, 2.5)
    ax.grid(axis="x", visible=False)
    ax.legend(loc="upper left", handletextpad=0.3, borderaxespad=0.1)
    letra(ax, "(a)")
    # (b) sostenimiento de 60 s con el comando congelado
    ax = fig.add_subplot(gs[:, 1])
    for d, dof, col in (("index", 3, INDICE), ("thumb", 4, PULGAR)):
        cyc = {}
        for r in csv.DictReader(open(EXP3 / f"e345_dof{dof}_F450_holds.csv")):
            if r["phase"] == "hold" and r["force_g"]:
                cyc.setdefault(r["cycle"], []).append((float(r["t_s"]), float(r["force_g"])))
        grid = np.linspace(0, 60, 241)
        curvas = []
        for s in cyc.values():
            t = np.array([x[0] for x in s]); F = np.array([x[1] for x in s])
            t = t - t[0]
            y = np.interp(grid, t, F) / np.median(F[t <= 1.0])
            curvas.append(y)
            ax.plot(grid, y, color=col, lw=0.4, alpha=0.35)
        ax.plot(grid, np.median(curvas, 0), color=col, lw=1.3, label=d)
    ax.set_xlim(0, 60)
    ax.set_ylim(0.75, 1.04)
    ax.set_xlabel("time with frozen command (s)")
    ax.set_ylabel(r"$F/F_{start}$, $F_{start}\approx$ 4.41 N")
    ax.legend(loc="lower left", handlelength=1.4)
    ax.text(59, 1.02, "motor current 0 mA in all 34 holds", ha="right", fontsize=6.2, color=TINTA2)
    letra(ax, "(b)")
    # (c) el pulgar sujeta ~9.9 N y la transmisión resbala
    s = leer(EXP3 / "techo_dof4_cubo.csv", ["t_s", "force4", "pos"])
    a1 = fig.add_subplot(gs[0, 2])
    a2 = fig.add_subplot(gs[1, 2], sharex=a1)
    a1.plot(s["t_s"], s["force4"] * G2N, color=PULGAR, lw=1.0)
    a2.plot(s["t_s"], s["pos"], color=TINTA2, lw=1.0)
    a1.set_ylabel("force (N)")
    a2.set_ylabel("POS_ACT")
    a2.set_xlabel("time (s)")
    a1.set_xlim(0, 8)
    a1.tick_params(labelbottom=False)
    a1.text(7.8, 8.6, "frozen command", ha="right", fontsize=6.2, color=TINTA2)
    letra(a1, "(c)")
    guardar(fig, "Figure_6")


# ── trazas de las tandas del regulador ────────────────────────────────────
def _tandas(bitacora, indice):
    t, f, c = lee_bitacora(CTRL / "data" / bitacora, 4)
    br = lee_brazos(CTRL / "data" / indice)
    out = []
    for (a, b), arm in zip(trials(t, 1.5), br):
        out.append((arm, np.array(t[a:b]) - t[a], np.array(f[a:b], float), np.array(c[a:b], float)))
    return out


def Figure_7():
    fig, axs = figura(PAG, 2.0, ncols=3, gridspec_kw={"width_ratios": [1.15, 1.25, 0.75]})
    tr = _tandas("a1_comparar_20260919_191452.csv", "a2_intercalado_dof4_F250.csv")
    ref = 250 * G2N
    for arm, t, F, c in tr:
        i_cmd = int(np.argmax(c < c[0]))
        i_on = i_cmd + int(np.argmax(F[i_cmd:] >= 150)) if arm == "lazo" else i_cmd
        col = LAZO if arm == "lazo" else FW
        w = (t >= t[i_on] - 0.2) & (t <= t[i_on] + 3.0)
        axs[0].plot(t[w] - t[i_on], F[w] * G2N, color=col, lw=0.6, alpha=0.7, drawstyle="steps-post")
        fin = len(t)
        previa = np.concatenate([np.full(60, np.inf), F[:-60]])      # ~0.2 s antes
        caida = np.nonzero((t > t[i_on] + 2) & (F < 0.85 * previa))[0]   # la mano abre al terminar
        if len(caida):
            fin = caida[0]
        w = (t >= t[i_on]) & (np.arange(len(t)) < fin)
        axs[1].plot(t[w] - t[i_on], F[w] * G2N, color=col, lw=0.5, alpha=0.6, drawstyle="steps-post")
    for ax in axs[:2]:
        ax.axhline(ref, color=TINTA2, lw=0.6, ls=(0, (3, 2)))
    axs[0].axhspan(ref - 0.294, ref + 0.294, color=LAZO, alpha=0.08, lw=0)
    axs[0].set_xlim(-0.2, 3)
    axs[0].set_ylim(0, 3.0)
    axs[0].set_xlabel("time from hand-over (s)")
    axs[0].set_ylabel("thumb force (N)")
    axs[0].plot([], [], color=LAZO, label="outer loop")
    axs[0].plot([], [], color=FW, label="firmware threshold")
    axs[0].legend(loc="lower right", handlelength=1.4)
    letra(axs[0], "(a) Contact transient")
    axs[1].set_xlim(0, 60)
    axs[1].set_ylim(1.9, 2.8)
    axs[1].axvspan(45, 60, color=TINTA2, alpha=0.07, lw=0)
    axs[1].text(52.5, 2.74, "steady-state\nwindow", ha="center", va="top", fontsize=6.2, color=TINTA2)
    axs[1].set_xlabel("time from hand-over (s)")
    letra(axs[1], "(b) 60 s hold")
    idx = list(csv.DictReader(open(CTRL / "data" / "a2_intercalado_dof4_F250.csv")))
    rng = np.random.default_rng(7)
    for i, (arm, col) in enumerate((("firmware", FW), ("lazo", LAZO))):
        v = np.array([abs(float(r["err_reg"])) for r in idx if r["brazo"] == arm]) * G2N
        afect = np.array([r["n"] == "10" for r in idx if r["brazo"] == arm])
        xx = i + rng.uniform(-0.13, 0.13, len(v))
        axs[2].plot(xx[~afect], v[~afect], "o", ms=3.2, color=col, mec="white", mew=0.5)
        axs[2].plot(xx[afect], v[afect], "o", ms=3.2, mfc="white", mec=col, mew=0.8)
        axs[2].plot([i - 0.28, i + 0.28], [np.median(v)] * 2, color=TINTA, lw=1.2)
    axs[2].set_xticks([0, 1], ["firmware", "outer\nloop"])
    axs[2].set_xlim(-0.55, 1.55)
    axs[2].set_ylim(0, 0.4)
    axs[2].set_ylabel(r"$|e_{ss}|$ (N)")
    axs[2].grid(axis="x", visible=False)
    letra(axs[2], "(c)")
    guardar(fig, "Figure_7")


def Figure_8():
    fig, axs = figura(PAG, 1.95, ncols=3, sharey=False, gridspec_kw={"width_ratios": [1.1, 1.1, 0.75]})
    idx = list(csv.DictReader(open(CTRL / "data" / "a2_intercalado_dof4_F250_pert32.csv")))
    d = leer(CTRL / "data" / "a1_comparar_20260921_115652.csv", ["t", "F_T", "cmd_I"])
    t, f, c = d["t"], d["F_T"], d["cmd_I"]
    pasos = np.nonzero((c[:-1] >= 945) & (c[:-1] <= 955) & (c[1:] == 918))[0] + 1
    rejilla = np.linspace(-8, 34, 421)
    afect = {int(r["n"]) for r in idx if r["tarado"] != "si" or int(r["n_muestras"]) < 20000}
    for ax, (arm, col, tit) in zip(axs, (("firmware", FW, "(a) Firmware threshold"),
                                          ("lazo", LAZO, "(b) Outer loop"))):
        curvas = []
        for k, r in zip(pasos, idx):
            if r["brazo"] != arm or int(r["n"]) in afect:
                continue
            tt = t - t[k]
            w = (tt >= -9) & (tt <= 35)
            y = np.interp(rejilla, tt[w], f[w]) * G2N
            curvas.append(y)
            ax.plot(rejilla, y, color=col, lw=0.5, alpha=0.55)
        ax.plot(rejilla, np.median(curvas, 0), color=TINTA, lw=1.1)
        ax.axvline(0, color=TINTA2, lw=0.6)
        ax.axhline(250 * G2N, color=TINTA2, lw=0.6, ls=(0, (3, 2)))
        ax.axvspan(20, 35, color=TINTA2, alpha=0.07, lw=0)
        ax.set_xlim(-8, 35)
        ax.set_ylim(1.8, 3.6)
        ax.set_xlabel(r"time from support step $t_p$ (s)")
        letra(ax, tit)
    axs[0].set_ylabel("thumb force (N)")
    axs[1].tick_params(labelleft=False)
    rng = np.random.default_rng(7)
    for i, (arm, col) in enumerate((("firmware", FW), ("lazo", LAZO))):
        # el trial truncado antes de su ventana de régimen no tiene residual
        rr = [r for r in idx if r["brazo"] == arm and int(r["n_muestras"]) >= 20000]
        v = np.array([abs(float(r["resid"])) for r in rr]) * G2N
        af = np.array([int(r["n"]) in afect for r in rr])
        xx = i + rng.uniform(-0.13, 0.13, len(v))
        axs[2].plot(xx[~af], v[~af], "o", ms=3.2, color=col, mec="white", mew=0.5)
        axs[2].plot(xx[af], v[af], "o", ms=3.2, mfc="white", mec=col, mew=0.8)
        axs[2].plot([i - 0.28, i + 0.28], [np.median(v[~af])] * 2, color=TINTA, lw=1.2)
    axs[2].set_xticks([0, 1], ["firmware", "outer\nloop"])
    axs[2].set_xlim(-0.55, 1.55)
    axs[2].set_ylim(0, 1.0)
    axs[2].set_ylabel(r"$|R|$ (N)")
    axs[2].grid(axis="x", visible=False)
    letra(axs[2], "(c)")
    guardar(fig, "Figure_8")


if __name__ == "__main__":
    todas = [Figure_4, Figure_5, Figure_6, Figure_7, Figure_8]
    pedidas = set(sys.argv[1:])
    for fn in todas:
        if not pedidas or fn.__name__ in pedidas:
            fn()
