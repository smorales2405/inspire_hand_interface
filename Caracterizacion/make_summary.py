#!/usr/bin/env python3
"""Arma el documento-resumen de la caracterización (HTML) embebiendo las figuras."""
import csv, json, os, re, statistics

REPO=os.path.dirname(os.path.abspath(__file__))
DST=os.path.join(REPO,'RESUMEN_caracterizacion.html')

def svgs(path):
    return re.findall(r'<svg\b.*?</svg>', open(path).read(), re.S)

e1=svgs(os.path.join(REPO,'exp1/figures/exp1_step_response.html'))
e2=svgs(os.path.join(REPO,'exp2/figures/exp2_force_overshoot.html'))
overlay, slope, latency = e1[0], e1[1], e1[2]
bars, compare = e2[0], e2[1]

# pendiente ∝ v (constante k) desde el análisis
by=list(csv.DictReader(open(os.path.join(REPO,'exp1/data/analysis_by_speed.csv'))))
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
grid=json.load(open(os.path.join(REPO,'exp2/data/exp2_overshoot_grid.json')))
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
    <p class="abstract">Se caracterizó experimentalmente la respuesta dinámica de la mano robótica Inspire RH56DFTP (comunicación Modbus RTU a 115 200 baud) con experimentos de <b>hardware en el lazo</b>. El hallazgo central: el <b>sobreimpulso de fuerza</b> al cerrar los dedos está dominado por la velocidad de cierre —llega a <b>triplicar la fuerza deseada</b>— y una estrategia de aproximación <b>híbrida</b> (rápida hasta el borde del contacto, luego lenta) lo reduce <b>~68×</b>. Se cuantificaron además la latencia comando→sensor, la respuesta al escalón y la repetibilidad del contacto para fijar los parámetros de dicha estrategia.</p>
  </header>

  <div class="kpis">
    <div class="kpi"><div class="n">98.3<span class="u"> Hz</span></div><div class="l">realimentación de fuerza sostenida (0 errores)</div></div>
    <div class="kpi"><div class="n">~64<span class="u"> ms</span></div><div class="l">latencia comando→sensor (indep. de la velocidad)</div></div>
    <div class="kpi"><div class="n">~3300<span class="u"> g</span></div><div class="l">sobreimpulso de fuerza al cerrar rápido</div></div>
    <div class="kpi"><div class="n">~68<span class="u">×</span></div><div class="l">reducción del sobreimpulso con la política híbrida</div></div>
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
    <h3>La plataforma sostiene ≥ 98 Hz de realimentación</h3>
    <p>Se leyó el bloque de los 6 registros de fuerza en lazo cerrado (3×2000 lecturas). Tasa media <b>98.3 Hz</b> con <b>0 errores</b> en 6000 lecturas. El techo lo impone el firmware de la mano y el bus, no el software. Esto fija la <b>resolución temporal (~10 ms)</b> de todo lo demás y confirma que la plataforma es adecuada para el control propuesto.</p>
  </section>

  <hr class="rule">

  <section>
    <h2>Exp 1 <span class="tag">respuesta al escalón · espacio libre</span></h2>
    <h3>Movimiento lineal con la velocidad y retardo fijo, sin sobreimpulso de posición</h3>
    <p>El dedo índice ejecuta un escalón de posición <b>en el aire</b> (sin objeto), a cinco velocidades × 20 repeticiones, muestreando la posición del actuador a ~90 Hz. Resultados: (i) el <b>retardo comando→sensor es ≈ 64 ms e independiente de la velocidad</b>; (ii) la velocidad del dedo <b>escala linealmente con el setpoint</b> (pendiente ≈ <span class="mono">{k:.2f} × v</span>, <span class="mono">R² ≥ {r2min:.2f}</span>), es decir, crecimiento lineal sin deceleración; (iii) el <b>sobreimpulso de posición es ≈ 0</b>.</p>
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
    <p>La yema del índice cierra contra un <b>bloque rígido</b>; se mide el sobreimpulso <span class="mono">ΔF = F_max − Fset</span> en función de la velocidad y del setpoint de fuerza (5 réplicas por celda). Resultados: (i) el sobreimpulso <b>crece dramáticamente con la velocidad</b> — a alta velocidad el impacto de la yema alcanza <b>~3300 g (≈33 N)</b>, casi independiente del setpoint, superando el techo de seguridad; (ii) con un <b>setpoint bajo</b> (100 g) el firmware frena antes de golpear y el sobreimpulso queda <b>≤ 36 g</b> a toda velocidad; (iii) la <b>política híbrida</b> —aproximación rápida hasta el borde del contacto y luego cierre lento— <b>colapsa el sobreimpulso ~68×</b>, al nivel del cierre lento, alcanzando el setpoint sin impactos.</p>
    <figure>
      {bars}
      <figcaption><b>Figura 2.</b> Sobreimpulso de fuerza por celda (velocidad × setpoint). ▲ marca los impactos que superaron el techo de seguridad de 2200 g. Con setpoint 100 g el sobreimpulso queda plano y bajo.</figcaption>
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
    <p>Para fijar el punto en que la política híbrida cambia a cierre lento, se midió la <b>posición de primer contacto</b> en 50 toques suaves a máxima velocidad. La <b>repetibilidad mecánica del contacto es excelente</b> (σ ~5–8 counts, comparable a la literatura). A máxima velocidad la resolución de posición por muestra domina la σ medida (~37 counts), de la cual se deriva un <b>margen de conmutación de ~124 counts</b>: la mano entra al cierre lento ~124 counts <b>antes</b> del contacto esperado, garantizando un toque suave. Este margen se re-mide por montaje.</p>
  </section>

  <hr class="rule">

  <section>
    <h2>Conclusiones</h2>
    <ul>
      <li>El <b>sobreimpulso de fuerza es el riesgo dominante</b> al agarrar rápido: puede triplicar la fuerza deseada, lo que justifica una estrategia de aproximación híbrida.</li>
      <li>La <b>política híbrida queda validada</b>: reduce el sobreimpulso ~68×, con un margen de conmutación (~124 counts) fijado experimentalmente.</li>
      <li>La plataforma sostiene <b>≥ 98 Hz de realimentación</b> y <b>~64 ms de latencia</b>, con movimiento lineal predecible — adecuada para el control propuesto.</li>
    </ul>
    <p class="lead"><b>Próximos pasos:</b> campaña completa (mayor N por celda), extensión a los demás dedos, e integración de la política híbrida en el lazo de agarre.</p>
  </section>

  <p class="foot">Documento de trabajo — resultados iniciales de tesis. Datos, código y figuras reproducibles en el repositorio: <span class="mono">github.com/smorales2405/inspire_hand_interface</span>. Hardware: Inspire Hand RH56DFTP · comunicación Modbus RTU.</p>

</div>'''

open(DST,'w').write(HTML)
print("escrito:", DST, f"({len(HTML)} bytes)  k={k:.2f}  R2min={r2min:.3f}  svgs e1={len(e1)} e2={len(e2)}")
