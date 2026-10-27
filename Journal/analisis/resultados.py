#!/usr/bin/env python3
"""Regenera, desde los archivos crudos, todas las cifras de la sección Results del
artículo para *Mechatronics*.

Uso:  .venv/bin/python Journal/analisis/resultados.py      (desde la raíz del repo)

Escribe `Journal/analisis/resultados.json` y un resumen legible por pantalla. Cada
bloque lee los CSV de trial o los índices que escribieron los scripts de captura;
ningún número se copia de las notas de resultados. Donde un índice ya resume un
trial (p. ej. `grid_index.csv`), se usa ese resumen, que el script de captura
calculó sobre la traza cruda en el momento.

Estadística (Sección 6.3 del manuscrito):
  - diferencia de medianas entre brazos;
  - p de permutación a dos colas, 20 000 reetiquetados al azar (semilla 0);
  - prueba exacta que solo intercambia etiquetas dentro de cada bloque;
  - IC 95 % por bootstrap percentil, 10 000 remuestreos dentro de cada brazo.
"""
from __future__ import annotations

import csv
import itertools
import json
import statistics as st
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
CAR = REPO / "Caracterizacion"
CTRL = REPO / "Control"
EXP2 = CAR / "exp2"
EXP3 = CAR / "exp3" / "data"
sys.path.insert(0, str(EXP2))
sys.path.insert(0, str(CTRL))
import exp2_analyze as e2  # noqa: E402
from a2_hipotesis import analiza_trial, lee_bitacora, lee_brazos, trials  # noqa: E402

G2N = 9.80665e-3
RES = {}


# ── estadística ───────────────────────────────────────────────────────────
def med(v):
    return float(np.median(v)) if len(v) else None


def iqr(v):
    return [float(np.percentile(v, 25)), float(np.percentile(v, 75))] if len(v) else None


def perm_p(a, b, n=20000, seed=0):
    """p a dos colas de |med(a) − med(b)| por reetiquetado al azar."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    obs = abs(np.median(a) - np.median(b))
    todo = np.concatenate([a, b])
    rng = np.random.default_rng(seed)
    cnt = 0
    for _ in range(n):
        rng.shuffle(todo)
        if abs(np.median(todo[:len(a)]) - np.median(todo[len(a):])) >= obs - 1e-12:
            cnt += 1
    return (cnt + 1) / (n + 1)


def perm_bloques(pares):
    """p exacta intercambiando etiquetas solo dentro de cada bloque.
    pares: lista de (valor_brazo_a, valor_brazo_b), un par por bloque completo."""
    a = np.array([p[0] for p in pares], float)
    b = np.array([p[1] for p in pares], float)
    obs = abs(np.median(a) - np.median(b))
    cnt = tot = 0
    for sw in itertools.product((0, 1), repeat=len(pares)):
        s = np.array(sw, bool)
        aa = np.where(s, b, a); bb = np.where(s, a, b)
        cnt += abs(np.median(aa) - np.median(bb)) >= obs - 1e-12
        tot += 1
    return cnt / tot


def boot_ci(a, b, n=10000, seed=1):
    """IC 95 % de med(b) − med(a), remuestreando dentro de cada brazo."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    d = np.median(rng.choice(b, (n, len(b))), 1) - np.median(rng.choice(a, (n, len(a))), 1)
    return [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]


