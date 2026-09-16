#!/usr/bin/env python3
"""Arma el documento-resumen de la caracterización (HTML) embebiendo las figuras."""
import csv, json, os, re, statistics, sys

# La raíz de Caracterizacion/ es el nivel de ARRIBA: este script vive en una
# subcarpeta y todas las rutas de datos cuelgan de la raíz.
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DST=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 'RESUMEN_caracterizacion.html')

def svgs(path):
    return re.findall(r'<svg\b.*?</svg>', open(path).read(), re.S)

e1=svgs(os.path.join(RAIZ,'exp1/figures/exp1_step_response.html'))
e2=svgs(os.path.join(RAIZ,'exp2/figures/exp2_force_overshoot.html'))
cruce=svgs(os.path.join(RAIZ,'exp2/figures/exp2_cruce_fset.html'))
cmp_=svgs(os.path.join(RAIZ,'figuras/comparativa_indice_pulgar.html'))
dist=svgs(os.path.join(RAIZ,'exp2/figures/exp2_dof4_distribucion.html'))
tcpf=svgs(os.path.join(RAIZ,'figuras/replica_tcp_onset.html'))
sys.path.insert(0, os.path.join(RAIZ, 'figuras'))   # replica_tcp_figure vive ahí
import replica_tcp_figure as _rtf          # reusa el cálculo de grupos y del paso del registro
_b25, _b1k = _rtf.onsets(25), _rtf.onsets(1000)
_st25, _st1k = _rtf.register_step(25), _rtf.register_step(1000)
_cl1k = _rtf.clusters(_b1k)

# datos del pulgar (DOF 4) para la sección comparativa
import statistics as _st
_gT=json.load(open(os.path.join(RAIZ,'exp2/data_dof4/exp2_overshoot_grid.json')))
_gI=json.load(open(os.path.join(RAIZ,'exp2/data/exp2_overshoot_grid.json')))
_sT={int(r['speed']):r for r in csv.DictReader(open(os.path.join(RAIZ,'exp1/data_dof4/analysis_by_speed.csv')))}
def _hyb(d):
    """ΔF del modo B por Fset, desde el JSON analizado: ya excluye los trials en
    los que el dedo no llegó al objeto (ver exp2_analyze.drop_*)."""
    g=json.load(open(os.path.join(RAIZ,d,'exp2_overshoot_grid.json')))
    med=g['median'][str(g['speeds'][0])]
    return {int(f):med[str(f)] for f in g['fsets'] if med.get(str(f)) is not None}
_bT,_bI=_hyb('exp2/data_dof4_hybrid'),_hyb('exp2/data_hybrid')
# distribución de impactos del pulgar a v=1000, Fset=100 (los 40 dedicados + los
# 15 de esa misma celda y montaje): la mediana esconde que hay DOS regímenes
_dist=[float(r['delta_f']) for r in csv.DictReader(open(os.path.join(RAIZ,'exp2/data_dof4_termico/grid_index.csv'))) if r['delta_f']]
_dist+=[float(r['delta_f']) for r in csv.DictReader(open(os.path.join(RAIZ,'exp2/data_dof4/grid_index.csv')))
        if int(r['fset'])==100 and int(r['speed'])==1000 and r.get('mount')=='m3' and r['delta_f']]
_dist=sorted(_dist); _dmed=_st.median(_dist)
_dhi=[v for v in _dist if v>1500]; _dlo=[v for v in _dist if v<=1500]
_bB=sorted(float(r['delta_f']) for r in csv.DictReader(open(os.path.join(RAIZ,'exp2/data_dof4_hybrid/grid_index.csv'))) if int(r['fset'])==100 and r['delta_f'])
_sI={int(r['speed']):r for r in csv.DictReader(open(os.path.join(RAIZ,'exp1/data/analysis_by_speed.csv')))}
# --- Verificación de los tres dedos restantes por TCP -----------------------
def _k(d, vmax=500):
    r=[x for x in csv.DictReader(open(os.path.join(RAIZ,d,'analysis_by_speed.csv')))
       if int(x['speed'])<=vmax]
    return sum(int(x['speed'])*float(x['slope_cps_mean']) for x in r)/sum(int(x['speed'])**2 for x in r)
_KS=[('Meñique',0,'exp1/data_dof0','exp1/data_dof0_tcp'),('Anular',1,'exp1/data_dof1','exp1/data_dof1_tcp'),
     ('Medio',2,'exp1/data_dof2','exp1/data_dof2_tcp'),('Índice',3,'exp1/data','exp1/data_tcp'),
     ('Pulgar',4,'exp1/data_dof4','exp1/data_dof4_tcp')]
_KT=[(n,d,_k(a),_k(b)) for n,d,a,b in _KS]
_kall=[v for _,_,a,b in _KT for v in (a,b)]
_g2=json.load(open(os.path.join(RAIZ,'exp2/data_dof2_tcp/exp2_overshoot_grid.json')))
_g1=json.load(open(os.path.join(RAIZ,'exp2/data_dof1_tcp/exp2_overshoot_grid.json')))
def _hyb2(d,F):
    v=[float(r['delta_f']) for r in csv.DictReader(open(os.path.join(RAIZ,d,'grid_index.csv')))
       if int(r['fset'])==F and r['delta_f']]
    return statistics.median(v)
_ab=[r for r in csv.DictReader(open(os.path.join(RAIZ,'exp2/data_dof1_tcp_ab_borde/ab_index.csv')))]
_abA=statistics.median(float(r['delta_f']) for r in _ab if r['policy']=='A')
_abB=statistics.median(float(r['delta_f']) for r in _ab if r['policy']=='B')
_g2res=43.0   # residual de flexión del medio en el onset (sondeo tcp1)
_krows=''.join(
    f'<tr><td class="mono b">{d} {n}</td><td class="mono">{a:.3f}</td>'
    f'<td class="mono">{b:.3f}</td><td class="mono">{100*(b-a)/a:+.1f} %</td></tr>'
    for n,d,a,b in _KT)
# Réplica por TCP: los dos grupos de posición de contacto, calculados del hueco
# mayor de cada campaña (no se fija a mano dónde parte).
def _onsets(d):
    return sorted(int(r['onset_pos']) for r in csv.DictReader(open(os.path.join(RAIZ,d)))
                  if r['onset_pos'] and r.get('aborted','0')=='0')
def _split(v):
    g=max(((b-a,i) for i,(a,b) in enumerate(zip(v,v[1:]))), key=lambda t:t[0])
    return v[:g[1]+1], v[g[1]+1:], g[0]
_oS=_onsets('exp2/data_dof4_onset/onset_trials.csv')
_oT=_onsets('exp2/data_dof4_tcp_onset/onset_trials.csv')
_lS,_hS,_gapS=_split(_oS)
_oT2=[x for x in _oT if x<960]            # un toque suelto muy lejos, aparte
_lT,_hT,_gapT=_split(_oT2)
_LOW=(100,250,500)   # tramo donde AMBOS dedos son lineales: fuera de él el pulgar satura
_kT=sum(v*float(_sT[v]['slope_cps_mean']) for v in _LOW)/sum(v*v for v in _LOW)
_kI=sum(v*float(_sI[v]['slope_cps_mean']) for v in _LOW)/sum(v*v for v in _LOW)
_FS=[int(f) for f in _gI['fsets']]
_gapI=sum(1 for v in _gI['speeds'] if _gI['median'][str(v)]['100'] is None)
_redT={F:_gT['median']['1000'][str(F)]/_bT[F] for F in _FS}
# Reducción del modo B en el índice, solo sobre los Fset que SÍ alcanzan el objeto
_redI={F:_gI['median']['1000'][str(F)]/_bI[F] for F in _FS
       if _gI['median']['1000'].get(str(F)) is not None and _bI.get(F)}
