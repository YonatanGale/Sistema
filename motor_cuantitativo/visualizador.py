# motor_cuantitativo/visualizador.py
"""
Generador de gráficos con Plotly.
- Devuelve: PNG (para PDF) + JSON plano (para renderizar en el navegador).
- Omite automáticamente preguntas sin datos.
- SOLO genera gráficos de PASTEL por pregunta (barras deshabilitadas).
- Layout optimizado: leyenda debajo, ancho completo, título con wrap.
- FIX doble para bdata: engine='json' + deserializador manual de respaldo.
"""

import os
import re
import base64
import json
import unicodedata
import logging

import numpy as np
import pandas as pd

import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio

logger = logging.getLogger(__name__)

# ============================================
# ✅ FIX CRÍTICO: JSON plano en vez de bdata
# ============================================
pio.json.config.default_engine = 'json'


# ============================================
# CONFIGURACIÓN
# ============================================
COLORES_MIXTOS = [
    '#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6',
    '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b',
    '#27ae60', '#2980b9', '#8e44ad', '#d35400', '#f1c40f'
]

PNG_WIDTH = 1100
PNG_HEIGHT = 720
PNG_SCALE = 2

try:
    pio.kaleido.scope.default_format = "png"
except Exception:
    pass


# ============================================
# HELPERS
# ============================================
def _limpiar_nombre(texto, max_length=40):
    if not texto:
        return "sin_nombre"
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = texto.encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'[^a-zA-Z0-9_-]', '_', texto)
    texto = re.sub(r'_+', '_', texto).strip('_')
    if len(texto) > max_length:
        texto = texto[:max_length].rstrip('_')
    return texto or "sin_nombre"


def _preparar_directorio(directorio):
    os.makedirs(directorio, exist_ok=True)
    return directorio


def _colores_para_opciones(tipo, n):
    if tipo == 'escala_likert':
        base = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60']
        if n <= len(base):
            return base[:n]
    elif tipo == 'seleccion_si_no':
        return ['#2ecc71', '#e74c3c'][:n]
    return [COLORES_MIXTOS[i % len(COLORES_MIXTOS)] for i in range(n)]


def _tiene_datos(df_frec):
    if df_frec is None or df_frec.empty:
        return False
    return int(df_frec['Frecuencia'].sum()) > 0


def _wrap_texto(texto, ancho=65):
    """
    Inserta <br> en un texto largo para que Plotly lo muestre en varias líneas.
    Plotly NO hace wrap automático, hay que hacerlo manual.
    """
    if not texto:
        return ""
    palabras = str(texto).split()
    lineas = []
    actual = []
    largo = 0
    for palabra in palabras:
        if largo + len(palabra) + 1 > ancho and actual:
            lineas.append(' '.join(actual))
            actual = [palabra]
            largo = len(palabra)
        else:
            actual.append(palabra)
            largo += len(palabra) + 1
    if actual:
        lineas.append(' '.join(actual))
    return '<br>'.join(lineas)


def _exportar(fig, ruta_png):
    try:
        fig.write_image(ruta_png, width=PNG_WIDTH, height=PNG_HEIGHT, scale=PNG_SCALE)
        return True
    except Exception as e:
        logger.error(f"❌ kaleido no pudo exportar {ruta_png}: {e}")
        logger.error("   → Verifica: pip install kaleido")
        return False


