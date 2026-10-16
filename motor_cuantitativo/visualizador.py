# motor_cuantitativo/visualizador.py
"""
Generador de gráficos para el análisis cuantitativo.
Todos los gráficos se guardan como PNG de alta resolución.
Compatible con matplotlib 3.9+ (tick_labels) y versiones anteriores (labels).
Adapta automáticamente el tamaño según el número de opciones.
Usa barras horizontales para preguntas con muchas opciones.
"""

import os
import re
import unicodedata
import matplotlib
matplotlib.use('Agg')  # Backend sin GUI
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

# Estilo consistente para todos los gráficos
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 12
plt.rcParams['axes.titleweight'] = 'bold'

# Paleta de colores consistente
COLORES_POSITIVOS = ['#2ecc71', '#27ae60']
COLORES_NEGATIVOS = ['#e74c3c', '#c0392b']
COLORES_NEUTROS = ['#95a5a6', '#7f8c8d']
COLORES_MIXTOS = [
    '#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6',
    '#1abc9c', '#e67e22', '#34495e', '#16a085', '#c0392b',
    '#27ae60', '#2980b9', '#8e44ad', '#d35400', '#f1c40f'
]


def _limpiar_nombre(texto, max_length=40):
    """Limpia un texto para usarlo en nombres de archivo."""
    if not texto:
        return "sin_nombre"
    texto = unicodedata.normalize('NFKD', str(texto))
    texto = texto.encode('ASCII', 'ignore').decode('ASCII')
    texto = re.sub(r'[^a-zA-Z0-9_-]', '_', texto)
    texto = re.sub(r'_+', '_', texto)
    texto = texto.strip('_')
    if len(texto) > max_length:
        texto = texto[:max_length].rstrip('_')
    return texto if texto else "sin_nombre"


def _preparar_directorio(directorio):
    """Crea el directorio si no existe."""
    os.makedirs(directorio, exist_ok=True)
    return directorio


def _colores_para_opciones(tipo, n_opciones, opciones=None):
    """
    Devuelve una lista de colores según el tipo de pregunta.
    """
    if tipo == 'escala_likert':
        colores_likert = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60']
        if n_opciones <= len(colores_likert):
            return colores_likert[:n_opciones]
        return COLORES_MIXTOS[:n_opciones]
    
    elif tipo == 'seleccion_si_no':
        return ['#2ecc71', '#e74c3c'][:n_opciones]
    
    # Para muchas opciones, ciclar la paleta
    colores = []
    for i in range(n_opciones):
        colores.append(COLORES_MIXTOS[i % len(COLORES_MIXTOS)])
    return colores


# ============================================
# 1. GRÁFICO DE BARRAS POR PREGUNTA
# ============================================

def grafico_barras_pregunta(pregunta, frecuencias, directorio, nombre_base):
    """
    Genera un gráfico de barras con las frecuencias de cada opción.
    - <= 10 opciones: barras VERTICALES
    - > 10 opciones: barras HORIZONTALES (más legibles)
    """
    n_opciones = len(frecuencias)
    
    # ✅ SI HAY MUCHAS OPCIONES, USAR BARRAS HORIZONTALES
    if n_opciones > 10:
        return _grafico_barras_horizontales(pregunta, frecuencias, directorio, nombre_base)
    
    # ============================================
    # BARRAS VERTICALES (pocas opciones)
    # ============================================
    if n_opciones <= 5:
        figsize = (10, 6)
        fontsize_etiquetas = 11
        rotacion = 0
    else:  # 6-10
        figsize = (11, 6)
        fontsize_etiquetas = 10
        rotacion = 30
    
    fig, ax = plt.subplots(figsize=figsize)
    
    opciones = frecuencias['Opcion'].tolist()
    valores = frecuencias['Frecuencia'].tolist()
    porcentajes = frecuencias['Porcentaje'].tolist()
    
    opciones_cortas = [
        (o[:35] + '...') if len(o) > 35 else o
        for o in opciones
    ]
    
    colores = _colores_para_opciones(pregunta['tipo'], len(opciones), opciones)
    barras = ax.bar(range(len(opciones)), valores, color=colores, edgecolor='white', linewidth=2)
    
    fontsize_valor = 10
    for barra, valor, pct in zip(barras, valores, porcentajes):
        height = barra.get_height()
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            height + 0.3,
            f'{valor}\n({pct}%)',
            ha='center', va='bottom',
            fontsize=fontsize_valor, fontweight='bold'
        )
    
    ax.set_xticks(range(len(opciones)))
    ax.set_xticklabels(
        opciones_cortas,
        rotation=rotacion,
        ha='right' if rotacion > 0 else 'center',
        fontsize=fontsize_etiquetas
    )
    ax.set_ylabel('Frecuencia', fontweight='bold')
    ax.set_title(f"Distribución de respuestas\n{pregunta['texto'][:70]}", pad=15, fontsize=12)
    
    if max(valores) > 0:
        ax.set_ylim(0, max(valores) * 1.18)
    
    plt.tight_layout()
    
    nombre_archivo = f"{nombre_base}_barras.png"
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  📊 Barras verticales: {nombre_archivo} ({n_opciones} opciones)")
    return ruta