def _c(v):
    """'—' donde el dedo no llegó a tocar el objeto: esa celda no existe, no es 0."""
    return '—' if v is None else f'{v:.0f}'


_cmp_rows=''.join(
    f'<tr><td class="mono b">{F}</td>'
    f'<td class="mono">{_c(_gI["median"]["1000"].get(str(F)))}</td>'
    f'<td class="mono">{_c(_bI.get(F))}</td>'
    f'<td class="mono">{_c(_gT["median"]["1000"].get(str(F)))}</td>'
    f'<td class="mono">{_c(_bT.get(F))}</td>'
    f'<td class="mono b">{_redT[F]:.0f}×</td></tr>' for F in _FS)

# ── Exp 3: régimen de contacto sostenido ─────────────────────────────────────
def _e3(path):
    return list(csv.DictReader(open(os.path.join(RAIZ,'exp3/data',path))))

def _med(rows, key, pred=None):
    v=[float(r[key]) for r in rows
       if r.get(key) not in ('',None) and (pred is None or pred(r))]
    return statistics.median(v) if v else float('nan')

def _plateau(traces_csv):
    """Meseta a la que cae la fuerza cuando se pide por encima del techo, y
    cuanto aguanta antes. Reconstruye cada trial de la traza cruda de E3.3."""
    from collections import defaultdict
    g=defaultdict(lambda: {'base':[], 'step':[]})
    for r in _e3(traces_csv):
        if r['fresh_force']!='1' or not r['force_g']: continue
        g[(r['trial'],r['step_units'],r['dir'])][r['phase']].append(
            (float(r['t_s']), float(r['force_g'])))
    hold, plat = [], []
    for v in g.values():
        b, st_ = sorted(v['base']), sorted(v['step'])
        if len(b)<5 or len(st_)<10: continue
        f0=statistics.median([f for _,f in b[:5]])
        if f0 < 800: continue
        tb=b[-1][0]
        seq=b + [(tb+0.05+t, f) for t,f in st_]
        t_rel=next((t for t,f in seq if f < f0-200), None)
        if t_rel is None: continue
        hold.append(t_rel)
        plat.append(statistics.median([f for t,f in seq if t>=seq[-1][0]-0.5]))
    return (statistics.median(hold), statistics.median(plat),
            statistics.pstdev(plat), len(hold))

# modelo de planta: celdas limpias (por debajo del techo sostenible)
_e33I=[r for r in (_e3('e33_dof3_F250.csv')+ _e3('e33_dof3_F450.csv')) if r['f_base']]
_e33I=[r for r in _e33I if not (r['dir']=='cerrar' and r['cmd_before'] and
                                float(r['f_base'])>400)]
_e33T=[r for r in _e3('e33_dof4_F250.csv') if r['f_base']]
_fast=lambda r: float(r['t_onset_ms'])<400 if r['t_onset_ms'] else False
_lagI=_med(_e33I,'t_onset_ms',_fast); _tauI=_med(_e33I,'tau_smith_ms')
_setI=_med(_e33I,'t_settle_ms', lambda r: r['t_settle_ms'] and float(r['t_settle_ms'])<900)
_lagT=_med(_e33T,'t_onset_ms',_fast); _tauT=_med(_e33T,'tau_smith_ms')
_setT=_med(_e33T,'t_settle_ms', lambda r: r['t_settle_ms'] and float(r['t_settle_ms'])<900)
_holdI,_platI,_sdI,_nI=_plateau('e33_dof3_F1000_traces.csv')
_holdT,_platT,_sdT,_nT=_plateau('e33_dof4_F1000_traces.csv')
_plat=(_platI+_platT)/2

# E3.4 + E3.5
_hdI=[r for r in _e3('e345_dof3_F450.csv') if r['f_start']]
_hdT=[r for r in _e3('e345_dof4_F450.csv') if r['f_start']]
def _jump(rows):
    return statistics.median([float(r['base_after_g'])-float(r['base_before_g'])
                              for r in rows if r['base_after_g'] and r['base_before_g']])
_jI,_jT=_jump(_hdI),_jump(_hdT)
_dropI=_med(_hdI,'drop_frac')*100; _dropT=_med(_hdT,'drop_frac')*100
_cycles=len(_hdI)+len(_hdT)

overlay, slope, latency = e1[0], e1[1], e1[2]
bars, compare = e2[0], e2[1]

# pendiente ∝ v (constante k) desde el análisis
by=list(csv.DictReader(open(os.path.join(RAIZ,'exp1/data/analysis_by_speed.csv'))))
sp=[int(r['speed']) for r in by]; sl=[float(r['slope_cps_mean']) for r in by]
k=sum(a*b for a,b in zip(sp,sl))/sum(a*a for a in sp)
r2min=min(float(r['r2_mean']) for r in by)

# ── Tabla 1: métricas del Exp 1 por velocidad ──
def _pm(r,key,dp=0):
    m=r.get(key+'_mean'); sd=r.get(key+'_sd')
    if m in (None,''): return '—'
    return f'{float(m):.{dp}f}<span class="pm">±{float(sd):.{dp}f}</span>'
t1='<div class="tbl-wrap"><table><caption><b>Tabla 1.</b> Respuesta al escalón (Exp 1): métricas por velocidad de cierre (media ± σ, N=20 por fila).</caption>'\
   '<thead><tr><th>SPEED_SET</th><th>Latencia (ms)</th><th>Subida 10–90% (ms)</th><th>Estab. ±2% (ms)</th><th>Pendiente (counts/s)</th><th>R²</th></tr></thead><tbody>'
for r in by:
    t1+=(f'<tr><td class="mono b">{r["speed"]}</td>'
         f'<td class="mono">{_pm(r,"L_band_ms")}</td>'
         f'<td class="mono">{_pm(r,"rise_ms")}</td>'
         f'<td class="mono">{_pm(r,"settle_ms")}</td>'
         f'<td class="mono">{float(r["slope_cps_mean"]):.0f}</td>'
         f'<td class="mono">{float(r["r2_mean"]):.3f}</td></tr>')
t1+='</tbody></table></div>'

# ── Tabla 2: mapa de sobreimpulso del Exp 2 ──
grid=json.load(open(os.path.join(RAIZ,'exp2/data/exp2_overshoot_grid.json')))
sp2=grid['speeds']; fs=grid['fsets']; med=grid['median']; abo=grid['abort']
t2='<div class="tbl-wrap"><table><caption><b>Tabla 2.</b> Sobreimpulso de fuerza ΔF = F_max − F_set (mediana, g) por celda. Filas = velocidad de cierre; columnas = F_set (g). ▲ = celda con impacto sobre el techo de seguridad (2200 g).</caption>'\
   '<thead><tr><th>v \\ F_set</th>'+''.join(f'<th>{F}</th>' for F in fs)+'</tr></thead><tbody>'
for v in sp2:
    cells=''
    for F in fs:
        m=med[str(v)][str(F)]; a=abo[str(v)][str(F)] or 0
        star='<span class="ab">▲</span>' if a else ''
        cells+='<td>—</td>' if m is None else f'<td class="mono">{m:.0f}{star}</td>'
    t2+=f'<tr><td class="mono b">{v}</td>{cells}</tr>'
t2+='</tbody></table></div>'

INK='#12181f'; MUTED='#5a6472'; HAIR='#dbe2ec'; ACC='#285F97'; AMBER='#B4740F'