# ============================================
# ✅ DESERIALIZADOR DE bdata (respaldo)
# ============================================
def _desbdataificar(obj):
    """
    Recorre recursivamente un dict/list y reemplaza cualquier
    {'dtype': 'i8', 'bdata': 'CgAAAA...'} por una lista Python normal.

    Esto es respaldo por si engine='json' no se aplica por algún motivo.
    """
    if isinstance(obj, dict):
        # ¿Es un bdata?
        if 'bdata' in obj and 'dtype' in obj:
            try:
                raw = base64.b64decode(obj['bdata'])
                dt = obj.get('dtype', 'i8')
                # Mapear dtype abreviado a numpy
                dtype_map = {
                    'i1': 'int8', 'i2': 'int16', 'i4': 'int32', 'i8': 'int64',
                    'u1': 'uint8', 'u2': 'uint16', 'u4': 'uint32', 'u8': 'uint64',
                    'f4': 'float32', 'f8': 'float64',
                }
                np_dtype = dtype_map.get(dt, dt)
                arr = np.frombuffer(raw, dtype=np_dtype)
                if obj.get('shape'):
                    try:
                        arr = arr.reshape(obj['shape'])
                    except Exception:
                        pass
                return arr.tolist()
            except Exception as e:
                logger.warning(f"bdata no decodificable: {e}")
                return []
        return {k: _desbdataificar(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_desbdataificar(x) for x in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        f = float(obj)
        return None if (np.isnan(f) or np.isinf(f)) else f
    return obj


def _fig_a_resultado(fig, ruta_png):
    """
    Exporta PNG y devuelve {png, plotly_json}.
    plotly_json es un dict JSON-safe con {'data': [...], 'layout': {...}}.

    Doble seguridad contra bdata:
      1) engine='json'
      2) _desbdataificar() si algo se coló
    """
    exito = _exportar(fig, ruta_png)
    plotly_json = None
    try:
        plotly_json = json.loads(fig.to_json(engine='json'))
        plotly_json = _desbdataificar(plotly_json)
    except Exception as e:
        logger.warning(f"No se pudo serializar figura a JSON: {e}")

    return {
        'png': ruta_png if exito else None,
        'plotly_json': plotly_json,
    }


# ============================================
# 1. PASTEL (único gráfico por pregunta)
# ============================================
def grafico_pastel_pregunta(pregunta, frecuencias, directorio, nombre_base):
    """
    Gráfico de pastel con la distribución porcentual.
    - Leyenda DEBAJO para no comerse el ancho.
    - Título con wrap manual (Plotly no lo hace solo).
    - Si hay > 8 opciones, agrupa las menores en "Otras (N categorías)".
    """
    df = frecuencias[frecuencias['Frecuencia'] > 0].copy()

    if df.empty:
        return None

    n_originales = len(df)

    # Agrupar si son demasiadas
    if n_originales > 8:
        df = df.sort_values('Frecuencia', ascending=False)
        top = df.head(7).copy()
        resto = df.iloc[7:]
        if not resto.empty:
            top = pd.concat([
                top,
                pd.DataFrame([{
                    'Opcion': f'Otras ({len(resto)} categorías)',
                    'Frecuencia': int(resto['Frecuencia'].sum()),
                    'Porcentaje': round(float(resto['Porcentaje'].sum()), 2),
                }])
            ], ignore_index=True)
        df = top

    colores = _colores_para_opciones(pregunta['tipo'], len(df))
    labels = df['Opcion'].astype(str).tolist()
    values = df['Frecuencia'].astype(int).tolist()

    # Título con wrap
    titulo_raw = f"P{pregunta['id']} · {pregunta['texto']}"
    if n_originales > 8:
        titulo_raw += f" (agrupado de {n_originales} opciones)"
    titulo_wrap = _wrap_texto(titulo_raw, ancho=70)

    # ✅ Usar go.Pie con listas puras para garantizar serialización
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        marker=dict(
            colors=colores,
            line=dict(color='white', width=2),
        ),
        textinfo='percent',
        textposition='inside',
        textfont=dict(size=13, color='white', family='DejaVu Sans'),
        insidetextorientation='horizontal',
        sort=False,
        direction='clockwise',
        hole=0.0,
    )])

    fig.update_layout(
        title=dict(
            text=titulo_wrap,
            x=0.5,
            xanchor='center',
            font=dict(size=14),
        ),
        font=dict(family="DejaVu Sans, Arial, sans-serif", size=11),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=720,
        margin=dict(l=40, r=40, t=120, b=180),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='top',
            y=-0.05,
            xanchor='center',
            x=0.5,
            font=dict(size=11),
            itemsizing='constant',
        ),
    )

    ruta = os.path.join(directorio, f"{nombre_base}_pastel.png")
    logger.info(f"  🥧 Pastel: {os.path.basename(ruta)} ({n_originales}→{len(df)})")
    return _fig_a_resultado(fig, ruta)