def _grafico_barras_horizontales(pregunta, frecuencias, directorio, nombre_base):
    """
    ✅ NUEVO: Barras HORIZONTALES para preguntas con muchas opciones.
    Es mucho más legible y permite etiquetas largas.
    """
    n_opciones = len(frecuencias)
    
    # ✅ Ordenar por frecuencia ascendente (más común arriba en gráfico)
    df_ordenado = frecuencias.sort_values('Frecuencia', ascending=True).reset_index(drop=True)
    
    opciones = df_ordenado['Opcion'].tolist()
    valores = df_ordenado['Frecuencia'].tolist()
    porcentajes = df_ordenado['Porcentaje'].tolist()
    
    # ✅ Altura adaptativa: ~0.4cm por opción, mín 8, máx 20
    altura = max(8, min(20, n_opciones * 0.4 + 3))
    
    fig, ax = plt.subplots(figsize=(12, altura))
    
    # ✅ Truncar etiquetas largas
    opciones_cortas = [
        (o[:45] + '...') if len(o) > 45 else o
        for o in opciones
    ]
    
    colores = _colores_para_opciones(pregunta['tipo'], len(opciones), opciones)
    
    # ✅ Barras horizontales
    y_pos = range(len(opciones))
    barras = ax.barh(y_pos, valores, color=colores, edgecolor='white', linewidth=1.5)
    
    # ✅ Etiquetas a la derecha de cada barra
    max_valor = max(valores) if valores else 1
    for barra, valor, pct in zip(barras, valores, porcentajes):
        ax.text(
            valor + max_valor * 0.01,
            barra.get_y() + barra.get_height() / 2,
            f'{valor} ({pct}%)',
            va='center', ha='left',
            fontsize=9, fontweight='bold'
        )
    
    ax.set_yticks(y_pos)
    ax.set_yticklabels(opciones_cortas, fontsize=9)
    ax.set_xlabel('Frecuencia', fontweight='bold')
    ax.set_title(
        f"Distribución de respuestas ({n_opciones} opciones)\n{pregunta['texto'][:70]}",
        pad=15, fontsize=12
    )
    ax.set_xlim(0, max_valor * 1.2)
    ax.grid(True, axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    nombre_archivo = f"{nombre_base}_barras.png"
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  📊 Barras horizontales: {nombre_archivo} ({n_opciones} opciones)")
    return ruta


# ============================================
# 2. GRÁFICO DE PASTEL
# ============================================

def grafico_pastel_pregunta(pregunta, frecuencias, directorio, nombre_base):
    """
    Genera un gráfico de pastel con la distribución porcentual.
    Si hay muchas opciones, agrupa las menores en "Otras".
    """
    # Filtrar opciones con frecuencia > 0
    df = frecuencias[frecuencias['Frecuencia'] > 0].copy()
    
    if len(df) == 0:
        return None
    
    if len(df) == 1:
        return grafico_barras_pregunta(pregunta, frecuencias, directorio, nombre_base)
    
    n_opciones_originales = len(df)
    
    # ✅ SI HAY MÁS DE 8 OPCIONES, AGRUPAR LAS MENORES EN "OTRAS"
    if n_opciones_originales > 8:
        df = df.sort_values('Frecuencia', ascending=False)
        
        top_df = df.head(7).copy()
        resto_df = df.iloc[7:]
        
        frecuencia_otras = resto_df['Frecuencia'].sum()
        porcentaje_otras = resto_df['Porcentaje'].sum()
        
        if frecuencia_otras > 0:
            nueva_fila = pd.DataFrame([{
                'Opcion': f'Otras ({len(resto_df)} categorías)',
                'Frecuencia': frecuencia_otras,
                'Porcentaje': round(porcentaje_otras, 2)
            }])
            df = pd.concat([top_df, nueva_fila], ignore_index=True)
    
    # ✅ ADAPTAR TAMAÑO SEGÚN N° DE OPCIONES MOSTRADAS
    n_final = len(df)
    if n_final <= 4:
        figsize = (9, 7)
    elif n_final <= 6:
        figsize = (10, 8)
    else:
        figsize = (12, 9)
    
    fig, ax = plt.subplots(figsize=figsize)
    
    opciones = df['Opcion'].tolist()
    valores = df['Frecuencia'].tolist()
    
    # ✅ TRUNCAR ETIQUETAS LARGAS
    opciones_cortas = [
        (o[:40] + '...') if len(o) > 40 else o
        for o in opciones
    ]
    
    colores = _colores_para_opciones(pregunta['tipo'], len(opciones), opciones)
    
    wedges, texts, autotexts = ax.pie(
        valores,
        labels=None,
        colors=colores,
        autopct=lambda pct: f'{pct:.1f}%' if pct >= 3 else '',
        startangle=90,
        counterclock=False,
        wedgeprops={'edgecolor': 'white', 'linewidth': 2},
        textprops={'fontsize': 10, 'fontweight': 'bold'}
    )
    
    # ✅ LEYENDA CON ETIQUETAS CORTAS
    etiquetas = [f'{op} ({val})' for op, val in zip(opciones_cortas, valores)]
    ax.legend(
        wedges, etiquetas,
        loc='center left',
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=9 if n_final > 6 else 10
    )
    
    titulo_extra = f" (agrupado de {n_opciones_originales} opciones)" if n_opciones_originales > 8 else ""
    ax.set_title(f"Distribución porcentual{titulo_extra}\n{pregunta['texto'][:70]}", pad=15, fontsize=12)
    ax.axis('equal')
    
    plt.tight_layout()
    
    nombre_archivo = f"{nombre_base}_pastel.png"
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  🥧 Pastel: {nombre_archivo} ({n_opciones_originales}→{n_final} opciones)")
    return ruta


# ============================================
# 3. HISTOGRAMA DE LIKERT
# ============================================

def grafico_histograma_likert(pregunta, valores_numericos, directorio, nombre_base):
    """
    Genera un histograma de valores Likert con curva de densidad.
    """
    valores = valores_numericos.dropna().values
    
    if len(valores) == 0:
        return None
    
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Histograma
    bins = np.arange(valores.min() - 0.5, valores.max() + 1.5, 1)
    n, bins_edges, patches = ax.hist(
        valores,
        bins=bins,
        color='#3498db',
        edgecolor='white',
        linewidth=2,
        alpha=0.75,
        density=False
    )
    
    # Colorear barras según posición en la escala
    max_val = valores.max()
    for i, patch in enumerate(patches):
        valor_centro = (bins_edges[i] + bins_edges[i+1]) / 2
        if valor_centro <= max_val * 0.4:
            patch.set_facecolor('#e74c3c')
        elif valor_centro <= max_val * 0.6:
            patch.set_facecolor('#f1c40f')
        else:
            patch.set_facecolor('#2ecc71')
    
    # Líneas de media y mediana
    media = valores.mean()
    mediana = np.median(valores)
    
    ax.axvline(media, color='#e67e22', linestyle='--', linewidth=2, label=f'Media: {media:.2f}')
    ax.axvline(mediana, color='#9b59b6', linestyle='--', linewidth=2, label=f'Mediana: {mediana:.2f}')
    
    ax.set_xlabel('Valor (escala Likert)', fontweight='bold')
    ax.set_ylabel('Frecuencia', fontweight='bold')
    ax.set_title(f"Distribución de respuestas Likert\n{pregunta['texto'][:70]}", pad=15, fontsize=12)
    ax.legend()
    
    plt.tight_layout()
    
    nombre_archivo = f"{nombre_base}_histograma.png"
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  📈 Histograma: {nombre_archivo}")
    return ruta


# ============================================
# 4. BOXPLOT DE PREGUNTAS LIKERT
# ============================================

def grafico_boxplot_likert(df_numerico, metadata, directorio, nombre_archivo='boxplot_likert.png'):
    """
    Boxplot comparativo de todas las preguntas Likert.
    Compatible con matplotlib 3.9+ (tick_labels) y versiones anteriores (labels).
    """
    preguntas_likert = [p for p in metadata['preguntas'] if p['tipo'] == 'escala_likert']
    
    if len(preguntas_likert) < 2:
        return None
    
    # Preparar datos
    datos = []
    etiquetas = []
    for p in preguntas_likert:
        col = f"P{p['id']}"
        if col not in df_numerico.columns:
            continue
        valores = pd.to_numeric(df_numerico[col], errors='coerce').dropna()
        if len(valores) > 0:
            datos.append(valores.values)
            etq = p['texto'][:35] + '...' if len(p['texto']) > 35 else p['texto']
            etiquetas.append(etq)
    
    if not datos:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    # ✅ COMPATIBILIDAD CON MATPLOTLIB 3.9+ (tick_labels) Y VERSIONES ANTIGUAS (labels)
    try:
        bp = ax.boxplot(
            datos,
            tick_labels=etiquetas,
            patch_artist=True,
            notch=False,
            showmeans=True,
            meanprops={'marker': 'D', 'markerfacecolor': 'white', 'markeredgecolor': 'black', 'markersize': 8}
        )
    except TypeError:
        bp = ax.boxplot(
            datos,
            labels=etiquetas,
            patch_artist=True,
            notch=False,
            showmeans=True,
            meanprops={'marker': 'D', 'markerfacecolor': 'white', 'markeredgecolor': 'black', 'markersize': 8}
        )
    
    # Colores consistentes
    colores = ['#3498db', '#2ecc71', '#f39c12', '#e74c3c', '#9b59b6', '#1abc9c']
    for patch, color in zip(bp['boxes'], colores):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)
    
    ax.set_ylabel('Valor Likert', fontweight='bold')
    ax.set_title('Comparación de respuestas Likert entre preguntas', pad=15, fontsize=12)
    ax.grid(True, axis='y', alpha=0.3)
    
    plt.xticks(rotation=15, ha='right')
    plt.tight_layout()
    
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  📦 Boxplot: {nombre_archivo}")
    return ruta