HTML=f'''<title>Caracterización dinámica RH56DFTP — Resultados iniciales</title>
<style>
  :root{{--ink:{INK};--muted:{MUTED};--hair:{HAIR};--acc:{ACC};--amber:{AMBER};
    --bg:#f6f8fb;--panel:#ffffff;--soft:#eef2f7;}}
  *{{box-sizing:border-box;}}
  /* El visor compone sobre un fondo que pinta EL con su propio tema: sin un
     background explícito en body, los márgenes fuera de .wrap heredarían un
     ground oscuro y el documento se partiría en dos. Este documento se
     compromete a un solo mundo visual (papel de instrumento), así que no lleva
     bloques de tema — pero pinta su fondo y sus colores explícitamente. */
  body{{background:var(--bg);color:var(--ink);margin:0;}}
  .wrap{{max-width:880px;margin:0 auto;padding:52px 26px 72px;color:var(--ink);background:var(--bg);
    font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.62;
    font-size:16px;}}
  .mono{{font-family:ui-monospace,"SF Mono","JetBrains Mono",Menlo,monospace;font-variant-numeric:tabular-nums;}}
  .b{{font-weight:600;}} .ey{{letter-spacing:.14em;text-transform:uppercase;}}
  .eyebrow{{font-size:12px;letter-spacing:.24em;text-transform:uppercase;color:var(--acc);font-weight:600;}}
  h1{{font-size:33px;line-height:1.12;margin:.5rem 0 .4rem;letter-spacing:-.015em;text-wrap:balance;max-width:20ch;}}
  .byline{{color:var(--muted);font-size:14px;margin:0 0 22px;}}
  .byline .mono{{color:var(--ink);}}
  .abstract{{font-size:17px;max-width:64ch;margin:0;color:#333b45;}}
  .abstract b{{color:var(--ink);}}
  h2{{font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:var(--acc);font-weight:700;
    margin:0 0 4px;display:flex;align-items:baseline;gap:10px;}}
  h2 .tag{{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:var(--muted);
    letter-spacing:0;text-transform:none;border:1px solid var(--hair);border-radius:20px;padding:1px 8px;}}
  h3{{font-size:20px;margin:.1rem 0 .5rem;letter-spacing:-.01em;text-wrap:balance;}}
  section{{margin:30px 0;}}
  p{{margin:.5rem 0;}}
  .rule{{height:1px;background:var(--hair);border:0;margin:30px 0;}}
  .lead{{font-size:16.5px;}}
  ul{{margin:.5rem 0;padding-left:1.1rem;}} li{{margin:.28rem 0;}}
  strong,b{{font-weight:600;}}
  .kpis{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:24px 0 4px;}}
  @media(max-width:640px){{.kpis{{grid-template-columns:repeat(2,1fr);}}}}
  .kpi{{background:var(--panel);border:1px solid var(--hair);border-radius:11px;padding:15px 15px 13px;}}
  .kpi .n{{font-size:23px;font-weight:600;letter-spacing:-.015em;line-height:1.1;}}
  .kpi .n .u{{font-size:13px;color:var(--muted);font-weight:500;}}
  .kpi .l{{font-size:11.5px;color:var(--muted);margin-top:5px;line-height:1.35;}}
  .method{{background:var(--soft);border:1px solid var(--hair);border-radius:11px;padding:16px 18px;
    font-size:14px;color:#3a434e;}}
  /* Aviso correctivo: va como acotación al margen, no como otra tarjeta — el
     documento ya usa .method y .panel para bloques, y una tercera caja aplanaría
     la jerarquía. */
  .note{{font-size:13.5px;color:var(--muted);border-left:2px solid var(--hair);
    padding-left:14px;margin:14px 0;}}
  /* Corrección publicada: más peso que .note porque rectifica un resultado, no
     acota uno. Filete ámbar (el color de "atención" del documento) sobre el
     fondo suave; sin borde completo, que lo convertiría en otra tarjeta. */
  .callout{{background:var(--soft);border-left:3px solid var(--amber);
    border-radius:0 8px 8px 0;padding:13px 16px;margin:16px 0;font-size:14px;color:#3a434e;}}
  .callout b{{color:var(--ink);}}
  /* Título de .panel — mismo tratamiento que .method .h */
  .tt{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);
    font-weight:700;margin-bottom:8px;}}
  .tt .tag{{letter-spacing:0;text-transform:none;font-weight:400;}}
  /* Leyenda de figura: la identidad de cada serie va por muestra de color MÁS
     etiqueta, nunca por color solo. */
  .legend{{display:flex;flex-wrap:wrap;gap:8px 18px;font-size:12.5px;color:var(--muted);
    margin-bottom:10px;}}
  .li{{display:inline-flex;align-items:center;gap:7px;}}
  .sw{{width:11px;height:11px;border-radius:3px;display:inline-block;flex:none;}}
  .method .h{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);font-weight:700;margin-bottom:6px;}}
  .method code,.foot code,p code,li code{{font-family:ui-monospace,Menlo,monospace;font-size:.86em;
    background:var(--soft);padding:1px 5px;border-radius:4px;color:var(--ink);}}
  figure{{margin:20px 0 6px;background:var(--panel);border:1px solid var(--hair);border-radius:11px;padding:16px 16px 8px;}}
  figure.pair{{display:grid;grid-template-columns:1fr 1fr;gap:14px;background:none;border:0;padding:0;}}
  figure.pair > div{{background:var(--panel);border:1px solid var(--hair);border-radius:11px;padding:14px 14px 8px;}}
  @media(max-width:600px){{figure.pair{{grid-template-columns:1fr;}}}}
  svg{{width:100%;height:auto;display:block;}}
  figcaption{{font-size:12.5px;color:var(--muted);margin-top:10px;}}
  figcaption b{{color:var(--ink);}}
  .foot{{font-size:12.5px;color:var(--muted);border-top:1px solid var(--hair);margin-top:34px;padding-top:16px;}}
  a{{color:var(--acc);}}
  table{{width:100%;border-collapse:collapse;font-size:13.5px;margin:4px 0;}}
  caption{{caption-side:top;text-align:left;font-size:12.5px;color:var(--muted);margin-bottom:9px;line-height:1.5;}}
  caption b{{color:var(--ink);}}
  th,td{{text-align:right;padding:7px 9px;border-bottom:1px solid var(--hair);}}
  th:first-child,td:first-child{{text-align:left;}}
  thead th{{font-size:10.5px;letter-spacing:.04em;text-transform:uppercase;color:var(--muted);font-weight:600;}}
  .tbl-wrap{{overflow-x:auto;margin:18px 0 6px;}}
  .pm{{color:var(--muted);font-size:.8em;margin-left:1px;}}
  .ab{{color:var(--amber);margin-left:1px;}}
</style>
<div class="wrap">

  <header>
    <div class="eyebrow">Trabajo de tesis · Resultados iniciales</div>
    <h1>Caracterización dinámica de la mano robótica Inspire RH56DFTP</h1>
    <p class="byline"><span class="mono">Sergio Morales</span> · Universidad de Ingeniería y Tecnología (UTEC) · Julio 2026 · <span class="ey" style="font-size:11px">documento de trabajo</span></p>
    <p class="abstract">Se caracterizó experimentalmente la respuesta dinámica de la mano robótica Inspire RH56DFTP (comunicación Modbus RTU a 115 200 baud) con experimentos de <b>hardware en el lazo</b>. El hallazgo central: el <b>sobreimpulso de fuerza</b> al cerrar los dedos está dominado por la velocidad de cierre —llega a <b>triplicar la fuerza deseada</b>— y una estrategia de aproximación <b>híbrida</b> (rápida hasta el borde del contacto, luego lenta) lo reduce <b>{min(_redI.values()):.0f}–{max(_redI.values()):.0f}×</b>. Se cuantificaron además la latencia comando→sensor, la respuesta al escalón y la repetibilidad del contacto para fijar los parámetros de dicha estrategia.</p>
  </header>

  <div class="kpis">
    <div class="kpi"><div class="n">~33<span class="u"> Hz</span></div><div class="l">estado nuevo por sensor — el enlace lee a 98–800 Hz, la mano no publica más rápido</div></div>
    <div class="kpi"><div class="n">~64<span class="u"> ms</span></div><div class="l">latencia comando→sensor (indep. de la velocidad)</div></div>
    <div class="kpi"><div class="n">~3300<span class="u"> g</span></div><div class="l">sobreimpulso de fuerza al cerrar rápido</div></div>
    <div class="kpi"><div class="n">{min(_redI.values()):.0f}–{max(_redI.values()):.0f}<span class="u">×</span></div><div class="l">reducción del sobreimpulso con la política híbrida</div></div>
  </div>

  <hr class="rule">

  <section>
    <h2>Contexto y objetivo</h2>
    <p class="lead">La RH56DFTP es una mano de 6 grados de libertad con sensores de fuerza en cada dedo, controlada por Modbus sin middleware. Para diseñar un <b>controlador de agarre híbrido</b> —que aproxime rápido y toque suave, evitando dañar objetos delicados— hace falta caracterizar tres propiedades del hardware: la <b>latencia</b> comando→sensor, la <b>dinámica de movimiento</b>, y el <b>sobreimpulso de fuerza</b> en el impacto. Este documento resume esos resultados iniciales, obtenidos sobre la mano física.</p>
  </section>

  <hr class="rule">

  <section>
    <h2>Método</h2>
    <h3>Protocolo experimental y definición de métricas</h3>
    <p><b>Adquisición.</b> Comunicación Modbus RTU a 115 200 baud (RS-485), un solo proceso/hilo/cliente con <b>lazo intercalado</b> (el comando se inyecta en el mismo lazo que lee, sin hilos separados), y marcas de tiempo con <code>time.perf_counter()</code> (reloj monotónico). Registros usados: <code>FORCE_ACT</code> (fuerza, g), <code>POS_ACT</code> (posición del actuador, 0–2000), <code>ANGLE_SET/ANGLE_ACT</code> (0–1000), <code>FORCE_SET</code> y <code>CURRENT</code>. La fuerza se tara con <code>forceClb</code> (palma abierta), dejando <code>FORCE_ACT</code> ≈ <b>fuerza externa real</b>. Todo corre fuera de la interfaz gráfica y es reproducible desde los CSV crudos.</p>
    <p><b>Exp 0 · muestreo.</b> Lectura del bloque de 6 <code>FORCE_ACT</code> en lazo cerrado (3×2000 lecturas); se registra el periodo <code>dt</code> de cada muestra y se reporta la tasa media y percentiles.</p>
    <p><b>Exp 1 · escalón en espacio libre.</b> Índice (DOF 3) en el aire; escalón de <code>ANGLE_SET</code> con <code>FORCE_SET</code> alto (para no limitar por fuerza); 5 velocidades × 20 repeticiones en orden aleatorio; muestreo de <code>POS_ACT</code> a ~90 Hz.</p>
    <p><b>Exp 2 · fuerza en contacto.</b> Yema del índice contra un bloque rígido; <code>forceClb</code> al inicio y recalibración periódica; barrido velocidad × <code>FORCE_SET</code> (5 réplicas por celda, orden aleatorio); se usa la <b>mediana</b> (robusta a outliers/aborts); seguridad por techo de fuerza (2200 g) y vigilancia de <code>CURRENT</code>. El modo <b>híbrido</b> aproxima rápido al borde del contacto y luego cierra lento.</p>
    <p><b>Sub-experimento · onset.</b> 50 toques suaves a velocidad máxima; la posición de primer contacto se detecta con un <b>baseline de fuerza propio de cada toque</b> (inmune a la deriva del sensor) y se retrae al detectar; se reporta σ robusta.</p>
    <div class="method">
      <div class="h">Definición de métricas</div>
      <b>Latencia</b>: del comando al primer movimiento detectable de <code>POS_ACT</code>. &nbsp;·&nbsp; <b>Tiempo de subida</b>: 10 %→90 % del desplazamiento final. &nbsp;·&nbsp; <b>Establecimiento</b>: entrada permanente en ±2 % del valor final. &nbsp;·&nbsp; <b>Pendiente / R²</b>: ajuste lineal del tramo 20–80 % (velocidad del actuador). &nbsp;·&nbsp; <b>ΔF (sobreimpulso)</b>: F_max − F_set. &nbsp;·&nbsp; <b>q_sw</b>: margen de conmutación = ceil(3.3·σ) del onset.
    </div>
  </section>

  <hr class="rule">

  <section>
    <h2>Exp 0 <span class="tag">baseline de muestreo</span></h2>
    <h3>El enlace sostiene 98 lecturas por segundo — la mano publica 33</h3>
    <p>Se leyó el bloque de los 6 registros de fuerza en lazo cerrado (3×2000 lecturas). Tasa media <b>98.3 Hz</b> con <b>0 errores</b> en 6000 lecturas; por Ethernet, 797 Hz. El techo de la <b>lectura</b> lo imponen el bus y el firmware, no el software.</p>
    <p class="note">Esa cifra es la tasa a la que se <b>pregunta</b>, no a la que la mano <b>responde con algo nuevo</b>. Midiendo cada cuánto cambia de valor un registro —y no cada cuánto se lee— la realimentación útil resulta ser de <b>~33 Hz</b> en los dos canales: ver la última sección. La resolución temporal de todo lo que sigue es por tanto de ~30 ms, no de ~10.</p>
  </section>

  <hr class="rule">

  <section>
    <h2>Exp 1 <span class="tag">respuesta al escalón · espacio libre</span></h2>
    <h3>Movimiento lineal con la velocidad y retardo fijo, sin sobreimpulso de posición</h3>
    <p>El dedo índice ejecuta un escalón de posición <b>en el aire</b> (sin objeto), a cinco velocidades × 20 repeticiones, muestreando la posición del actuador a ~90 Hz. Resultados: (i) el <b>retardo comando→sensor es ≈ 64 ms e independiente de la velocidad</b>; (ii) la velocidad del dedo <b>escala linealmente con el setpoint</b> (pendiente ≈ <span class="mono">{k:.2f} × v</span> sobre todo el barrido, <span class="mono">R² ≥ {r2min:.2f}</span>), es decir, crecimiento lineal sin deceleración; (iii) el <b>sobreimpulso de posición es ≈ 0</b>.</p>
    <figure>
      {overlay}
      <figcaption><b>Figura 1.</b> Trayectorias medias de posición normalizada, alineadas al instante del comando, por velocidad de cierre. El arranque común confirma un retardo independiente de la velocidad; el abanico de pendientes, el escalado lineal.</figcaption>
    </figure>
    <figure class="pair">
      <div>{slope}<figcaption>Pendiente ∝ velocidad comandada (ajuste por el origen).</figcaption></div>
      <div>{latency}<figcaption>Latencia ~plana con la velocidad (barras = ±1σ).</figcaption></div>
    </figure>
    {t1}
  </section>

  <hr class="rule">

  <section>
    <h2>Exp 2 <span class="tag">sobreimpulso de fuerza · en contacto</span></h2>
    <h3>El sobreimpulso lo domina la velocidad de cierre — y la estrategia híbrida lo elimina</h3>
    <p>La yema del índice cierra contra un <b>bloque rígido</b>; se mide el sobreimpulso <span class="mono">ΔF = F_max − Fset</span> en función de la velocidad y del setpoint de fuerza (5 réplicas por celda). Resultados: (i) el sobreimpulso <b>crece dramáticamente con la velocidad</b> — a alta velocidad el impacto de la yema alcanza <b>~3300 g (≈33 N)</b>, casi independiente del setpoint, superando el techo de seguridad; (ii) un <b>setpoint bajo</b> (100 g) <b>no es una zona segura sino un ajuste inalcanzable</b>: queda por debajo de la fuerza que el propio dedo genera al flexionarse, así que el firmware frena <b>en el aire</b> y el dedo no llega a tocar el objeto en {_gapI} de las 7 velocidades — y en la única en que el momento lo mete dentro (<span class="mono">v=1000</span>) golpea con <b>{_gI['median']['1000']['100']:.0f} g</b>; (iii) la <b>política híbrida</b> —aproximación rápida hasta el borde del contacto y luego cierre lento— <b>colapsa el sobreimpulso ~35×</b>, al nivel del cierre lento, alcanzando el setpoint sin impactos.</p>

    <div class="callout"><b>Corrección (2026-09-07).</b> El punto (ii) decía antes que el setpoint de 100 g mantenía el sobreimpulso «plano y bajo a toda velocidad», y así se presentó como el hallazgo central. Al medir por fin la <b>curva de fuerza del dedo en espacio libre</b> —que faltaba— se vio que esos ensayos <b>nunca alcanzaban el objeto</b>: terminan en <span class="mono">POS 791–851</span> con el bloque en <span class="mono">POS 1416</span>, siempre en el mismo punto sea cual sea la velocidad, que es la firma de frenar contra la propia fuerza de flexión. El sobreimpulso «bajo» era <b>ausencia de impacto</b>. La verificación posterior en los otros tres dedos confirma el patrón y da el criterio para detectarlo.</div>
    <figure>
      {bars}
      <figcaption><b>Figura 2.</b> Sobreimpulso de fuerza por celda (velocidad × setpoint). ▲ marca los impactos que superaron el techo de seguridad de 2200 g. La columna de setpoint 100 g está <b>vacía</b> en casi todo el barrido: ahí el dedo no llegaba a tocar el objeto.</figcaption>
    </figure>
    <figure>
      {compare}
      <figcaption><b>Figura 3 · La mitigación.</b> Con la política híbrida (curva azul) el sobreimpulso se colapsa al nivel de la aproximación lenta, muy por debajo del cierre rápido (curva ámbar), para todo setpoint.</figcaption>
    </figure>
    {t2}
  </section>

  <hr class="rule">

  <section>
    <h2>Sub-experimento <span class="tag">margen de conmutación</span></h2>
    <h3>Dónde debe la mano cambiar a velocidad lenta</h3>
    <p>Para fijar el punto en que la política híbrida cambia a cierre lento, se midió la <b>posición de primer contacto</b> en 50 toques suaves a máxima velocidad, de donde sale un <b>margen de conmutación de ~124 counts</b>: la mano entra al cierre lento ~124 counts <b>antes</b> del contacto esperado, garantizando un toque suave. Este margen se re-mide por montaje.</p>
    <p class="note">El margen es correcto, pero el razonamiento que lo justificó no: se atribuyó la dispersión medida a la resolución de posición por muestra, y se resumió el contacto con la desviación de su grupo más poblado. Repetir el experimento a nueve veces la tasa de muestreo mostró que ninguna de las dos cosas se sostiene — ver la última sección.</p>
  </section>

  <hr class="rule">

  <section>
    <h2>Réplica en un segundo dedo <span class="tag">índice vs pulgar</span></h2>
    <h3>Qué del hardware es general y qué es propio de cada dedo</h3>
    <p class="lead">Todo el protocolo se repitió sobre la <b>flexión del pulgar</b> (DOF&nbsp;4), con la rotación del pulgar anclada en oposición para que la única variable fuera la flexión: 100 trials de escalón y 200 de contacto adicionales. El objetivo no era duplicar resultados sino <b>separar lo que es propiedad de la plataforma de lo que depende del dedo</b> — la distinción que decide si una estrategia de control se puede generalizar.</p>

    <figure>
      <div class="legend"><span class="li"><span class="sw" style="background:#285F97"></span>Índice (DOF 3)</span><span class="li"><span class="sw" style="background:#B4740F"></span>Pulgar (DOF 4)</span></div>
      <div class="grid2">{cmp_[0]}{cmp_[1]}</div>
      <figcaption><b>Figura 4.</b> <b>Izquierda:</b> la velocidad comandada se traduce en movimiento con la <b>misma constante en los dos dedos</b> ({_kI:.2f} y {_kT:.2f} counts/s por unidad de <span class="mono">SPEED_SET</span>, ajustadas sobre el tramo donde ambos son lineales) — el comando calibra el actuador, no el ángulo. El pulgar solo se despega en el extremo (−12&nbsp;% a máxima velocidad: su techo mecánico). <b>Derecha:</b> un umbral de fuerza bajo (100&nbsp;g) <b>no protege a ninguno de los dos</b>. En el pulgar deja de contener el impacto en cuanto sube la velocidad, hasta {_gT['median']['1000']['100']:.0f}&nbsp;g. En el índice el umbral queda por debajo de su propia fuerza de flexión, así que el dedo <b>no llega al objeto</b> (franja gris) salvo a máxima velocidad, donde golpea con {_gI['median']['1000']['100']:.0f}&nbsp;g. Escala logarítmica.</figcaption>
    </figure>

    <figure>
      <div class="legend"><span class="li"><span class="sw" style="background:#285F97"></span>Índice</span><span class="li"><span class="sw" style="background:#B4740F"></span>Pulgar</span><span class="li" style="color:var(--muted)">○ modo A a máxima velocidad &nbsp;·&nbsp; ● modo B híbrido</span></div>
      {cmp_[2]}
      <figcaption><b>Figura 5.</b> La política híbrida colapsa el sobreimpulso <b>en los dos dedos y para todo umbral de fuerza</b>, entre 30× y 82×.</figcaption>
    </figure>

    <div class="panel">
      <div class="tt">Tabla 3 · Sobreimpulso a máxima velocidad: modo directo frente a híbrido <span class="tag">mediana, g</span></div>
      <div style="overflow-x:auto"><table>
        <thead><tr><th>Umbral de fuerza (g)</th><th>Índice · directo</th><th>Índice · híbrido</th><th>Pulgar · directo</th><th>Pulgar · híbrido</th><th>Reducción (pulgar)</th></tr></thead>
        <tbody>{_cmp_rows}</tbody>
      </table></div>
    </div>

    <h3>Por qué la mediana no basta</h3>
    <p>El mapa de arriba reporta medianas, y para dimensionar un agarre eso induce a error. Repitiendo <b>{len(_dist)} veces</b> el caso más desfavorable del pulgar —velocidad máxima con el umbral de fuerza más bajo— la distribución de los impactos resulta no tener un valor típico, sino <b>dos</b>.</p>

    <figure>
      {dist[0]}
      <figcaption><b>Figura 6.</b> {len(_dlo)} impactos se agrupan entre {min(_dlo):.0f} y {max(_dlo):.0f}&nbsp;g; después hay <b>500&nbsp;g sin un solo impacto</b>; y {len(_dhi)} llegan a {min(_dhi):.0f}–{max(_dhi):.0f}&nbsp;g, más del doble de la mediana. El régimen duro <b>no se anuncia</b>: ocurre con el mismo comando, en la misma posición de contacto y con el mismo residual de fuerza que los suaves. A la izquierda, el modo híbrido: sus trials caben en {min(_bB):.0f}–{max(_bB):.0f}&nbsp;g.</figcaption>
    </figure>

    <p>La consecuencia es concreta: un objeto dimensionado para aguantar la mediana (~{_dmed:.0f}&nbsp;g) no falla «de vez en cuando», falla en <b>1 de cada {len(_dist)//len(_dhi)} agarres</b>, y cuando falla recibe además presión sostenida y no solo un pico. Como nada en la señal permite anticipar cuál de los dos regímenes va a ocurrir, <b>acotar el pico en promedio no es una mitigación</b>. La conmutación de velocidad sí lo es, porque suprime el régimen duro entero en vez de promediarlo.</p>

    <p><b>Lo que generaliza:</b> la calibración velocidad→movimiento, la latencia comando→sensor (~73&nbsp;ms en el pulgar contra ~69 en el índice, sin dependencia de la velocidad) y la ausencia de sobreimpulso de posición. Son propiedades de la plataforma, no del dedo.</p>
    <p><b>Lo que no:</b> el "umbral de fuerza bajo" <b>no protege en ningún dedo</b>. Cuando el umbral queda por debajo de la fuerza que el propio dedo genera al flexionarse, el firmware frena en el aire y el dedo ni siquiera alcanza el objeto — eso pasa en el índice y en el meñique, donde el ajuste directamente <b>no es ejecutable</b>. Y cuando el dedo sí llega, como el pulgar, el umbral no contiene el impacto: {_gT['median']['1000']['100']:.0f}&nbsp;g a máxima velocidad. <b>La conmutación de velocidad es la única mitigación que sobrevive</b>, verificada en los cinco grados de libertad, porque ataca la causa —el momento en el instante del contacto— y no el síntoma.</p>
  </section>

  <hr class="rule">

  <section>
    <h2>Réplica por Modbus TCP <span class="tag">mismo dedo · 9× la tasa de lectura</span></h2>
    <h3>La mano publica estado nuevo 33 veces por segundo, se lea a la velocidad que se lea</h3>
    <p class="lead">La mano también responde por Ethernet, lo que multiplica por nueve la tasa de <b>lectura</b> (de ~65 a ~600 consultas por segundo). Todo el protocolo del pulgar se repitió por ese canal —100 trials de escalón, 175 de contacto, 120 toques de contacto y 25 del modo híbrido— con dos preguntas: si cambiaba la física, y si mejoraban las medidas que se habían dado por limitadas por el muestreo.</p>
    <p><b>La física no cambia.</b> El mapa de posición reproduce <b>dentro de 1 count</b> un mes y varios montajes después; la constante de velocidad, el retardo, la distancia de frenado, el mapa de sobreimpulso completo y el colapso del modo híbrido caen todos dentro de la variabilidad de las campañas. Eso <b>valida hacia atrás</b> toda la caracterización hecha por el canal serie.</p>
    <p><b>Y las medidas tampoco mejoran</b> — pero no porque el muestreo no importe, sino porque el cuello de botella nunca estuvo en el enlace. Midiendo cada cuánto <b>cambia de valor</b> un registro, en lugar de cada cuánto se lee, aparece la explicación de todo lo anterior:</p>

    <div class="panel">
      <div class="tt">Tasa de lectura frente a tasa de información <span class="tag">cuatro campañas, dos canales</span></div>
      <div style="overflow-x:auto"><table>
        <thead><tr><th>Campaña</th><th>Se lee a</th><th>El valor cambia cada</th><th>Información real</th></tr></thead>
        <tbody>
          <tr><td>Contacto, Ethernet</td><td class="mono">596 Hz</td><td class="mono">30.5 ms</td><td class="mono b">33 Hz</td></tr>
          <tr><td>Cierre lento, Ethernet</td><td class="mono">579 Hz</td><td class="mono">31.1 ms</td><td class="mono b">32 Hz</td></tr>
          <tr><td>Política híbrida, Ethernet</td><td class="mono">575 Hz</td><td class="mono">31.0 ms</td><td class="mono b">32 Hz</td></tr>
          <tr><td>Contacto, canal serie</td><td class="mono">78 Hz</td><td class="mono">31.1 ms</td><td class="mono b">32 Hz</td></tr>
        </tbody>
      </table></div>
    </div>

    <p>Posición, fuerza y corriente se refrescan <b>cada ~30.7&nbsp;ms</b>, con independencia del canal, de la velocidad del dedo y de lo rápido que se pregunte. Por encima de ~33&nbsp;Hz se releen valores que no han cambiado. Lo que Ethernet sí aporta es <b>entregar antes</b> cada valor nuevo —hasta 30&nbsp;ms menos de espera—, que para un lazo de control es real, pero no es más información.</p>

    <h3>Qué explica esto</h3>
    <p>La posición de primer contacto parecía tener <b>dos valores</b> en vez de uno, en los dos canales y en tres montajes distintos. Repetir el experimento a velocidad lenta y a velocidad máxima sobre el mismo montaje lo resuelve:</p>

    <figure>
      {tcpf[0]}
      <figcaption><b>Figura 7.</b> A cierre lento los {len(_b25)} toques caen en un solo punto, con una repetibilidad de <b>σ&nbsp;=&nbsp;{_st.pstdev(_b25):.1f}&nbsp;counts</b>. A velocidad máxima aparecen dos grupos separados <b>{_st.median(_cl1k[1])-_st.median(_cl1k[0]):.0f}&nbsp;counts</b> — que es exactamente lo que el dedo avanza entre dos refrescos del registro a esa velocidad ({_st1k:.0f}&nbsp;counts, frente a {_st25:.0f} en el cierre lento). No son dos posiciones de contacto: son <b>dos escalones del registro de posición</b>.</figcaption>
    </figure>

    <p>El contacto de este dedo es, por tanto, <b>mucho más repetible de lo que cualquier medida anterior sugería</b>: σ de {_st.pstdev(_b25):.1f} counts frente a las decenas que se venían reportando. Lo que se estaba midiendo a alta velocidad no era la dispersión del dedo sino la resolución con que la mano informa de dónde está.</p>

    <p><b>La consecuencia práctica no es que el margen de seguridad sobre para el cierre lento, sino al revés:</b> a velocidad máxima el controlador <b>no puede saber dónde está el dedo mejor que ±{_st1k:.0f}&nbsp;counts</b>, por rápido que lea. El margen de conmutación de ~120&nbsp;counts que ya usaba la política híbrida queda justificado — por esta razón y no por la que se creía. Y refuerza la propia política: si la posición solo se conoce con esa holgura mientras se va rápido, la decisión de frenar no puede depender de leerla con precisión.</p>

    <p>De paso, la tasa alta hizo visibles dos defectos de método que el canal lento ocultaba: la pre-posición se daba por asentada cuando el dedo todavía reptaba unos counts —lo que contaminaba la medida de retardo—, y el registro de temperatura llega en un formato distinto por cada canal. Corregidos ambos, la campaña registró además el calentamiento del actuador, de 34 a 40&nbsp;°C a lo largo de los 175 contactos.</p>
  </section>

  <hr class="rule">

  <section>
    <h2>Los cinco dedos <span class="tag">verificación de los tres restantes</span></h2>
    <h3>La calibración de velocidad se confirma; el umbral de fuerza se derrumba</h3>

    <p class="lead">Meñique, anular y medio se midieron por Modbus TCP para completar los cinco grados de libertad. El <b>medio</b> llevó el protocolo entero —175 contactos del barrido más 25 de la política híbrida— por una razón concreta: es el único dedo cuya fuerza de flexión propia en el punto de contacto ({_g2res:.0f}&nbsp;g) deja el umbral más bajo <b>alcanzable</b>. En el índice y en el meñique no lo es, y por eso esa columna nunca se había podido medir de verdad.</p>

    <div class="tbl-wrap"><table><caption><b>Tabla 4.</b> Constante velocidad→movimiento por grado de libertad y por canal de comunicación (counts/s por unidad de <span class="mono">SPEED_SET</span>, ajuste por el origen sobre el tramo lineal).</caption>
      <thead><tr><th>Grado de libertad</th><th>RS-485</th><th>TCP</th><th>Diferencia</th></tr></thead>
      <tbody>{_krows}</tbody></table></div>

    <p><b>Diez medidas independientes entre {min(_kall):.2f} y {max(_kall):.2f}.</b> La velocidad comandada se traduce en movimiento con la misma constante en los cinco dedos y por los dos canales: es una propiedad del actuador, no del dedo ni del enlace. Esto cierra además una duda que había dejado la réplica del pulgar, cuyo valor se había movido un 1.7&nbsp;% sin explicación: se sospechaba de una corrección de método aplicada entre campañas, pero esa corrección habría afectado a todos los dedos por igual y los otros cuatro se mueven entre −0.3 y +0.4&nbsp;%.</p>

    <h3>El umbral de fuerza bajo no protege: a alta velocidad es el peor</h3>

    <p>Con el medio alcanzando el objeto en las siete velocidades, la columna del umbral más bajo se pudo medir por primera vez completa. El resultado invierte lo que el proyecto sostuvo durante meses: a máxima velocidad, <b>un umbral de 100&nbsp;g produce el golpe más fuerte de todo el mapa</b> — {_g2['median']['1000']['100']:.0f}&nbsp;g, por encima de cualquier ajuste más alto. El anular lo replica: {_g1['median']['1000']['100']:.0f}&nbsp;g frente a {_g1['median']['1000']['1000']:.0f}&nbsp;g del umbral de 1000.</p>

    <figure>
      <div class="grid2">{cruce[0]}{cruce[1]}</div>
      <figcaption><b>Figura 9.</b> A velocidad baja el umbral bajo hace lo que promete: menos sobreimpulso. A partir de <span class="mono">v ≈ 500–750</span> las curvas <b>se cruzan</b> y se invierte, en los dos dedos. El umbral solo manda mientras el dedo va lo bastante despacio para que el firmware alcance a frenar; pasado ese punto lo único que queda es el momento en el instante del contacto — y con el umbral bajo el dedo llega ahí habiendo acelerado más recorrido, porque nada lo frenó antes. La columna baja no es la segura: es la que más carrera le da al golpe.</figcaption>
    </figure>

    <p><b>La conmutación de velocidad sigue siendo la mitigación, y ahora se sabe cuánto entrega.</b> Comparada contra un cierre lento puro <b>en la misma tanda y en orden alternado</b> —el único diseño que resiste que el objeto ceda entre unas pruebas y otras— la política híbrida da {_abB:.0f}&nbsp;g frente a {_abA:.0f}&nbsp;g del cierre lento: <b>no hay diferencia medible</b>. Entrega el rendimiento del cierre lento sin pagar su tiempo de aproximación, que es exactamente lo que se le pedía.</p>

    <div class="callout"><b>Dos lecciones de método, ambas pagadas caras.</b> Primera: un sobreimpulso pequeño <b>no prueba que haya habido contacto</b>. Si el umbral queda por debajo de la fuerza que el propio dedo genera al flexionarse, el firmware frena en el aire y el ensayo termina con un ΔF minúsculo que parece protección perfecta — así se sostuvo durante meses un hallazgo que no existía. Hay que comprobar la carga, no leer el sobreimpulso. Segunda: <b>dos políticas solo se pueden comparar dentro de una misma tanda aleatorizada</b>. Medidas en tandas separadas, las mismas dos políticas sobre el mismo dedo y el mismo objeto difirieron en un factor dos por causas ajenas a ellas.</div>
  </section>

  <hr class="rule">

  <section>
    <h2>Exp 3 <span class="tag">régimen de contacto sostenido · hacia el regulador de fuerza</span></h2>
    <h3>Del golpe al apriete: lo que hace falta para cerrar un lazo</h3>

    <p class="lead">Los experimentos anteriores miden el <b>impacto</b>: qué pasa en los primeros cientos de milisegundos de un contacto. Un regulador de fuerza vive en el régimen contrario —el dedo ya apoyado, sosteniendo— y ese régimen no estaba caracterizado. El Exp 3 lo mide sobre los dos grados de libertad que forman la pinza: <b>índice y pulgar</b>.</p>

    <div class="callout"><b>El hallazgo que cambia el alcance: hay un techo de fuerza <i>sostenible</i> en torno a {_plat:.0f}&nbsp;g.</b> Por encima, la fuerza no se mantiene: se alcanza, se aguanta unas décimas de segundo y cae. El índice pedido a 1000&nbsp;g aguanta {_holdI:.2f}&nbsp;s y se estabiliza en {_platI:.0f}&nbsp;g; el pulgar aguanta {_holdT:.2f}&nbsp;s y acaba en {_platT:.0f}&nbsp;g. <b>Dos dedos, dos contactos distintos, rigideces que difieren 2.3×, y la misma meseta.</b> No es un objeto que se mueve ni una arista que resbala: es un límite de la mano. Los ~3000&nbsp;g de sobreimpulso del Exp 2 y los «≥30&nbsp;N» de la hoja de datos son <b>picos de impacto, no fuerza sostenible</b>.</div>

    <p>Debajo de ese techo la mano sí sostiene: a 450&nbsp;g, durante 60&nbsp;s, la fuerza cae solo un {_dropI:.0f}&nbsp;% en el índice y un {_dropT:.0f}&nbsp;% en el pulgar, y el actuador no cede (0 a −2 counts de movimiento con el comando congelado). <b>La consigna útil del lazo vive entre ~100 y ~{_plat:.0f}&nbsp;g</b>, y eso es lo que el diseño del regulador tiene que asumir.</p>

    <h3>La planta que el regulador controla</h3>

    <div class="tbl-wrap"><table><caption><b>Tabla 5.</b> Modelo de planta en contacto: del comando al cambio de fuerza, medido sobre muestras frescas (Exp 3, prueba E3.3).</caption>
      <thead><tr><th>Métrica</th><th>Índice</th><th>Pulgar</th></tr></thead>
      <tbody>
        <tr><td>Retardo comando → fuerza</td><td class="mono b">{_lagI:.0f} ms</td><td class="mono b">{_lagT:.0f} ms</td></tr>
        <tr><td>Constante de subida τ</td><td class="mono">≲ {_tauI:.0f} ms</td><td class="mono">≲ {_tauT:.0f} ms</td></tr>
        <tr><td>Asentamiento</td><td class="mono">{_setI:.0f} ms</td><td class="mono">{_setT:.0f} ms</td></tr>
        <tr><td>Cociente L/τ</td><td class="mono b">{_lagI/_tauI:.1f}</td><td class="mono b">{_lagT/_tauT:.1f}</td></tr>
      </tbody></table></div>

    <p><b>El contacto no añade retardo.</b> En espacio libre el Exp 1 midió ~64&nbsp;ms del comando al primer movimiento; en contacto son {_lagI:.0f}–{_lagT:.0f}&nbsp;ms del comando al primer cambio de fuerza. La planta que el regulador controla no es más lenta que la que ya se conocía.</p>

    <p>Pero <b>está dominada por el retardo</b>: con L/τ ≈ 1, subir la ganancia proporcional no acelera el lazo, lo hace oscilar. Y τ está <i>en</i> el límite de resolución del sistema —sus valores caen en múltiplos exactos del periodo de publicación de ~30.7&nbsp;ms—, así que <b>lo que limita al lazo es el refresco de la mano, no la mecánica</b>. El periodo de control no debe bajar de ~30&nbsp;ms: por debajo solo se reprocesan muestras repetidas.</p>

    <h3>Dos cosas que el regulador no puede ignorar</h3>

    <p><b>El firmware no sostiene fuerza.</b> Durante {_cycles} ciclos de sostenimiento de 60&nbsp;s en los dos dedos, la corriente del actuador fue <b>0&nbsp;mA</b>, siempre. No hay par activo: lo que retiene la fuerza es la fricción de la transmisión. Todo lo que el lazo quiera, lo tiene que poner el lazo — y la fuerza decae sola en los primeros segundos, lo que obliga a <b>fuga en el integrador</b>.</p>

    <p><b>El cero de fuerza se corre al sostener, y mucho más que por temperatura.</b> La deriva térmica de la tara es de 6–7&nbsp;g y satura. Pero tras sostener fuerza, el cero salta <b>{_jI:+.0f}&nbsp;g en el índice y {_jT:+.0f}&nbsp;g en el pulgar</b> —igual en frío que en caliente, de modo que es histéresis de carga, no temperatura— y tarda unos 8&nbsp;s en volver. La consecuencia práctica es una regla: <b>nunca re-tarar justo después de soltar</b>. Nótese que el signo es opuesto en cada dedo: no hay una corrección común, hay que medirla por grado de libertad.</p>

    <div class="callout"><b>Lección de método, otra vez sobre la ventana de medida.</b> Este trabajo concluyó primero que el colapso de fuerza era del índice y su montaje, porque el pulgar parecía sostener 944&nbsp;g. Era un artefacto: esa campaña leía la fuerza en ventanas de 0.30&nbsp;s, más cortas que las ~0.3&nbsp;s que el colapso tarda en empezar, de modo que medía dentro del tiempo de agarre. Con ventanas de 2&nbsp;s el pulgar hace exactamente lo mismo. <b>Una ventana más corta que el fenómeno no lo mide: lo esconde.</b></div>
  </section>

  <hr class="rule">

  <section>
    <h2>Conclusiones</h2>
    <ul>
      <li>El <b>sobreimpulso de fuerza es el riesgo dominante</b> al agarrar rápido: puede triplicar la fuerza deseada, lo que justifica una estrategia de aproximación híbrida.</li>
      <li>Bajar el umbral de fuerza <b>no es una alternativa</b>: por debajo de la fuerza de flexión propia del dedo el firmware frena sin llegar al objeto, y por encima no contiene el impacto.</li>
      <li>La <b>política híbrida queda validada</b>: reduce el sobreimpulso {min(_redI.values()):.0f}–{max(_redI.values()):.0f}× en el índice y {min(_redT.values()):.0f}–{max(_redT.values()):.0f}× en el pulgar, con un margen de conmutación (~124 counts) fijado experimentalmente, y se verificó después en los otros tres dedos.</li>
      <li>La plataforma entrega <b>~33 Hz de estado nuevo</b> por sensor —no los 98 de la tasa de lectura— y <b>~64 ms de latencia</b>, con movimiento lineal predecible. Suficiente para el control propuesto, pero fija el techo: ningún lazo puede reaccionar a información que aún no existe.</li>
      <li>La réplica en un <b>segundo dedo</b>, y la verificación en los otros tres, separan lo general de lo particular: la calibración de velocidad y la latencia son de la plataforma; <b>bajar el umbral de fuerza no protege en ninguno</b>. La política híbrida es la única que generaliza.</li>
      <li>La caracterización se <b>replicó por un segundo canal de comunicación</b> con nueve veces la tasa de muestreo: la física reproduce, lo que valida las campañas previas. Pero <b>ninguna de las tres mejoras de medida que se le atribuían era real</b>, y a cambio reveló por qué: la mano publica estado nuevo a ~33&nbsp;Hz, así que leer más rápido no añade información — y lo que parecían dos posiciones de contacto eran <b>dos escalones del registro de posición</b>.</li>
      <li>Un umbral de fuerza por debajo de la fuerza de flexión propia del dedo produce ensayos <b>sin contacto</b> que aparentan protección perfecta. Detectarlo exige comprobar que hubo carga, no leer el sobreimpulso: es la lección metodológica de este trabajo, y costó el hallazgo que se creía central.</li>
      <li>La mano tiene un <b>techo de fuerza sostenible en torno a {_plat:.0f}&nbsp;g</b>, medido en dos grados de libertad con contactos y rigideces distintos. Por encima, la fuerza es transitoria. Esto acota el alcance de cualquier regulador de fuerza que se monte sobre esta plataforma, y separa por primera vez la fuerza de <b>impacto</b> —que llega a los miles de gramos— de la fuerza que la mano puede <b>mantener</b>.</li>
      <li>El firmware <b>no aplica par para sostener</b>: 0&nbsp;mA durante 60&nbsp;s en {_cycles} ciclos. La fuerza la retiene la fricción de la transmisión, y decae. Un lazo de fuerza no puede delegar el sostenimiento en la mano: tiene que regularlo él, con fuga en el integrador para no perseguir una caída que ya paró.</li>
      <li>La planta en contacto está <b>dominada por el retardo</b> (L/τ ≈ 1) y su constante de tiempo está en el límite de resolución del sistema: <b>el refresco de ~33&nbsp;Hz, no la mecánica, es lo que limita al lazo</b>. Es el mismo techo que apareció en el Exp 0, ahora medido desde el otro extremo.</li>
    </ul>
    <p class="lead"><b>Próximos pasos:</b> los cinco grados de libertad están medidos y el régimen de contacto sostenido está caracterizado en los dos que forman la pinza, con la especificación del regulador ya cerrada: rango de consigna, escalón mínimo de comando, modelo de planta, política de integrador y cadencia de re-tara. Queda <b>medir el acoplamiento entre dedos en las pinzas reales</b> —pulgar+índice y pulgar+índice+medio— que es también el único ensayo que puede responder si los grados de libertad refrescan su estado en el mismo instante o escalonados. Y queda una condición de prueba por levantar: todas las campañas usan un objeto <b>apoyado</b> y contacto sobre <b>arista</b>; un objeto sujeto entre dos dedos es un contacto distinto y más blando, así que el techo de {_plat:.0f}&nbsp;g y las rigideces hay que re-verificarlos ahí.</p>
  </section>

  <p class="foot">Documento de trabajo — resultados iniciales de tesis. Datos, código y figuras reproducibles en el repositorio: <span class="mono">github.com/smorales2405/inspire_hand_interface</span>. Hardware: Inspire Hand RH56DFTP · comunicación Modbus RTU (RS-485) y Modbus TCP.</p>

</div>'''

open(DST,'w').write(HTML)
print("escrito:", DST, f"({len(HTML)} bytes)  k={k:.2f} kT={_kT:.2f}  R2min={r2min:.3f}  "
      f"svgs e1={len(e1)} e2={len(e2)} cmp={len(cmp_)} dist={len(dist)} tcp={len(tcpf)}")
