#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prueba unificada del sistema de búsqueda avanzada con LLM.
Este script combina todas las pruebas en una sola, con opciones para ejecutar
escenarios específicos o consultas individuales.
"""

import time
import os
import argparse
import json
import logging
from colorama import init, Fore, Style
from helpers.llm_search import procesar_consulta_completa
from helpers.error_handler import ErrorHandler, LLMError, SQLError, ConsultaError, DatosError
from helpers.logger import Logger, log_consulta, log_respuesta, log_metrica, log_error
from helpers.semantic_cache import semantic_cache
from helpers.llm_normalizer import limpiar_cache_normalizacion
from config import SEMANTIC_CACHE_ENABLED

# Inicializar colorama para colores en la terminal
init()

# Limpiar caché de normalización para aplicar nuevos cambios
limpiar_cache_normalizacion()

# Limpiar caché semántico
semantic_cache.cache = {}

# Mostrar mensaje de limpieza de caché
print(f"{Fore.GREEN}✅ Caché de normalización y caché semántico limpiados para aplicar nuevos cambios{Style.RESET_ALL}")

# Mostrar estado del caché semántico
if SEMANTIC_CACHE_ENABLED:
    print(f"{Fore.GREEN}ℹ️ Caché semántico HABILITADO. Las consultas similares se recuperarán del caché.{Style.RESET_ALL}")
else:
    print(f"{Fore.YELLOW}ℹ️ Caché semántico DESHABILITADO. Todas las consultas se procesarán completamente.{Style.RESET_ALL}")

# Obtener instancia del logger
logger = Logger.get_logger()

# Importar configuración centralizada
from config import DB_PATH

# Directorio para resultados de pruebas
RESULTADOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados_pruebas")
if not os.path.exists(RESULTADOS_DIR):
    os.makedirs(RESULTADOS_DIR)

def mostrar_titulo(texto):
    """Muestra un título con formato."""
    print(f"\n{Fore.YELLOW}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{texto}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'=' * 80}{Style.RESET_ALL}")

def mostrar_subtitulo(texto):
    """Muestra un subtítulo con formato."""
    print(f"\n{Fore.CYAN}{'-' * 60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{texto}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'-' * 60}{Style.RESET_ALL}")

def ejecutar_consulta(consulta, contexto=None, mostrar_tiempos=False, escenario=None):
    """
    Ejecuta una consulta y muestra la respuesta final.

    Args:
        consulta (str): Consulta a ejecutar
        contexto (dict): Contexto de la consulta anterior
        mostrar_tiempos (bool): Si se deben mostrar los tiempos de ejecución
        escenario (str): Nombre del escenario (para logging)

    Returns:
        dict: Contexto para la siguiente consulta
    """
    # Registrar inicio de la consulta
    logger.info(f"Ejecutando consulta: {consulta}")

    # Detalles para el log
    detalles_log = {
        "escenario": escenario,
        "con_contexto": contexto is not None
    }

    # Pedir al usuario que presione Enter para continuar o 's' para saltar
    respuesta = input(f"\n{Fore.YELLOW}Presiona Enter para ejecutar la consulta o 's' para saltar: \"{consulta}\"{Style.RESET_ALL}")
    if respuesta.lower() == 's':
        print(f"{Fore.RED}Consulta omitida.{Style.RESET_ALL}")
        logger.info(f"Consulta omitida: {consulta}")
        log_metrica("consulta_omitida", 1, detalles_log)
        return contexto

    print(f"\n{Fore.GREEN}👤 Consulta: {consulta}{Style.RESET_ALL}")

    # Registrar la consulta en el log
    log_consulta(consulta, detalles_log)

    # Medir tiempo total
    inicio_total = time.time()

    try:
        # Usar la función centralizada para procesar la consulta
        resultado_procesamiento = procesar_consulta_completa(consulta, contexto, DB_PATH, mostrar_tiempos, 1)

        # Extraer componentes del resultado
        estrategia = resultado_procesamiento.get("estrategia", {})
        resultado_sql = resultado_procesamiento.get("resultado_sql", {"total": 0, "registros": []})
        respuesta_texto = resultado_procesamiento["respuesta"]
        error = resultado_procesamiento.get("error")

        # Calcular tiempo total
        fin_total = time.time()
        tiempo_total = fin_total - inicio_total

        # Registrar métricas
        log_metrica("tiempo_ejecucion_prueba", tiempo_total, {
            "escenario": escenario,
            "consulta": consulta,
            "resultados": resultado_sql.get("total", 0)
        })

        # Mostrar respuesta
        print(f"\n{Fore.BLUE}🤖 Respuesta:{Style.RESET_ALL}")
        print(respuesta_texto)

        if mostrar_tiempos:
            print(f"\n{Fore.GREEN}Tiempo total: {tiempo_total:.2f} segundos{Style.RESET_ALL}")

        # Registrar la respuesta
        log_respuesta(consulta, respuesta_texto, tiempo_total, resultado_procesamiento.get("from_cache", False))

        # Guardar resultado en archivo JSON para análisis posterior
        if escenario:
            resultado_archivo = {
                "escenario": escenario,
                "consulta": consulta,
                "respuesta": respuesta_texto,
                "tiempo": tiempo_total,
                "resultados": resultado_sql.get("total", 0),
                "timestamp": time.time()
            }

            # Crear nombre de archivo basado en timestamp
            archivo_resultado = os.path.join(RESULTADOS_DIR, f"resultado_{int(time.time())}.json")
            with open(archivo_resultado, 'w', encoding='utf-8') as f:
                json.dump(resultado_archivo, f, ensure_ascii=False, indent=2)

        # Crear contexto para la siguiente consulta
        contexto_siguiente = {
            "consulta_anterior": consulta,
            "estrategia_anterior": estrategia,
            "resultados_anteriores": resultado_sql.get("registros", []) if resultado_sql.get("total", 0) > 0 else [],
            "respuesta_anterior": respuesta_texto,
            "historial_consultas": contexto.get("historial_consultas", []) + [consulta] if contexto else [consulta],
            "historial_respuestas": contexto.get("historial_respuestas", []) + [respuesta_texto] if contexto else [respuesta_texto]
        }

        return contexto_siguiente

    except Exception as e:
        # Manejar errores con el sistema centralizado
        error_info = ErrorHandler.handle_error(e, "PRUEBA", mostrar_traceback=True)
        log_error(f"Error al ejecutar consulta: {consulta}", e, detalles_log)

        # Mostrar mensaje de error
        print(f"\n{Fore.RED}❌ Error: {error_info['mensaje']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Mensaje para usuario: {ErrorHandler.get_user_message(error_info)}{Style.RESET_ALL}")

        # Calcular tiempo total en caso de error
        fin_total = time.time()
        tiempo_total = fin_total - inicio_total

        if mostrar_tiempos:
            print(f"\n{Fore.RED}Tiempo hasta error: {tiempo_total:.2f} segundos{Style.RESET_ALL}")

        # Registrar métrica de error
        log_metrica("error_consulta", 1, {
            "escenario": escenario,
            "consulta": consulta,
            "tipo_error": error_info["tipo"],
            "tiempo": tiempo_total
        })

        # Mantener el contexto anterior
        return contexto

def ejecutar_escenario(titulo, consultas, mostrar_tiempos=False):
    """
    Ejecuta un escenario de prueba con varias consultas relacionadas.

    Args:
        titulo (str): Título del escenario
        consultas (list): Lista de consultas a ejecutar
        mostrar_tiempos (bool): Si se deben mostrar los tiempos de ejecución
    """
    # Registrar inicio del escenario
    logger.info(f"Iniciando escenario: {titulo}")
    log_metrica("escenario_iniciado", 1, {"titulo": titulo, "consultas": len(consultas)})

    # Tiempo de inicio del escenario
    inicio_escenario = time.time()

    # Pedir al usuario que presione Enter para continuar o 's' para saltar
    respuesta = input(f"\n{Fore.YELLOW}Presiona Enter para ejecutar el escenario o 's' para saltar: \"{titulo}\"{Style.RESET_ALL}")
    if respuesta.lower() == 's':
        print(f"{Fore.RED}Escenario omitido.{Style.RESET_ALL}")
        logger.info(f"Escenario omitido: {titulo}")
        log_metrica("escenario_omitido", 1, {"titulo": titulo})
        return

    mostrar_titulo(titulo)

    try:
        contexto = None
        consultas_ejecutadas = 0

        for i, consulta in enumerate(consultas):
            # Ejecutar la consulta con el contexto actual
            contexto = ejecutar_consulta(consulta, contexto, mostrar_tiempos, titulo)

            if contexto is None:  # Si se omitió la consulta
                continue

            consultas_ejecutadas += 1
            print("\n")

        # Calcular tiempo total del escenario
        tiempo_escenario = time.time() - inicio_escenario

        # Registrar finalización del escenario
        logger.info(f"Escenario completado: {titulo} - {consultas_ejecutadas}/{len(consultas)} consultas ejecutadas en {tiempo_escenario:.2f} segundos")
        log_metrica("escenario_completado", 1, {
            "titulo": titulo,
            "consultas_ejecutadas": consultas_ejecutadas,
            "consultas_totales": len(consultas),
            "tiempo_total": tiempo_escenario
        })

        if mostrar_tiempos:
            print(f"\n{Fore.GREEN}Tiempo total del escenario: {tiempo_escenario:.2f} segundos{Style.RESET_ALL}")

    except Exception as e:
        # Manejar errores con el sistema centralizado
        error_info = ErrorHandler.handle_error(e, "ESCENARIO", mostrar_traceback=True)
        log_error(f"Error en escenario: {titulo}", e, {"titulo": titulo})

        # Mostrar mensaje de error
        print(f"\n{Fore.RED}❌ Error en escenario: {error_info['mensaje']}{Style.RESET_ALL}")

        # Calcular tiempo hasta el error
        tiempo_escenario = time.time() - inicio_escenario

        if mostrar_tiempos:
            print(f"\n{Fore.RED}Tiempo hasta error: {tiempo_escenario:.2f} segundos{Style.RESET_ALL}")

# Definir escenarios de prueba reorganizados
ESCENARIOS = [
    {
        "id": 1,
        "titulo": "PRUEBA DE CACHÉ SEMÁNTICO",
        "descripcion": "Consultas similares para probar el caché semántico con normalización LLM",
        "consultas": [
            # Primera consulta - se procesará completamente
            "¿Cuál es el teléfono de Luis Pérez?",

            # Segunda consulta - debería recuperarse del caché (misma información, diferente formulación)
            "¿Me puedes dar el número de Luis Pérez?",

            # Tercera consulta - debería recuperarse del caché (misma información, diferente formulación)
            "¿Cuál es el celular de Luis Pérez Ibáñez?",

            # Cuarta consulta - debería recuperarse del caché (misma información, con errores ortográficos)
            "dame el telefono de luiz perez",

            # Quinta consulta - diferente información, no debería recuperarse del caché
            "¿Cuál es el correo electrónico de Luis Pérez?",

            # Sexta consulta - diferente persona, no debería recuperarse del caché
            "¿Cuál es el teléfono de José Angel Alvarado?",

            # Séptima consulta - similar a la quinta, debería recuperarse del caché
            "¿Me puedes dar el email de Luis Pérez?"
        ]
    },
    {
        "id": 10,
        "titulo": "PRUEBA DE CACHÉ SEMÁNTICO PARA DIVERSOS TIPOS DE DATOS",
        "descripcion": "Consultas sobre diferentes tipos de datos y encabezados de la base de datos",
        "consultas": [
            # Datos laborales
            "¿Cuál es la función específica de Luis Pérez?",
            "¿Qué cargo tiene Luis Pérez?",

            # Datos académicos
            "¿Cuál es el nivel de estudios de Luis Pérez?",
            "¿Qué estudió Luis Pérez?",

            # Datos administrativos
            "¿Luis Pérez tiene doble plaza?",
            "¿Tiene doble plaza Luis Pérez?",

            # Datos de ubicación laboral
            "¿En qué centro de trabajo está Luis Pérez?",
            "¿Dónde trabaja Luis Pérez?",

            # Datos de antigüedad
            "¿Cuándo ingresó Luis Pérez?",
            "¿Cuál es la fecha de ingreso de Luis Pérez?",

            # Consultas de listado
            "Dame todos los docentes de la zona 109",
            "Lista los maestros de la zona 109",

            # Consultas estadísticas
            "¿Cuántos docentes hay en la zona 109?",
            "¿Cuál es el número de maestros en la zona 109?"
        ]
    },
    {
        "id": 2,
        "titulo": "DATOS PERSONALES COMPLETOS",
        "descripcion": "Consultas sobre información personal, contacto, documentos y estado civil",
        "consultas": [
            "¿Quién es Luis Pérez Ibáñez?",
            "¿Cuál es el nombre completo de José Angel?",
            "¿Cuál es el CURP de Luis Pérez?",
            "¿Cuál es el RFC de José Angel Alvarado?",
            "¿Cuál es el estado civil de Luis Pérez?",
            "¿Cuál es el teléfono particular de José Angel Alvarado?",
            "¿Cuál es el celular de Luis Pérez?",
            "¿Cuál es el correo electrónico de José Angel Alvarado?",
            "¿Dónde vive Luis Pérez?"
        ]
    },
    {
        "id": 3,
        "titulo": "INFORMACIÓN LABORAL Y ACADÉMICA",
        "descripcion": "Consultas sobre trabajo, estudios, antigüedad y ubicación laboral",
        "consultas": [
            "¿Cuál es la función específica de Luis Pérez?",
            "¿En qué centro de trabajo está José Angel Alvarado?",
            "¿Qué estudios tiene Luis Pérez?",
            "¿Cuándo ingresó José Angel Alvarado a la SEP?",
            "¿A qué sector pertenece Luis Pérez?",
            "¿En qué zona trabaja José Angel Alvarado?",
            "¿Cuál es la modalidad del centro de trabajo de Luis Pérez?",
            "¿Quién tiene más antigüedad, Luis Pérez o José Angel Alvarado?"
        ]
    },
    {
        "id": 4,
        "titulo": "CLAVES Y DATOS ADMINISTRATIVOS",
        "descripcion": "Consultas sobre claves de centros de trabajo, doble plaza y datos administrativos",
        "consultas": [
            "¿Luis Pérez tiene doble plaza?",
            "¿Cuál es la clave del centro de trabajo donde labora José Angel Alvarado?",
            "¿Cuál es la clave del centro de trabajo donde cobra Luis Pérez?",
            "¿Cuál es la clave presupuestal de José Angel Alvarado?",
            "¿Cuál es el teléfono del centro de trabajo de Luis Pérez?",
            "¿Hay diferencia entre la clave donde labora y donde cobra José Angel Alvarado?",
            "¿Quiénes tienen doble plaza?"
        ]
    },
    {
        "id": 5,
        "titulo": "BÚSQUEDAS FLEXIBLES Y ERRORES",
        "descripcion": "Consultas con errores ortográficos, nombres parciales o incompletos",
        "consultas": [
            "dame el telefono de luiz perez",
            "quien es jose anjel",
            "informacion de peres ibañes",
            "dame el telefono de luis",
            "informacion de perez",
            "dame el correo de alvarado",
            "cual es la funcion de jose"
        ]
    },
    {
        "id": 6,
        "titulo": "LISTADOS Y FILTROS",
        "descripcion": "Consultas que piden listar personas por diferentes criterios",
        "consultas": [
            "muestra todos los docentes",
            "dame todos los números de teléfono de los directores",
            "lista todos los correos electrónicos de los directores",
            "muestra todos los que trabajan en la zona 109",
            "¿quiénes tienen maestría?",
            "¿cuántas personas tienen doble plaza?",
            "busca personas casadas que trabajen en el sector 13",
            "¿quiénes son docentes con licenciatura?"
        ]
    },
    {
        "id": 7,
        "titulo": "CONSULTAS ESTADÍSTICAS Y COMPARATIVAS",
        "descripcion": "Consultas que piden información estadística o comparaciones",
        "consultas": [
            "¿Cuántas personas hay en la base de datos?",
            "¿Cuántos docentes hay?",
            "¿Cuántas personas tienen más de 10 años de antigüedad?",
            "¿Qué porcentaje de personas tienen maestría?",
            "¿Quién tiene más antigüedad, el director o el supervisor?",
            "Compara los estudios de Luis Pérez y José Angel Alvarado",
            "¿Quién tiene un puesto más alto, Luis Pérez o José Angel Alvarado?"
        ]
    },
    {
        "id": 8,
        "titulo": "MANTENIMIENTO DE CONTEXTO",
        "descripcion": "Consultas de seguimiento que dependen del contexto o lo cambian",
        "consultas": [
            "¿Quién es el director?",
            "¿Cuál es su correo electrónico?",
            "¿Y su número de teléfono?",
            "¿Dónde trabaja él?",
            "¿Tiene estudios de maestría?",
            "Ahora dime quién es José Angel Alvarado",
            "¿Cuál es su función?",
            "¿Y su correo electrónico?"
        ]
    },
    {
        "id": 9,
        "titulo": "CONSULTAS COMPLEJAS MULTI-CONDICIÓN",
        "descripcion": "Consultas con múltiples condiciones y criterios combinados",
        "consultas": [
            "busca personas casadas que trabajen en la zona 109",
            "muestra todas las personas que ingresaron antes del 2010 y tienen maestría",
            "¿quiénes son directores con más de 15 años de antigüedad?",
            "dame los nombres y teléfonos de todos los que tienen doble plaza y trabajan en el sector 13",
            "¿cuántos docentes tienen licenciatura y trabajan en la zona 109?",
            "¿quiénes tienen maestría y son subdirectores?",
            "muestra la información completa de los directores que tienen doble plaza"
        ]
    }
]

def main():
    """Función principal del script de prueba."""
    # Registrar inicio de la prueba
    logger.info("Iniciando prueba unificada del sistema de búsqueda avanzada con LLM")

    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Prueba unificada del sistema de búsqueda avanzada con LLM.')
    parser.add_argument('--escenario', type=int, help='ID del escenario a ejecutar (1-10)')
    parser.add_argument('--list', '--listar', action='store_true', help='Listar todos los escenarios disponibles')
    parser.add_argument('--interactive', '--interactivo', action='store_true',
                        help='Modo interactivo para seleccionar un escenario de la lista')
    parser.add_argument('--consulta', type=str, help='Consulta específica a ejecutar')
    parser.add_argument('--tiempos', action='store_true', help='Mostrar tiempos de ejecución')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO',
                        help='Nivel de detalle del log en consola (por defecto: INFO)')
    parser.add_argument('--no-cache', action='store_true', help='Desactivar el caché semántico para esta ejecución')
    args = parser.parse_args()

    # Configurar nivel de log en consola según el argumento
    if args.log_level:
        # Obtener el nivel de log correspondiente
        nivel_log = getattr(logging, args.log_level)

        # Actualizar nivel de log en los handlers de consola
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                handler.setLevel(nivel_log)
                logger.info(f"Nivel de log en consola establecido a: {args.log_level}")

    # Procesar argumento --no-cache
    if args.no_cache:
        # Desactivar el caché semántico para esta ejecución
        semantic_cache.enabled = False
        print(f"{Fore.YELLOW}ℹ️ Caché semántico DESHABILITADO por argumento --no-cache{Style.RESET_ALL}")

    # Registrar opciones de ejecución
    log_metrica("opciones_ejecucion", 1, {
        "escenario": args.escenario,
        "consulta": args.consulta,
        "tiempos": args.tiempos,
        "log_level": args.log_level,
        "list": args.list,
        "interactive": args.interactive,
        "no_cache": args.no_cache,
        "cache_enabled": semantic_cache.enabled
    })

    # Función para listar escenarios
    def listar_escenarios():
        print(f"\n{Fore.CYAN}ESCENARIOS DISPONIBLES:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        for escenario in ESCENARIOS:
            print(f"{Fore.GREEN}{escenario['id']:2d}{Style.RESET_ALL}: {Fore.YELLOW}{escenario['titulo']}{Style.RESET_ALL}")
            print(f"   {Fore.CYAN}Descripción:{Style.RESET_ALL} {escenario['descripcion']}")
            print(f"   {Fore.CYAN}Consultas:{Style.RESET_ALL} {len(escenario['consultas'])}")
            print(f"{Fore.CYAN}{'-' * 80}{Style.RESET_ALL}")

    # Función para modo interactivo
    def modo_interactivo():
        listar_escenarios()
        while True:
            try:
                seleccion = input(f"\n{Fore.YELLOW}Selecciona un escenario (1-{len(ESCENARIOS)}) o 'q' para salir: {Style.RESET_ALL}")
                if seleccion.lower() == 'q':
                    return None

                seleccion = int(seleccion)
                if 1 <= seleccion <= len(ESCENARIOS):
                    for escenario in ESCENARIOS:
                        if escenario["id"] == seleccion:
                            return escenario
                    print(f"{Fore.RED}Error: No se encontró el escenario con ID {seleccion}.{Style.RESET_ALL}")
                else:
                    print(f"{Fore.RED}Error: Por favor, selecciona un número entre 1 y {len(ESCENARIOS)}.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}Error: Por favor, ingresa un número válido.{Style.RESET_ALL}")

    try:
        # Si se solicitó listar escenarios, mostrarlos y salir
        if args.list:
            listar_escenarios()
            return

        # Verificar que la base de datos existe
        if not os.path.exists(DB_PATH):
            error_msg = f"La base de datos no existe en {DB_PATH}."
            logger.error(error_msg)
            log_error(error_msg, None, {"db_path": DB_PATH})

            print(f"{Fore.RED}Error: {error_msg}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Ejecuta primero 'python asistente_llm_search.py' para crear la base de datos.{Style.RESET_ALL}")
            return

        mostrar_titulo("PRUEBA UNIFICADA DEL SISTEMA DE BÚSQUEDA AVANZADA CON LLM")

        # Si se especificó una consulta, ejecutarla
        if args.consulta:
            logger.info(f"Ejecutando consulta específica: {args.consulta}")
            mostrar_subtitulo(f"CONSULTA ESPECÍFICA: {args.consulta}")
            ejecutar_consulta(args.consulta, None, args.tiempos, "consulta_especifica")

            # Mostrar estadísticas del caché semántico
            if semantic_cache.enabled:
                stats = semantic_cache.get_stats()
                print(f"\n{Fore.CYAN}📊 Estadísticas del caché semántico:{Style.RESET_ALL}")
                print(f"{Fore.CYAN}   - Tamaño actual: {stats['size']} / {stats['max_size']} entradas{Style.RESET_ALL}")
                print(f"{Fore.CYAN}   - Aciertos (hits): {stats['hits']}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}   - Fallos (misses): {stats['misses']}{Style.RESET_ALL}")
                print(f"{Fore.CYAN}   - Tasa de aciertos: {stats['hit_rate']}{Style.RESET_ALL}")
            else:
                print(f"\n{Fore.YELLOW}ℹ️ Caché semántico DESHABILITADO. No se generaron estadísticas.{Style.RESET_ALL}")

            return

        # Si se solicitó modo interactivo, mostrar escenarios y permitir selección
        if args.interactive:
            escenario_seleccionado = modo_interactivo()
            if escenario_seleccionado:
                logger.info(f"Ejecutando escenario {escenario_seleccionado['id']}: {escenario_seleccionado['titulo']}")
                ejecutar_escenario(
                    f"ESCENARIO {escenario_seleccionado['id']}: {escenario_seleccionado['titulo']}",
                    escenario_seleccionado["consultas"],
                    args.tiempos
                )

                # Mostrar estadísticas del caché semántico
                if semantic_cache.enabled:
                    stats = semantic_cache.get_stats()
                    print(f"\n{Fore.CYAN}📊 Estadísticas del caché semántico:{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Tamaño actual: {stats['size']} / {stats['max_size']} entradas{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Aciertos (hits): {stats['hits']}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Fallos (misses): {stats['misses']}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Tasa de aciertos: {stats['hit_rate']}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Ahorro estimado: {stats['hits']} consultas = {stats['hits'] * 3} llamadas LLM{Style.RESET_ALL}")
                else:
                    print(f"\n{Fore.YELLOW}ℹ️ Caché semántico DESHABILITADO. No se generaron estadísticas.{Style.RESET_ALL}")

            return

        # Si se especificó un escenario, ejecutarlo
        if args.escenario:
            logger.info(f"Buscando escenario con ID: {args.escenario}")

            for escenario in ESCENARIOS:
                if escenario["id"] == args.escenario:
                    logger.info(f"Ejecutando escenario {escenario['id']}: {escenario['titulo']}")
                    ejecutar_escenario(
                        f"ESCENARIO {escenario['id']}: {escenario['titulo']}",
                        escenario["consultas"],
                        args.tiempos
                    )

                    # Mostrar estadísticas del caché semántico
                    if semantic_cache.enabled:
                        stats = semantic_cache.get_stats()
                        print(f"\n{Fore.CYAN}📊 Estadísticas del caché semántico:{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}   - Tamaño actual: {stats['size']} / {stats['max_size']} entradas{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}   - Aciertos (hits): {stats['hits']}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}   - Fallos (misses): {stats['misses']}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}   - Tasa de aciertos: {stats['hit_rate']}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}   - Ahorro estimado: {stats['hits']} consultas = {stats['hits'] * 3} llamadas LLM{Style.RESET_ALL}")
                    else:
                        print(f"\n{Fore.YELLOW}ℹ️ Caché semántico DESHABILITADO. No se generaron estadísticas.{Style.RESET_ALL}")

                    return

            error_msg = f"No se encontró el escenario con ID {args.escenario}."
            logger.error(error_msg)
            log_error(error_msg, None, {"escenario_id": args.escenario})
            print(f"{Fore.RED}Error: {error_msg}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Usa --list para ver los escenarios disponibles.{Style.RESET_ALL}")
            return

        # Si no se especificó nada, sugerir el modo interactivo y ejecutar todos los escenarios
        logger.info("Ejecutando todos los escenarios")

        print(f"{Fore.YELLOW}Sugerencia: Usa --interactive para seleccionar un escenario específico o --list para ver todos los escenarios disponibles.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Ejecutando todos los escenarios. Esto puede tomar tiempo...{Style.RESET_ALL}")

        inicio_total = time.time()
        escenarios_completados = 0

        for escenario in ESCENARIOS:
            try:
                ejecutar_escenario(
                    f"ESCENARIO {escenario['id']}: {escenario['titulo']}",
                    escenario["consultas"],
                    args.tiempos
                )
                escenarios_completados += 1
                print("\n\n")
            except Exception as e:
                error_info = ErrorHandler.handle_error(e, "ESCENARIO_PRINCIPAL", mostrar_traceback=True)
                log_error(f"Error en escenario principal: {escenario['titulo']}", e, {"escenario_id": escenario['id']})
                print(f"{Fore.RED}Error en escenario {escenario['id']}: {error_info['mensaje']}{Style.RESET_ALL}")
                print("\n\n")
                continue

        # Calcular tiempo total de ejecución
        tiempo_total = time.time() - inicio_total

        # Registrar finalización de la prueba
        logger.info(f"Prueba completada: {escenarios_completados}/{len(ESCENARIOS)} escenarios ejecutados en {tiempo_total:.2f} segundos")
        log_metrica("prueba_completada", 1, {
            "escenarios_completados": escenarios_completados,
            "escenarios_totales": len(ESCENARIOS),
            "tiempo_total": tiempo_total
        })

        if args.tiempos:
            print(f"\n{Fore.GREEN}Tiempo total de la prueba: {tiempo_total:.2f} segundos{Style.RESET_ALL}")

        # Mostrar estadísticas del caché semántico
        if semantic_cache.enabled:
            stats = semantic_cache.get_stats()
            print(f"\n{Fore.CYAN}📊 Estadísticas del caché semántico:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   - Tamaño actual: {stats['size']} / {stats['max_size']} entradas{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   - Aciertos (hits): {stats['hits']}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   - Fallos (misses): {stats['misses']}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   - Tasa de aciertos: {stats['hit_rate']}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   - Ahorro estimado: {stats['hits']} consultas = {stats['hits'] * 3} llamadas LLM{Style.RESET_ALL}")
        else:
            print(f"\n{Fore.YELLOW}ℹ️ Caché semántico DESHABILITADO. No se generaron estadísticas.{Style.RESET_ALL}")

    except Exception as e:
        # Manejar errores con el sistema centralizado
        error_info = ErrorHandler.handle_error(e, "PRUEBA_PRINCIPAL", mostrar_traceback=True)
        log_error("Error en prueba principal", e)
        print(f"\n{Fore.RED}❌ Error general: {error_info['mensaje']}{Style.RESET_ALL}")
        print(f"{Fore.RED}Mensaje para usuario: {ErrorHandler.get_user_message(error_info)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