# ============================================
# 2. HISTOGRAMA LIKERT (solo si hay Likert)
# ============================================
def grafico_histograma_likert(pregunta, valores_numericos, directorio, nombre_base):
    valores = pd.to_numeric(valores_numericos, errors='coerce').dropna()
    if valores.empty:
        return None

    media = float(valores.mean())
    mediana = float(valores.median())

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=valores.tolist(),
        nbinsx=int(valores.max() - valores.min()) + 1,
        marker=dict(color='#3498db', line=dict(color='white', width=2)),
        name='Frecuencia',
    ))
    fig.add_vline(
        x=media, line_dash="dash", line_color="#e67e22",
        annotation_text=f"Media: {media:.2f}",
        annotation_position="top right",
    )
    fig.add_vline(
        x=mediana, line_dash="dash", line_color="#9b59b6",
        annotation_text=f"Mediana: {mediana:.2f}",
        annotation_position="bottom right",
    )

    titulo = f"P{pregunta['id']} · Distribución Likert<br>{_wrap_texto(pregunta['texto'], 70)}"
    fig.update_layout(
        title=dict(text=titulo, x=0.5, xanchor='center', font=dict(size=14)),
        font=dict(family="DejaVu Sans, Arial, sans-serif", size=11),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=620,
        margin=dict(l=70, r=40, t=120, b=80),
        xaxis_title="Valor",
        yaxis_title="Frecuencia",
        showlegend=False,
        bargap=0.15,
    )

    ruta = os.path.join(directorio, f"{nombre_base}_histograma.png")
    logger.info(f"  📈 Histograma: {os.path.basename(ruta)}")
    return _fig_a_resultado(fig, ruta)


# ============================================
# 3. BOXPLOT LIKERT
# ============================================
def grafico_boxplot_likert(df_numerico, metadata, directorio,
                            nombre_archivo='boxplot_likert.png'):
    preguntas = [p for p in metadata['preguntas'] if p['tipo'] == 'escala_likert']
    if len(preguntas) < 2:
        return None

    datos = []
    etiquetas = []
    for p in preguntas:
        col = f"P{p['id']}"
        if col not in df_numerico.columns:
            continue
        v = pd.to_numeric(df_numerico[col], errors='coerce').dropna()
        if len(v) > 0:
            datos.append(v.tolist())
            etiquetas.append(p['texto'][:40] + ('...' if len(p['texto']) > 40 else ''))

    if len(datos) < 2:
        return None

    fig = go.Figure()
    for i, (vals, etq) in enumerate(zip(datos, etiquetas)):
        fig.add_trace(go.Box(
            y=vals, name=etq,
            marker_color=COLORES_MIXTOS[i % len(COLORES_MIXTOS)],
            boxmean='sd',
        ))

    fig.update_layout(
        title=dict(text='Comparación Likert entre preguntas',
                   x=0.5, xanchor='center', font=dict(size=14)),
        font=dict(family="DejaVu Sans, Arial, sans-serif", size=11),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=620,
        margin=dict(l=70, r=40, t=120, b=140),
        showlegend=False,
    )

    ruta = os.path.join(directorio, nombre_archivo)
    logger.info(f"  📦 Boxplot: {nombre_archivo}")
    return _fig_a_resultado(fig, ruta)


# ============================================
# 4. HEATMAP CORRELACIONES
# ============================================
def grafico_heatmap_correlaciones(matriz, directorio,
                                   nombre_archivo='heatmap_correlaciones.png'):
    if matriz is None or matriz.empty or len(matriz) < 2:
        return None

    fig = px.imshow(
        matriz,
        color_continuous_scale='RdYlGn',
        zmin=-1, zmax=1,
        text_auto='.2f',
        aspect='auto',
    )
    fig.update_traces(textfont=dict(size=10))

    fig.update_layout(
        title=dict(text='Matriz de correlaciones (Spearman)',
                   x=0.5, xanchor='center', font=dict(size=14)),
        font=dict(family="DejaVu Sans, Arial, sans-serif", size=11),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=620,
        margin=dict(l=70, r=40, t=120, b=180),
        xaxis=dict(tickangle=-35, tickfont=dict(size=9)),
        yaxis=dict(tickfont=dict(size=9)),
        coloraxis_colorbar=dict(title="r"),
    )

    ruta = os.path.join(directorio, nombre_archivo)
    logger.info(f"  🔥 Heatmap: {nombre_archivo}")
    return _fig_a_resultado(fig, ruta)