def boot_ratio(a, b, n=10000, seed=1):
    """IC 95 % de med(a) / med(b)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    rng = np.random.default_rng(seed)
    r = np.median(rng.choice(a, (n, len(a))), 1) / np.median(rng.choice(b, (n, len(b))), 1)
    return [float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))]


def resumen(v):
    v = list(v)
    return dict(n=len(v), mediana=med(v), iqr=iqr(v), min=float(min(v)), max=float(max(v)))


def comparar(fw, lz, pares=None):
    """Bloque completo de una comparación de dos brazos (fw → lazo)."""
    out = dict(firmware=resumen(fw), lazo=resumen(lz),
               dif_medianas=med(lz) - med(fw), ic95=boot_ci(fw, lz), p_perm=perm_p(fw, lz))
    if pares:
        out["p_bloques"] = perm_bloques(pares)
        out["n_bloques"] = len(pares)
    return out


# ── utilidades de series ──────────────────────────────────────────────────
def leer(path, cols):
    out = {c: [] for c in cols}
    with open(path) as fh:
        for r in csv.DictReader(fh):
            for c in cols:
                v = r.get(c, "")
                out[c].append(float(v) if v not in ("", None) else np.nan)
    return {c: np.array(v) for c, v in out.items()}


def intervalos_cambio(t, x):
    """Intervalos entre cambios consecutivos del valor publicado (ignora huecos)."""
    m = ~np.isnan(x)
    t, x = t[m], x[m]
    idx = np.nonzero(np.diff(x) != 0)[0] + 1
    return np.diff(t[idx])


def periodo_base(dt):
    """Periodo de publicación: mediana de los intervalos cortos (≤1.5×mediana), y
    fracción de todos los intervalos a ±15 % de un múltiplo entero."""
    dt = np.asarray(dt)
    corto = dt[dt <= 1.5 * np.median(dt)]
    T = float(np.median(corto))
    k = np.maximum(np.round(dt / T), 1)
    frac = float(np.mean(np.abs(dt / k - T) <= 0.15 * T))
    return T, frac


# ── 7.1 temporización ─────────────────────────────────────────────────────
def temporizacion():
    out = {}
    for v in (25, 1000):
        d = EXP2 / f"data_dof4_tcp_bif_v{v}"
        dq, dpos, dfor, dcur, avance = [], [], [], [], []
        onset = {int(r["trial"]): int(r["onset_pos"]) for r in csv.DictReader(open(d / "onset_trials.csv"))
                 if r["onset_pos"] not in ("", None)}
        for f in sorted(d.glob("trace_*.csv")):
            s = leer(f, ["t_s", "pos_act", "force_g", "current_mA"])
            t = s["t_s"]
            dq += list(np.diff(t))
            dpos += list(intervalos_cambio(t, s["pos_act"]))
            dfor += list(intervalos_cambio(t, s["force_g"]))
            dcur += list(intervalos_cambio(t, s["current_mA"]))
            n = int(f.stem.split("_n")[-1])
            if n in onset:   # avance de POS por refresco en los 200 counts previos al onset
                p = s["pos_act"][~np.isnan(s["pos_act"])]
                ch = p[np.nonzero(np.diff(p) != 0)[0] + 1]
                saltos = np.diff(ch)
                ini = ch[:-1]
                sel = (ini >= onset[n] - 200) & (ini < onset[n]) & (saltos > 0)
                avance += list(saltos[sel])
        ons = np.array(list(onset.values()))
        bloque = {}
        for nom, dt in (("pos", dpos), ("force", dfor), ("current", dcur)):
            if len(dt) < 10:
                continue
            T, frac = periodo_base(dt)
            dt = np.asarray(dt)
            bloque[nom] = dict(n=len(dt), mediana_ms=1e3 * float(np.median(dt)), T_ms=1e3 * T,
                               frac_multiplos=frac,
                               p5_ms=1e3 * float(np.percentile(dt, 5)),
                               p95_ms=1e3 * float(np.percentile(dt, 95)))
        out[f"v{v}"] = dict(f_query_hz=1 / float(np.median(dq)), dt_query_ms=1e3 * float(np.median(dq)),
                            n_toques=len(ons), onset_sd=float(np.std(ons, ddof=1)),
                            onset_rango=[int(ons.min()), int(ons.max())],
                            avance_por_refresco=med(avance), registros=bloque)
        if v == 1000:   # estructura en dos escalones
            o = np.sort(ons)
            g = np.diff(o)
            out[f"v{v}"]["hueco_max_counts"] = int(g.max())
            corte = o[np.argmax(g)]
            out[f"v{v}"]["grupos"] = [int((o <= corte).sum()), int((o > corte).sum())]
    # con carga y sin carga, en el software del regulador
    s = leer(CTRL / "data" / "a1_resbalon_20260919_170522.csv", ["t", "F_T"])
    m = s["F_T"] > 300
    dt = intervalos_cambio(s["t"][m], s["F_T"][m])
    out["carga"] = dict(rango_g=[float(np.nanmin(s["F_T"][m])), float(np.nanmax(s["F_T"][m]))],
                        mediana_ms=1e3 * float(np.median(dt)), tasa_hz=1 / float(np.median(dt)),
                        cambios_hz=len(dt) / float(s["t"][m][-1] - s["t"][m][0]))
    s = leer(CTRL / "data" / "a1_tasas_20260919_170852.csv", ["t", "F_T", "F_I"])
    dtv = list(intervalos_cambio(s["t"], s["F_T"])) + list(intervalos_cambio(s["t"], s["F_I"]))
    out["vacio"] = dict(mediana_ms=1e3 * float(np.median(dtv)))
    # desfase entre actuadores: pulgar (4) e índice (3) cerrando juntos sobre la bola
    lags = []
    for f in ("e36_modo1_bola_grasp_log.csv", "e36_modo1_bola2_grasp_log.csv"):
        s = leer(EXP3 / f, ["t_s", "pos3", "pos4"])
        t = s["t_s"]
        def cambios(x):
            m = ~np.isnan(x)
            tt, xx = t[m], x[m]
            return tt[np.nonzero(np.diff(xx) != 0)[0] + 1]
        ti, tp = cambios(s["pos3"]), cambios(s["pos4"])
        if len(ti) < 5 or len(tp) < 5:
            continue
        T = periodo_base(np.diff(tp))[0]
        for x in ti:
            j = np.argmin(np.abs(tp - x))
            d = x - tp[j]
            if abs(d) <= T / 2:
                lags.append(d)
        dq = np.diff(t)
    lags = np.array(lags)
    out["desfase_indice_pulgar"] = dict(n=len(lags), mediana_ms=1e3 * float(np.median(lags)),
                                        cuartiles_ms=[1e3 * float(np.percentile(lags, 25)),
                                                      1e3 * float(np.percentile(lags, 75))],
                                        periodo_lectura_ms=1e3 * float(np.median(dq)))
    # tasa de control: el disparador (cambio de valor o 40 ms) sobre los trials del lazo de A2
    t, f, c = lee_bitacora(CTRL / "data" / "a1_comparar_20260919_191452.csv", 4)
    brazos = lee_brazos(CTRL / "data" / "a2_intercalado_dof4_F250.csv")
    disp = plazo = dur = 0.0
    for (a, b), br in zip(trials(t, 1.5), brazos):
        if br != "lazo":
            continue
        tt, ff = np.array(t[a:b]), np.array(f[a:b])
        tu, fu = tt[0], ff[0]
        for ti, fi in zip(tt[1:], ff[1:]):
            if fi != fu or ti - tu >= 0.040:
                disp += 1; plazo += fi == fu
                tu, fu = ti, fi
        dur += tt[-1] - tt[0]
    out["control"] = dict(f_control_hz=disp / dur, frac_por_plazo=plazo / disp)
    RES["temporizacion"] = out


# ── 7.2 movimiento libre ──────────────────────────────────────────────────
DEDOS = {0: ("little", "data_dof0_tcp"), 1: ("ring", "data_dof1_tcp"), 2: ("middle", "data_dof2_tcp"),
         3: ("index", "data_tcp"), 4: ("thumb", "data_dof4_tcp")}


def movimiento_libre():
    out = {}
    for dof, (nom, d) in DEDOS.items():
        rows = list(csv.DictReader(open(CAR / "exp1" / d / "analysis_per_trial.csv")))
        v = np.array([float(r["speed"]) for r in rows])
        sl = np.array([float(r["slope_cps"]) if r["slope_cps"] else np.nan for r in rows])
        lb = np.array([float(r["L_band_ms"]) if r["L_band_ms"] else np.nan for r in rows])
        le = np.array([float(r["L_extrap_ms"]) if r["L_extrap_ms"] else np.nan for r in rows])
        r2 = np.array([float(r["r2"]) if r["r2"] else np.nan for r in rows])
        os_ = np.array([float(r["overshoot_pct"]) if r["overshoot_pct"] else np.nan for r in rows])
        m = (v <= 500) & ~np.isnan(sl)
        k = float(np.sum(v[m] * sl[m]) / np.sum(v[m] ** 2))
        speeds = sorted(set(v))
        out[nom] = dict(dof=dof, n=len(rows), velocidades=[int(x) for x in speeds], k=k,
                        L_mediana_ms=float(np.nanmedian(lb)), L_iqr_ms=[float(np.nanpercentile(lb, 25)),
                                                                        float(np.nanpercentile(lb, 75))],
                        L_extrap_por_v={int(s): float(np.nanmedian(le[v == s])) for s in speeds},
                        r2_min_v500=float(np.nanmin(r2[m])), sobreimpulso_max_pct=float(np.nanmax(os_)))
    ks = [x["k"] for x in out.values()]
    RES["movimiento_libre"] = dict(por_dedo=out, k_rango=[min(ks), max(ks)])


# ── 7.3 sobreimpulso a velocidad constante (modo A) ───────────────────────
def filas_validas(d):
    rows = e2.load(d)
    rows, _ = e2.drop_no_load(rows, 30)
    rows, _ = e2.drop_contactless(rows)
    rows, glitch = e2.drop_glitches(rows, d)
    return rows, len(glitch)


def celdas(rows):
    out = {}
    for r in rows:
        k = (r["speed"], r["fset"])
        out.setdefault(k, []).append(r)
    return out


def sobreimpulso():
    out = {}
    for dof, nom, d in ((2, "middle", "data_dof2_tcp"), (4, "thumb", "data_dof4_tcp"),
                        (1, "ring", "data_dof1_tcp")):
        rows, nglitch = filas_validas(EXP2 / d)
        rows = [r for r in rows if r["trial_file"].startswith("A_")]
        cs = celdas(rows)
        grid = {}
        for (v, F), rr in sorted(cs.items()):
            df = [r["delta_f"] for r in rr]
            nab = sum(r["aborted"] for r in rr)
            grid[f"{v}_{F}"] = dict(v=v, F=F, n=len(rr), mediana=med(df), iqr=iqr(df),
                                    abortos=nab, cota_inferior=nab * 2 >= len(rr),
                                    trials=[float(x) for x in df])
        out[nom] = dict(n=len(rows), abortos=sum(r["aborted"] for r in rows), descartes_glitch=nglitch,
                        celdas=grid)
    RES["sobreimpulso"] = out


# ── 7.4 aproximación rápida y contacto lento (modo B) ─────────────────────
def modo_b():
    out = {}
    T_pub = RES["temporizacion"]["v1000"]["registros"]["pos"]["T_ms"] / 1e3
    k = RES["movimiento_libre"]["por_dedo"]["thumb"]["k"]
    for dof, nom, dA, dB in ((2, "middle", "data_dof2_tcp", "data_dof2_tcp_hybrid"),
                             (4, "thumb", "data_dof4_tcp", "data_dof4_tcp_hybrid"),
                             (1, "ring", "data_dof1_tcp", "data_dof1_tcp_hybrid"),
                             (0, "little", None, "data_dof0_tcp_hybrid")):
        rB, _ = filas_validas(EXP2 / dB)
        cB = celdas(rB)
        cA = celdas(filas_validas(EXP2 / dA)[0]) if dA else {}
        por_F = {}
        for (v, F), rr in sorted(cB.items()):
            b = [r["delta_f"] for r in rr]
            ent = dict(n=len(b), mediana=med(b), rango=[float(min(b)), float(max(b))],
                       abortos=sum(r["aborted"] for r in rr))
            a = cA.get((1000, F))
            if a:
                av = [r["delta_f"] for r in a]
                nab = sum(r["aborted"] for r in a)
                ent.update(modoA_v1000=med(av), modoA_abortos=nab, razon=med(av) / med(b),
                           razon_ic95=boot_ratio(av, b), razon_cota_inferior=nab * 2 >= len(a))
            por_F[str(F)] = ent
        out[nom] = por_F
    # comparación intercalada en el anular: cierre lento (A, v=25) frente a modo B
    inter = {}
    for pose, d in (("edge", "data_dof1_tcp_ab_borde"), ("flat", "data_dof1_tcp_ab")):
        rows = list(csv.DictReader(open(EXP2 / d / "ab_index.csv")))
        A = [float(r["delta_f"]) for r in rows if r["policy"] == "A" and r["aborted"] == "0"]
        B = [float(r["delta_f"]) for r in rows if r["policy"] == "B" and r["aborted"] == "0"]
        inter[pose] = comparar(A, B)
    out["anular_intercalado"] = inter
    out["avance_por_publicacion_v1000_counts"] = k * 1000 * T_pub
    RES["modo_b"] = out


# ── 7.5 contacto sostenido ────────────────────────────────────────────────
def contacto():
    out = {}
    pasos = {}
    for dof, nom in ((4, "thumb"), (3, "index"), (2, "middle")):
        for F0 in (250, 1000):
            f = EXP3 / f"e32_dof{dof}_F{F0}.csv"
            if not f.exists():
                continue
            rows = [r for r in csv.DictReader(open(f)) if r["aborted"] == "0"]
            tab = {}
            for sentido in ("cerrar", "abrir"):
                for u in (1, 2, 3, 5, 10):
                    rr = [r for r in rows if r["dir"] == sentido and int(r["step_units"]) == u]
                    if not rr:
                        continue
                    movio = sum(abs(float(r["dpos"])) > 0 for r in rr)
                    tab[f"{sentido}_{u}"] = dict(n=len(rr), movio=movio,
                                                 df_mediana=med([float(r["df"]) for r in rr]))
            minimo = {}
            for sentido in ("cerrar", "abrir"):
                for u in (1, 2, 3, 5, 10):
                    e = tab.get(f"{sentido}_{u}")
                    if e and e["movio"] >= 0.9 * e["n"]:
                        minimo[sentido] = dict(paso=u, cuanto_g=abs(e["df_mediana"]))
                        break
            pasos[f"{nom}_F{F0}"] = dict(tabla=tab, minimo=minimo)
    out["paso_minimo"] = pasos
    # rigidez local: ajuste de ΔF frente a ΔPOS por el origen, escalones de ≤ 5 unidades
    kloc = {}
    for dof, nom in ((4, "thumb"), (3, "index"), (2, "middle")):
        for F0 in (250, 500, 1000):
            f = EXP3 / f"e32_dof{dof}_F{F0}.csv"
            if not f.exists():
                continue
            rows = [r for r in csv.DictReader(open(f)) if r["aborted"] == "0" and int(r["step_units"]) <= 5]
            for sentido in ("cerrar", "abrir"):
                rr = [r for r in rows if r["dir"] == sentido]
                dp = np.array([float(r["dpos"]) for r in rr]); df = np.array([float(r["df"]) for r in rr])
                if len(dp) and np.sum(dp ** 2) > 0:
                    kloc[f"{nom}_F{F0}_{sentido}"] = float(np.sum(dp * df) / np.sum(dp ** 2))
    out["k_local_g_por_count"] = kloc
    # planta en contacto (E3.3): retardo, constante de tiempo, asentamiento
    planta = {}
    # celdas limpias (E3.3): 250 g en los dos sentidos y 450 g abriendo; cerrando a
    # 450 g el punto de operación se desplaza durante el escalón y no da un retardo limpio
    for nom, sel in (("index", [("e33_dof3_F250.csv", ("cerrar", "abrir")), ("e33_dof3_F450.csv", ("abrir",))]),
                     ("thumb", [("e33_dof4_F250.csv", ("cerrar", "abrir"))])):
        rows = []
        for f, dirs in sel:
            rows += [r for r in csv.DictReader(open(EXP3 / f))
                     if r["aborted"] == "0" and r["t_onset_ms"] and r["dir"] in dirs]
        L = [float(r["t_onset_ms"]) for r in rows]
        tau = [float(r["tau_ms"]) for r in rows if r["tau_ms"] and float(r["tau_ms"]) > 0]
        ts = [float(r["t_settle_ms"]) for r in rows if r["t_settle_ms"]]
        planta[nom] = dict(n=len(rows), L_ms=med(L), L_iqr=iqr(L), tau_ms=med(tau), tau_iqr=iqr(tau),
                           settle_ms=med(ts), L_sobre_tau=med(L) / med(tau) if tau else None)
    out["planta"] = planta
    # colapso al intentar sostener ~1000 g (E3.3, trazas)
    colapso = {}
    # en el archivo de trazas cada (trial, paso, sentido) es un ensayo distinto, y el
    # tiempo se reinicia en cada fase: se respeta el orden del archivo
    for nom, f in (("index", "e33_dof3_F1000_traces.csv"), ("thumb", "e33_dof4_F1000_traces.csv")):
        tr = {}
        for r in csv.DictReader(open(EXP3 / f)):
            if r["force_g"]:
                tr.setdefault((r["trial"], r["step_units"], r["dir"]), []).append(
                    (r["phase"], float(r["t_s"]), float(r["force_g"])))
        ini, fin, t200 = [], [], []
        for s_ in tr.values():
            base = [x for x in s_ if x[0] == "base"]
            if not base or base[0][2] < 800:
                continue
            f0, t0 = base[0][2], base[0][1]
            ini.append(f0)
            fin.append(np.median([x[2] for x in s_[-20:]]))
            cae = [x[1] for x in base if x[2] < f0 - 200]
            if cae:
                t200.append(cae[0] - t0)
        colapso[nom] = dict(n=len(ini), f_inicial=med(ini), meseta=med(fin),
                            meseta_sd=float(np.std(fin, ddof=1)) if len(fin) > 1 else None,
                            t_hasta_perder_200g_s=med(t200), t200_rango=[min(t200), max(t200)] if t200 else None,
                            n_pierden_en_base=len(t200))
    out["colapso_1000"] = colapso
    # sostenimiento 60 s y deriva del cero (E3.4 + E3.5)
    sost = {}
    for nom, dof in (("index", 3), ("thumb", 4)):
        rows = [r for r in csv.DictReader(open(EXP3 / f"e345_dof{dof}_F450.csv")) if r["aborted"] == "0"]
        drop = [float(r["drop_g"]) for r in rows]
        frac = [float(r["drop_frac"]) for r in rows]
        t63 = [float(r["t63_s"]) for r in rows if r["t63_s"]]
        dpos = [float(r["dpos"]) for r in rows]
        cur = [float(r["cur_med"]) for r in rows]
        salto = [float(r["base_after_g"]) - float(r["base_before_g"]) for r in rows]
        base = [float(r["base_before_g"]) for r in rows]
        temp = [float(r["temp_before"]) for r in rows]
        sost[nom] = dict(ciclos=len(rows), caida_g=med(drop), caida_rango=[min(drop), max(drop)],
                         caida_frac=med(frac), t63_s=med(t63), dpos_mediana=med(dpos),
                         dpos_rango=[min(dpos), max(dpos)], corriente_max_mA=max(cur),
                         salto_cero_g=med(salto), salto_rango=[min(salto), max(salto)],
                         deriva_termica_g=base[-1] - base[0], temp_rango=[min(temp), max(temp)])
    # recuperación del cero tras soltar: pendiente de la base en los ~3 s posteriores (índice)
    for nom, dof in (("index", 3), ("thumb", 4)):
        pend = []
        cyc = {}
        for r in csv.DictReader(open(EXP3 / f"e345_dof{dof}_F450_holds.csv")):
            if r["phase"] == "base_post" and r["force_g"]:
                cyc.setdefault(r["cycle"], []).append((float(r["t_s"]), float(r["force_g"])))
        for c_ in cyc.values():
            t_ = np.array([x[0] for x in c_]); f_ = np.array([x[1] for x in c_])
            if t_[-1] - t_[0] > 1:
                pend.append(float(np.polyfit(t_ - t_[0], f_, 1)[0]))
        sost[nom]["recuperacion_g_s"] = med(pend)
    out["sostenimiento"] = sost
    # el pulgar sujetando el cubo: aguanta ~1000 g y resbala (techo de la transmisión)
    s = leer(EXP3 / "techo_dof4_cubo.csv", ["t_s", "force4", "pos"])
    t, F, P = s["t_s"], s["force4"], s["pos"]
    j = np.nonzero(F < F[0] - 200)[0][0]
    out["techo_pulgar_cubo"] = dict(f_inicial=float(F[0]), t_aguanta_s=float(t[j] - t[0]),
                                    retroceso_pos=float(P[0] - np.median(P[j:j + 200])),
                                    f_final=float(np.median(F[-500:])),
                                    deriva_final_g=float(np.median(F[-200:]) - np.median(F[j + 400:j + 600])))
    RES["contacto"] = out


# ── 7.6 y 7.7 regulador frente a firmware ─────────────────────────────────
def regulador():
    out = {}
    # sostenimiento (A2)
    idx = list(csv.DictReader(open(CTRL / "data" / "a2_intercalado_dof4_F250.csv")))
    afect = {10}            # trial truncado por un detector disparado por una muestra corrupta
    def col(rows, k, f=float):
        return [f(r[k]) for r in rows]

    def analisis(excluir):
        rr = [r for r in idx if int(r["n"]) not in excluir and r["pico"]]
        fw = [r for r in rr if r["brazo"] == "firmware"]
        lz = [r for r in rr if r["brazo"] == "lazo"]
        bloques = {}
        for r in rr:
            bloques.setdefault((int(r["n"]) - 1) // 2, {})[r["brazo"]] = r
        def pares(k, fn):
            return [(fn(b["firmware"][k]), fn(b["lazo"][k])) for b in bloques.values()
                    if "firmware" in b and "lazo" in b]
        absf = lambda x: abs(float(x))
        return dict(
            abs_ess=comparar([absf(r["err_reg"]) for r in fw], [absf(r["err_reg"]) for r in lz],
                             pares("err_reg", absf)),
            ess=comparar(col(fw, "err_reg"), col(lz, "err_reg"), pares("err_reg", float)),
            pico=comparar(col(fw, "pico"), col(lz, "pico"), pares("pico", float)),
            corriente=dict(firmware=resumen(col(fw, "I_med")), lazo=resumen(col(lz, "I_med"))),
            n=dict(firmware=len(fw), lazo=len(lz)))
    out["sostenimiento"] = dict(todos=analisis(set()), sin_afectados=analisis(afect),
                                temp_rango=[min(col(idx, "temp")), max(col(idx, "temp"))],
                                orden=[r["brazo"][0].upper() for r in idx])
    # exploratorio sobre la traza cruda: establecimiento, RMS, sobreimpulso
    class A:
        ref, banda, frac_aprox, filtro = 250.0, 30.0, 0.6, 31
    t, f, c = lee_bitacora(CTRL / "data" / "a1_comparar_20260919_191452.csv", 4)
    brazos = lee_brazos(CTRL / "data" / "a2_intercalado_dof4_F250.csv")
    ex = {"firmware": [], "lazo": []}
    for (a, b), br in zip(trials(t, 1.5), brazos):
        ex[br].append(analiza_trial(t[a:b], f[a:b], c[a:b], br, A))
    def lista(br, k):
        return [m[k] for m in ex[br] if m[k] is not None]
    # tiempo de adquisición del contacto en el brazo del lazo: del primer contacto
    # (fuerza 20 g sobre el reposo) a la toma de control (0.6 F*)
    adq = []
    for (a, b), br in zip(trials(t, 1.5), brazos):
        if br != "lazo":
            continue
        tt = np.array(t[a:b]) - t[a]; ff = np.array(f[a:b], float); cc = np.array(c[a:b], float)
        i_cmd = int(np.argmax(cc < cc[0]))
        reposo = np.median(ff[(tt > 1) & (tt < 3.5)])
        i_c = i_cmd + int(np.argmax(ff[i_cmd:] >= reposo + 20))
        i_on = i_cmd + int(np.argmax(ff[i_cmd:] >= 150))
        adq.append(float(tt[i_on] - tt[i_c]))
    out["adquisicion_s"] = resumen(adq)
    out["exploratorio"] = dict(
        establecimiento_s=dict(firmware=resumen(lista("firmware", "ts")), lazo=resumen(lista("lazo", "ts")),
                               entran=dict(firmware=len(lista("firmware", "ts")), lazo=len(lista("lazo", "ts")))),
        rms=comparar(lista("firmware", "rms"), lista("lazo", "rms")),
        sobreimpulso=comparar(lista("firmware", "sobre"), lista("lazo", "sobre")))
    # perturbación
    idx = list(csv.DictReader(open(CTRL / "data" / "a2_intercalado_dof4_F250_pert32.csv")))
    afect = {int(r["n"]) for r in idx if r["tarado"] != "si" or int(r["n_muestras"]) < 20000}
    # un trial truncado antes de su ventana de régimen (20–35 s tras t_p) no tiene residual:
    # queda fuera de los dos análisis; los demás afectados solo del segundo
    sin_ventana = {int(r["n"]) for r in idx if int(r["n_muestras"]) < 20000}

    def pert(excluir):
        rr = [r for r in idx if int(r["n"]) not in excluir and r["resid"]]
        fw = [r for r in rr if r["brazo"] == "firmware"]
        lz = [r for r in rr if r["brazo"] == "lazo"]
        Dfw = med(col(fw, "salto"))
        rho = lambda rows: [1 - abs(float(r["resid"])) / Dfw for r in rows]
        bloques = {}
        for r in rr:
            bloques.setdefault((int(r["n"]) - 1) // 2, {})[r["brazo"]] = r
        completos = [b for b in bloques.values() if "firmware" in b and "lazo" in b]
        pares = [(float(b["firmware"]["resid"]), float(b["lazo"]["resid"])) for b in completos]
        pares_abs = [(abs(a), abs(b)) for a, b in pares]
        pr = [(1 - a / Dfw, 1 - b / Dfw) for a, b in pares_abs]
        return dict(base=dict(firmware=resumen(col(fw, "f_base")), lazo=resumen(col(lz, "f_base"))),
                    excursion=dict(firmware=resumen(col(fw, "salto")), lazo=resumen(col(lz, "salto"))),
                    residual=comparar(col(fw, "resid"), col(lz, "resid"), pares),
                    residual_abs=comparar([abs(x) for x in col(fw, "resid")],
                                          [abs(x) for x in col(lz, "resid")], pares_abs),
                    rho=comparar(rho(fw), rho(lz), pr), D_fw_mediana=Dfw,
                    n=dict(firmware=len(fw), lazo=len(lz)))
    out["perturbacion"] = dict(afectados=sorted(afect), sin_ventana=sorted(sin_ventana),
                               todos=pert(sin_ventana), sin_afectados=pert(afect),
                               temp_rango=[min(col(idx, "temp")), max(col(idx, "temp"))])
    # deriva dentro de la tanda: correlación de Spearman entre el orden y el |error|
    def spearman(x, y):
        rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
        return float(np.corrcoef(rx, ry)[0, 1])
    idx2 = list(csv.DictReader(open(CTRL / "data" / "a2_intercalado_dof4_F250.csv")))
    out["deriva_orden"] = {br: spearman([int(r["n"]) for r in idx2 if r["brazo"] == br and r["err_reg"]],
                                        [abs(float(r["err_reg"])) for r in idx2 if r["brazo"] == br and r["err_reg"]])
                           for br in ("firmware", "lazo")}
    RES["regulador"] = out


def main():
    for paso in (temporizacion, movimiento_libre, sobreimpulso, modo_b, contacto, regulador):
        paso()
        print(f"✔ {paso.__name__}")
    dst = Path(__file__).with_name("resultados.json")
    dst.write_text(json.dumps(RES, indent=1, ensure_ascii=False, default=float))
    print(dst)


if __name__ == "__main__":
    main()
