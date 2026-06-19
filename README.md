# Inspire Hand RH56DFTP — Interface de Control PyQt5

Interfaz gráfica para el control y visualización de la mano robótica **Inspire Hand RH56DFTP** (6 DOF, 12 joints, grip máximo 30 N). Comunicación directa por **Modbus RTU/TCP** sin dependencia de DDS ni middleware adicional.

---

## Características

| Pestaña | Descripción |
|---|---|
| **Control y Ángulos** | Sliders por DOF, lectura en tiempo real de ángulos, gestos predefinidos (Abrir, Cerrar, Señalar, Pinza, Pulgar arriba), control de velocidad |
| **Lectura Fuerzas** | Silueta de la mano con mapa de calor por FORCE_ACT, barras verticales por DOF y curvas temporales (ventana 20 s) |
| **Sensores Táctiles** | Vista anatómica de 17 zonas táctiles clicables con coloreado por valor medio de taxel; panel de detalle con grilla de taxeles y estadísticas |

---

## Requisitos

### Python

**Python 3.9 o superior** (probado con Python 3.10).

### Dependencias

Instala los paquetes con `pip`:

```bash
pip install PyQt5>=5.15 pymodbus==3.6.9 pyserial>=3.5
```

| Paquete | Versión mínima | Uso |
|---|---|---|
| `PyQt5` | 5.15 | Interfaz gráfica |
| `pymodbus` | **3.6.9** | Comunicación Modbus RTU/TCP |
| `pyserial` | 3.5 | Puerto serial (RS-485) |

> **Nota:** `pymodbus` **3.6.9** es la versión requerida. Versiones anteriores usan una API diferente (`method='rtu'` en `ModbusSerialClient`) que causará errores.

No se requieren `numpy`, `pyqtgraph` ni ningún middleware DDS.

---

## Instalación

```bash
# Clonar el repositorio
git clone https://github.com/smorales2405/inspire_hand_interface.git
cd inspire_hand_interface

# Instalar dependencias
pip install PyQt5>=5.15 pymodbus==3.6.9 pyserial>=3.5
```

---

## Uso

Ejecutar desde la carpeta `inspire_hand_interface/`:

```bash
cd inspire_hand_interface
python main.py
```

La interfaz se abre sin necesidad de conectar la mano; las secciones de lectura simplemente no mostrarán datos hasta que se establezca la conexión.

### Conexión TCP (por defecto)

```
IP:    192.168.11.210
Puerto: 6000
```

### Conexión Serial (RS-485)

```
Puerto: /dev/ttyUSB0  (Linux)  o  COM3  (Windows)
Baud:   115200
```

Selecciona el modo de conexión en el panel superior de la pestaña **Control y Ángulos**.

---

## Estructura del proyecto

```
inspire_hand_interface/
├── main.py                        # Punto de entrada
├── core/
│   ├── hand_connection.py         # Wrapper Modbus (TCP + Serial)
│   ├── angle_converter.py         # Conversión registros ↔ grados por DOF
│   └── tactile_zones.py           # Definiciones de las 17 zonas táctiles
└── ui/
    ├── main_window.py             # Ventana principal con 3 pestañas
    ├── tabs/
    │   ├── control_tab.py         # Pestaña 1: control y ángulos
    │   ├── force_tab.py           # Pestaña 2: fuerzas
    │   └── tactile_tab.py         # Pestaña 3: sensores táctiles
    └── widgets/
        ├── finger_widget.py       # Widget de control por DOF
        ├── gesture_panel.py       # Panel de gestos predefinidos
        ├── hand_silhouette_widget.py   # Silueta con mapa de calor
        ├── force_bar_widget.py    # Barra vertical de fuerza por DOF
        ├── force_plot_widget.py   # Curvas temporales de FORCE_ACT
        ├── tactile_overview_widget.py  # Vista anatómica clicable
        └── tactile_detail_widget.py    # Grilla de taxeles por zona
```

---

## Rangos de los DOF

| DOF | Articulación | Rango (grados) | Registro 0 → 1000 |
|---|---|---|---|
| 0 | Meñique | 176.7° → 19.0° | Cerrado → Abierto |
| 1 | Anular | 176.7° → 19.0° | Cerrado → Abierto |
| 2 | Medio | 176.7° → 19.0° | Cerrado → Abierto |
| 3 | Índice | 176.7° → 19.0° | Cerrado → Abierto |
| 4 | Pulgar (flex.) | 53.6° → −13.0° | Cerrado → Abierto |
| 5 | Pulgar (rot.) | 165° → 90° | Abducción → Aducción |

---

## Zonas táctiles

17 zonas Modbus (registros 3000–5012) con taxeles de 16 bits con signo:

| Zona | Taxeles | Grid |
|---|---|---|
| Punta (×5 dedos) | 9 | 3 × 3 |
| Distal (×5 dedos) | 96 | 12 × 8 |
| Palmar/Medio (×5) | 80 / 96 | 10×8 / 12×8 |
| Palma | 112 | 14 × 8 |

Las lecturas de las 17 zonas se realizan en un `QThread` en segundo plano (~5 Hz) para no bloquear la interfaz.

---

## Hardware compatible

- **Mano:** Inspire Hand RH56DFTP (derecha)
- **Interfaces probadas:** Modbus TCP y Modbus RTU sobre RS-485
- **SO:** Linux (Ubuntu 20.04 / 22.04), Windows 10/11

---

## Licencia

MIT