# ============================================
# 5. BARRAS APILADAS
# ============================================
def grafico_barras_apiladas_comparativa(frecuencias_df, metadata, directorio,
                                         nombre_archivo='barras_apiladas_comparativa.png'):
    preguntas = [p for p in metadata['preguntas'] if p['tipo'] == 'escala_likert']
    if len(preguntas) < 2:
        return None

    filas = []
    for p in preguntas:
        df_p = frecuencias_df[frecuencias_df['Pregunta_ID'] == p['id']]
        if df_p.empty:
            continue
        for _, row in df_p.iterrows():
            filas.append({
                'Pregunta': p['texto'][:45],
                'Opcion': row['Opcion'],
                'Porcentaje': row['Porcentaje'],
            })

    if not filas:
        return None

    df = pd.DataFrame(filas)
    fig = px.bar(
        df, x='Porcentaje', y='Pregunta', color='Opcion',
        orientation='h',
        color_discrete_sequence=['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60'],
    )
    fig.update_layout(barmode='stack')

    fig.update_layout(
        title=dict(text='Comparación Likert (100% apilado)',
                   x=0.5, xanchor='center', font=dict(size=14)),
        font=dict(family="DejaVu Sans, Arial, sans-serif", size=11),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=max(500, len(df['Pregunta'].unique()) * 80),
        margin=dict(l=280, r=180, t=120, b=60),
        xaxis_title='Porcentaje (%)',
        legend=dict(orientation='v', x=1.02, y=1, xanchor='left'),
    )

    ruta = os.path.join(directorio, nombre_archivo)
    logger.info(f"  📊 Apiladas: {nombre_archivo}")
    return _fig_a_resultado(fig, ruta)


# ============================================
# 6. COMPARACIÓN GRUPOS
# ============================================
def grafico_comparacion_grupos(df_comparacion, pregunta_grupo, directorio,
                                nombre_archivo='comparacion_grupos.png'):
    if df_comparacion is None or df_comparacion.empty:
        return None

    cols = [c for c in df_comparacion.columns
            if c.startswith('P') and c not in ('Grupo', 'Identificador')]
    if not cols:
        return None

    df = df_comparacion[['Grupo']].copy()
    for c in cols:
        df[c] = pd.to_numeric(df_comparacion[c], errors='coerce')

    medias = df.groupby('Grupo')[cols].mean().reset_index()
    if medias.empty:
        return None

    largo = medias.melt(id_vars='Grupo', var_name='Pregunta', value_name='Media')
    largo = largo.dropna(subset=['Media'])

    if largo.empty:
        return None

    fig = px.bar(
        largo, x='Pregunta', y='Media', color='Grupo',
        barmode='group', text='Media',
        color_discrete_sequence=COLORES_MIXTOS,
    )
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')

    fig.update_layout(
        title=dict(text=f'Comparación por grupo<br>{_wrap_texto(pregunta_grupo, 70)}',
                   x=0.5, xanchor='center', font=dict(size=14)),
        font=dict(family="DejaVu Sans, Arial, sans-serif", size=11),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=580,
        margin=dict(l=70, r=160, t=140, b=120),
        legend=dict(orientation='v', x=1.02, y=1, xanchor='left'),
        xaxis_tickangle=-20,
    )

    ruta = os.path.join(directorio, nombre_archivo)
    logger.info(f"  📊 Grupos: {nombre_archivo}")
    return _fig_a_resultado(fig, ruta)


# ============================================
# 7. ÍNDICE SATISFACCIÓN
# ============================================
def grafico_indice_satisfaccion(indice, directorio,
                                 nombre_archivo='indice_satisfaccion.png'):
    df = indice.get('por_pregunta')
    if df is None or df.empty:
        return None

    df = df.copy()
    df['Pregunta_corta'] = df['Pregunta'].apply(
        lambda t: t[:55] + ('...' if len(t) > 55 else '')
    )
    df['color'] = df['Indice_Promedio'].apply(
        lambda v: '#2ecc71' if v >= 70 else ('#f1c40f' if v >= 50 else '#e74c3c')
    )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df['Indice_Promedio'].tolist(),
        y=df['Pregunta_corta'].tolist(),
        orientation='h',
        marker=dict(color=df['color'].tolist()),
        text=df['Indice_Promedio'].apply(lambda v: f'{v:.1f}').tolist(),
        textposition='outside',
    ))
    fig.add_vline(
        x=50, line_dash="dash", line_color="gray",
        annotation_text="Neutral", annotation_position="top",
    )
    fig.add_vline(
        x=70, line_dash="dash", line_color="green",
        annotation_text="Satisfactorio", annotation_position="top",
    )

    fig.update_layout(
        title=dict(text='Índice de satisfacción por pregunta',
                   x=0.5, xanchor='center', font=dict(size=14)),
        font=dict(family="DejaVu Sans, Arial, sans-serif", size=11),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=max(500, len(df) * 80),
        margin=dict(l=340, r=60, t=120, b=60),
        xaxis=dict(range=[0, 110], title='Índice (0-100)'),
        yaxis=dict(autorange='reversed'),
        showlegend=False,
    )

    ruta = os.path.join(directorio, nombre_archivo)
    logger.info(f"  📈 Índice: {nombre_archivo}")
    return _fig_a_resultado(fig, ruta)


