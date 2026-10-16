# motor_cuantitativo/runner.py
"""
Script de línea de comandos para ejecutar el motor cuantitativo
sobre un archivo CSV generado por el sistema de encuestas.

Uso:
    python runner.py <ruta_csv> [opciones]

Ejemplos:
    python runner.py ../exports/cuantitativo_1_20261012.csv
    python runner.py ../exports/cuantitativo_1.csv --sin-graficos
    python runner.py ../exports/cuantitativo_1.csv --grupo 3
"""

import sys
import os
import argparse
import logging

# Asegurar que el directorio actual esté en el path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from analizador_cuantitativo import AnalizadorCuantitativo


def configurar_logging(verbose=False):
    """Configura el logging."""
    nivel = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=nivel,
        format='%(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def mostrar_banner():
    """Muestra el banner del runner."""
    print("\n" + "=" * 65)
    print("  📊 MOTOR DE ANÁLISIS CUANTITATIVO - RUNNER")
    print("  Análisis estadístico desde CSV")
    print("=" * 65)


def main():
    parser = argparse.ArgumentParser(
        description='Ejecuta el motor cuantitativo sobre un CSV de encuestas.'
    )
    parser.add_argument(
        'ruta_csv',
        help='Ruta al archivo CSV generado por el sistema de encuestas'
    )
    parser.add_argument(
        '--grupo', '-g',
        type=int,
        default=None,
        help='ID de la pregunta a usar como grupo para comparación'
    )
    parser.add_argument(
        '--sin-graficos',
        action='store_true',
        help='No generar gráficos PNG'
    )
    parser.add_argument(
        '--sin-excel',
        action='store_true',
        help='No generar archivo Excel'
    )
    parser.add_argument(
        '--sin-json',
        action='store_true',
        help='No generar archivo JSON'
    )
    parser.add_argument(
        '--salida', '-s',
        default='data/resultados',
        help='Directorio de salida (default: data/resultados)'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Modo verbose (más logs)'
    )
    
    args = parser.parse_args()
    
    configurar_logging(args.verbose)
    mostrar_banner()
    
    # Validar archivo
    if not os.path.exists(args.ruta_csv):
        print(f"\n❌ ERROR: No se encontró el archivo: {args.ruta_csv}")
        sys.exit(1)
    
    print(f"\n📂 Archivo CSV: {args.ruta_csv}")
    print(f"⚙️  Configuración:")
    print(f"   - Directorio salida: {args.salida}")
    print(f"   - Gráficos: {'No' if args.sin_graficos else 'Sí'}")
    print(f"   - Excel: {'No' if args.sin_excel else 'Sí'}")
    print(f"   - JSON: {'No' if args.sin_json else 'Sí'}")
    if args.grupo:
        print(f"   - Grupo: pregunta P{args.grupo}")
    
    try:
        analizador = AnalizadorCuantitativo(directorio_resultados=args.salida)
        
        resultados = analizador.analizar_completo(
            ruta_csv=args.ruta_csv,
            generar_graficos=not args.sin_graficos,
            guardar_excel=not args.sin_excel,
            guardar_json=not args.sin_json,
            n_grupos=args.grupo
        )
        
        # ============================================
        # MOSTRAR RESUMEN DE ARCHIVOS GENERADOS
        # ============================================
        print("\n" + "=" * 65)
        print("📁 ARCHIVOS GENERADOS")
        print("=" * 65)
        
        archivos = resultados.get('archivos', {})
        
        if 'excel' in archivos:
            print(f"\n📊 Excel: {archivos['excel']}")
        
        if 'json' in archivos:
            print(f"📄 JSON: {archivos['json']}")
        
        if 'graficos' in archivos:
            print(f"\n🎨 Gráficos ({len(archivos['graficos'])}):")
            for nombre, ruta in archivos['graficos'].items():
                print(f"   • {nombre}: {os.path.basename(ruta)}")
        
        print("\n" + "=" * 65)
        print("✅ ANÁLISIS COMPLETADO EXITOSAMENTE")
        print("=" * 65)
        
    except Exception as e:
        print(f"\n❌ ERROR durante el análisis: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()