# ============================================
# 5. MAPA DE CALOR DE CORRELACIONES
# ============================================

def grafico_heatmap_correlaciones(matriz_corr, directorio, nombre_archivo='heatmap_correlaciones.png'):
    """
    Genera un mapa de calor con la matriz de correlaciones.
    Se adapta al número de preguntas.
    """
    if matriz_corr.empty or len(matriz_corr) < 2:
        return None
    
    n = len(matriz_corr)
    # ✅ ADAPTAR TAMAÑO SEGÚN N° DE PREGUNTAS
    tamaño = max(10, min(20, n * 0.8 + 4))
    
    fig, ax = plt.subplots(figsize=(tamaño, tamaño * 0.85))
    
    mask = np.triu(np.ones_like(matriz_corr, dtype=bool), k=1)
    
    fontsize_annot = max(7, min(11, 14 - n // 2))
    
    sns.heatmap(
        matriz_corr,
        mask=mask,
        annot=True,
        fmt='.2f',
        cmap='RdYlGn',
        center=0,
        vmin=-1,
        vmax=1,
        square=True,
        linewidths=1,
        cbar_kws={'shrink': 0.8, 'label': 'Correlación de Spearman'},
        ax=ax,
        annot_kws={'fontsize': fontsize_annot, 'fontweight': 'bold'}
    )
    
    ax.set_title('Matriz de correlaciones entre preguntas', pad=20, fontsize=13, fontweight='bold')
    plt.xticks(rotation=45, ha='right', fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    
    plt.tight_layout()
    
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  🔥 Heatmap: {nombre_archivo}")
    return ruta


# ============================================
# 6. GRÁFICO DE BARRAS APILADAS (COMPARATIVA)
# ============================================

def grafico_barras_apiladas_comparativa(frecuencias_df, metadata, directorio, nombre_archivo='barras_apiladas_comparativa.png'):
    """
    Barras apiladas 100% comparando todas las preguntas Likert.
    """
    preguntas_likert = [p for p in metadata['preguntas'] if p['tipo'] == 'escala_likert']
    
    if len(preguntas_likert) < 2:
        return None
    
    datos = {}
    for p in preguntas_likert:
        df_p = frecuencias_df[frecuencias_df['Pregunta_ID'] == p['id']]
        if df_p.empty:
            continue
        
        opciones = df_p['Opcion'].tolist()
        porcentajes = df_p['Porcentaje'].tolist()
        
        etq = p['texto'][:40] + '...' if len(p['texto']) > 40 else p['texto']
        datos[etq] = dict(zip(opciones, porcentajes))
    
    if not datos:
        return None
    
    df_plot = pd.DataFrame(datos).T.fillna(0)
    
    n_preguntas = len(df_plot)
    altura = max(6, min(14, n_preguntas * 0.8 + 3))
    
    fig, ax = plt.subplots(figsize=(12, altura))
    
    colores = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#27ae60']
    
    df_plot.plot(
        kind='barh',
        stacked=True,
        color=colores[:len(df_plot.columns)],
        ax=ax,
        edgecolor='white',
        linewidth=1
    )
    
    ax.set_xlabel('Porcentaje (%)', fontweight='bold')
    ax.set_title('Comparación 100% apilado de preguntas Likert', pad=15, fontsize=12)
    ax.legend(title='Respuesta', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9)
    ax.set_xlim(0, 100)
    ax.grid(True, axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  📊 Barras apiladas: {nombre_archivo}")
    return ruta


# ============================================
# 7. GRÁFICO DE COMPARACIÓN ENTRE GRUPOS
# ============================================

def grafico_comparacion_grupos(df_comparacion, pregunta_grupo, directorio, nombre_archivo='comparacion_grupos.png'):
    """
    Barras agrupadas comparando las medias por grupo.
    Corregido: fuerza conversión a numérico antes del groupby.
    """
    if df_comparacion.empty:
        return None
    
    columnas_preguntas = [
        c for c in df_comparacion.columns 
        if c.startswith('P') and c not in ['Grupo', 'Identificador']
    ]
    
    if not columnas_preguntas:
        return None
    
    # ✅ FORZAR CONVERSIÓN A NUMÉRICO
    df_num = df_comparacion[['Grupo']].copy()
    for col in columnas_preguntas:
        df_num[col] = pd.to_numeric(df_comparacion[col], errors='coerce')
    
    columnas_validas = [c for c in columnas_preguntas if df_num[c].notna().sum() > 0]
    
    if not columnas_validas:
        logger.warning("  ⚠️ No hay columnas numéricas válidas para comparar grupos")
        return None
    
    medias = df_num.groupby('Grupo')[columnas_validas].mean()
    
    if medias.empty:
        return None
    
    n_preguntas = len(columnas_validas)
    ancho = max(10, min(16, n_preguntas * 1.2 + 4))
    
    fig, ax = plt.subplots(figsize=(ancho, 7))
    
    medias.T.plot(
        kind='bar',
        ax=ax,
        color=COLORES_MIXTOS[:len(medias)],
        edgecolor='white',
        linewidth=1.5
    )
    
    ax.set_xlabel('Pregunta', fontweight='bold')
    ax.set_ylabel('Media', fontweight='bold')
    ax.set_title(f"Comparación de medias por grupo\nBasado en: {pregunta_grupo[:70]}", pad=15, fontsize=12)
    ax.legend(title='Grupo', bbox_to_anchor=(1.02, 1), loc='upper left', fontsize=9)
    ax.grid(True, axis='y', alpha=0.3)
    
    plt.xticks(rotation=15, ha='right', fontsize=9)
    plt.tight_layout()
    
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  📊 Comparación grupos: {nombre_archivo}")
    return ruta


# ============================================
# 8. GRÁFICO DE ÍNDICE DE SATISFACCIÓN
# ============================================

def grafico_indice_satisfaccion(indice_satisfaccion, directorio, nombre_archivo='indice_satisfaccion.png'):
    """
    Gráfico de barras con el índice de satisfacción por pregunta.
    """
    df = indice_satisfaccion.get('por_pregunta')
    
    if df is None or df.empty:
        return None
    
    n_preguntas = len(df)
    altura = max(5, min(12, n_preguntas * 0.7 + 3))
    
    fig, ax = plt.subplots(figsize=(11, altura))
    
    etiquetas = [t[:45] + '...' if len(t) > 45 else t for t in df['Pregunta'].tolist()]
    valores = df['Indice_Promedio'].tolist()
    
    colores = []
    for v in valores:
        if v >= 70:
            colores.append('#2ecc71')
        elif v >= 50:
            colores.append('#f1c40f')
        else:
            colores.append('#e74c3c')
    
    barras = ax.barh(range(len(etiquetas)), valores, color=colores, edgecolor='white', linewidth=2)
    
    for barra, valor in zip(barras, valores):
        ax.text(valor + 1, barra.get_y() + barra.get_height() / 2,
                f'{valor:.1f}', va='center', fontsize=10, fontweight='bold')
    
    ax.set_yticks(range(len(etiquetas)))
    ax.set_yticklabels(etiquetas, fontsize=9)
    ax.set_xlabel('Índice de satisfacción (0-100)', fontweight='bold')
    ax.set_title('Índice de satisfacción por pregunta', pad=15, fontsize=12)
    ax.set_xlim(0, 105)
    ax.axvline(50, color='gray', linestyle='--', alpha=0.5, label='Neutral')
    ax.axvline(70, color='green', linestyle='--', alpha=0.5, label='Satisfactorio')
    ax.legend(loc='lower right')
    ax.grid(True, axis='x', alpha=0.3)
    
    plt.tight_layout()
    
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  📈 Índice satisfacción: {nombre_archivo}")
    return ruta


# ============================================
# 9. HEATMAP DE TABLA DE CONTINGENCIA
# ============================================

def grafico_heatmap_contingencia(tabla_contingencia, pregunta1, pregunta2, directorio, nombre_archivo='heatmap_contingencia.png'):
    """
    Heatmap de una tabla de contingencia.
    """
    if tabla_contingencia is None or tabla_contingencia.empty:
        return None
    
    n_filas = len(tabla_contingencia)
    n_cols = len(tabla_contingencia.columns)
    tamaño = max(8, min(16, max(n_filas, n_cols) * 0.8 + 4))
    
    fig, ax = plt.subplots(figsize=(tamaño, tamaño * 0.85))
    
    sns.heatmap(
        tabla_contingencia,
        annot=True,
        fmt='d',
        cmap='Blues',
        linewidths=1,
        cbar_kws={'label': 'Frecuencia'},
        ax=ax,
        annot_kws={'fontsize': 10, 'fontweight': 'bold'}
    )
    
    ax.set_title(
        f"Tabla de contingencia\n{pregunta1[:45]}  vs  {pregunta2[:45]}",
        pad=15,
        fontsize=11
    )
    ax.set_xlabel(pregunta2[:60], fontweight='bold')
    ax.set_ylabel(pregunta1[:60], fontweight='bold')
    
    plt.xticks(rotation=30, ha='right', fontsize=9)
    plt.yticks(rotation=0, fontsize=9)
    
    plt.tight_layout()
    
    ruta = os.path.join(directorio, nombre_archivo)
    plt.savefig(ruta, dpi=130, bbox_inches='tight', facecolor='white')
    plt.close()
    
    logger.info(f"  🔥 Contingencia: {nombre_archivo}")
    return ruta


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
    directorio
):
    """
    Genera todos los gráficos posibles y devuelve un dict con las rutas.
    """
    _preparar_directorio(directorio)
    graficos = {}
    
    logger.info("🎨 Generando gráficos...")
    
    # 1. Barras y pastel por pregunta
    for pregunta in metadata['preguntas']:
        df_preg = frecuencias_df[frecuencias_df['Pregunta_ID'] == pregunta['id']]
        if df_preg.empty:
            continue
        
        nombre_base = f"P{pregunta['id']}_{_limpiar_nombre(pregunta['texto'])}"
        
        # Barras
        ruta_barras = grafico_barras_pregunta(pregunta, df_preg, directorio, nombre_base)
        if ruta_barras:
            graficos[f'P{pregunta["id"]}_barras'] = ruta_barras
        
        # Pastel (solo si no son muchas opciones, o agrupado)
        if len(df_preg) <= 15 or len(df_preg[df_preg['Frecuencia'] > 0]) <= 15:
            ruta_pastel = grafico_pastel_pregunta(pregunta, df_preg, directorio, nombre_base)
            if ruta_pastel:
                graficos[f'P{pregunta["id"]}_pastel'] = ruta_pastel
        
        # Histograma para Likert
        if pregunta['tipo'] == 'escala_likert':
            col = f"P{pregunta['id']}"
            if col in df_numerico.columns:
                valores = pd.to_numeric(df_numerico[col], errors='coerce')
                ruta_hist = grafico_histograma_likert(pregunta, valores, directorio, nombre_base)
                if ruta_hist:
                    graficos[f'P{pregunta["id"]}_histograma'] = ruta_hist
    
    # 2. Boxplot Likert
    ruta_boxplot = grafico_boxplot_likert(df_numerico, metadata, directorio)
    if ruta_boxplot:
        graficos['boxplot_likert'] = ruta_boxplot
    
    # 3. Barras apiladas
    ruta_apiladas = grafico_barras_apiladas_comparativa(frecuencias_df, metadata, directorio)
    if ruta_apiladas:
        graficos['barras_apiladas'] = ruta_apiladas
    
    # 4. Heatmap correlaciones
    if correlaciones_result and not correlaciones_result.get('matriz', pd.DataFrame()).empty:
        ruta_heat = grafico_heatmap_correlaciones(correlaciones_result['matriz'], directorio)
        if ruta_heat:
            graficos['heatmap_correlaciones'] = ruta_heat
    
    # 5. Comparación de grupos
    if grupos_result and not grupos_result.get('df_comparacion', pd.DataFrame()).empty:
        ruta_grupos = grafico_comparacion_grupos(
            grupos_result['df_comparacion'],
            grupos_result.get('grupo_pregunta', ''),
            directorio
        )
        if ruta_grupos:
            graficos['comparacion_grupos'] = ruta_grupos
    
    # 6. Índice de satisfacción
    if indice_result and indice_result.get('indice_global') is not None:
        ruta_indice = grafico_indice_satisfaccion(indice_result, directorio)
        if ruta_indice:
            graficos['indice_satisfaccion'] = ruta_indice
    
    logger.info(f"✅ {len(graficos)} gráficos generados")
    
    return graficos