# ============================================
# 8. HEATMAP CONTINGENCIA
# ============================================
def grafico_heatmap_contingencia(tabla, p1, p2, directorio,
                                  nombre_archivo='heatmap_contingencia.png'):
    if tabla is None or tabla.empty:
        return None

    fig = px.imshow(
        tabla,
        color_continuous_scale='Blues',
        text_auto=True,
        aspect='auto',
    )
    fig.update_traces(textfont=dict(size=10))

    fig.update_layout(
        title=dict(
            text=f'Contingencia<br>{_wrap_texto(p1, 40)} vs {_wrap_texto(p2, 40)}',
            x=0.5, xanchor='center', font=dict(size=13),
        ),
        font=dict(family="DejaVu Sans, Arial, sans-serif", size=11),
        plot_bgcolor="white",
        paper_bgcolor="white",
        height=560,
        margin=dict(l=70, r=40, t=140, b=140),
        xaxis=dict(tickangle=-30, tickfont=dict(size=9), title=p2[:60]),
        yaxis=dict(tickfont=dict(size=9), title=p1[:60]),
    )

    ruta = os.path.join(directorio, nombre_archivo)
    logger.info(f"  🔥 Contingencia: {nombre_archivo}")
    return _fig_a_resultado(fig, ruta)


# ============================================
# GENERADOR MASIVO
# ============================================
def generar_todos_los_graficos(
    metadata,
    df_numerico,
    df_categorico,
    frecuencias_df,
    correlaciones_result,
    grupos_result,
    indice_result,
    directorio,
    incluir_html=True,   # ← se ignora (compat con llamadas viejas)
):
    """
    Genera los gráficos.
    ✅ SOLO PASTEL por pregunta (barras deshabilitadas).
    """
    _preparar_directorio(directorio)
    graficos = {}
    omitidos = []

    logger.info("🎨 Generando gráficos (Plotly + kaleido) — solo pastel...")

    for pregunta in metadata['preguntas']:
        pid = pregunta['id']
        df_preg = frecuencias_df[frecuencias_df['Pregunta_ID'] == pid]

        if not _tiene_datos(df_preg):
            logger.info(f"  ⏭️  P{pid} sin datos → se omite")
            omitidos.append(pid)
            continue

        nombre_base = f"P{pid}_{_limpiar_nombre(pregunta['texto'])}"

        res_pastel = grafico_pastel_pregunta(
            pregunta, df_preg, directorio, nombre_base
        )
        if res_pastel:
            graficos[f'P{pid}_pastel'] = res_pastel

        if pregunta['tipo'] == 'escala_likert':
            col = f"P{pid}"
            if col in df_numerico.columns:
                v = pd.to_numeric(df_numerico[col], errors='coerce')
                if v.notna().sum() > 0:
                    res_hist = grafico_histograma_likert(
                        pregunta, v, directorio, nombre_base
                    )
                    if res_hist:
                        graficos[f'P{pid}_histograma'] = res_hist

    res = grafico_boxplot_likert(df_numerico, metadata, directorio)
    if res:
        graficos['boxplot_likert'] = res

    res = grafico_barras_apiladas_comparativa(frecuencias_df, metadata, directorio)
    if res:
        graficos['barras_apiladas'] = res

    matriz = correlaciones_result.get('matriz') if correlaciones_result else None
    if matriz is not None and not matriz.empty and len(matriz) >= 2:
        res = grafico_heatmap_correlaciones(matriz, directorio)
        if res:
            graficos['heatmap_correlaciones'] = res

    df_comp = grupos_result.get('df_comparacion') if grupos_result else None
    if df_comp is not None and not df_comp.empty:
        res = grafico_comparacion_grupos(
            df_comp,
            grupos_result.get('grupo_pregunta', ''),
            directorio,
        )
        if res:
            graficos['comparacion_grupos'] = res

    if indice_result and indice_result.get('indice_global') is not None:
        res = grafico_indice_satisfaccion(indice_result, directorio)
        if res:
            graficos['indice_satisfaccion'] = res

    logger.info(f"✅ {len(graficos)} gráficos generados, {len(omitidos)} omitidos")
    return {
        'graficos': graficos,
        'omitidos': omitidos,
    }