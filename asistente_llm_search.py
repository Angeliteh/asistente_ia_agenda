#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Asistente de agenda con búsqueda avanzada utilizando LLM.
Este script implementa un asistente de agenda que utiliza las capacidades
de razonamiento del LLM para realizar búsquedas más flexibles y precisas.
"""

import time
import random
import os
from colorama import init, Fore, Style
import google.generativeai as genai
from config import (
    GOOGLE_API_KEY,
    DB_PATH,
    EXCEL_PATH
)
from helpers.agenda_real_mapper import cargar_agenda_real
from helpers.sqlite_adapter import crear_base_datos
from helpers.llm_search import procesar_consulta_completa
from helpers.semantic_cache import semantic_cache
from helpers.error_handler import ErrorHandler
from helpers.logger import Logger, log_consulta, log_respuesta, log_metrica, log_error

# Inicializar colorama para colores en la terminal
init()

# Obtener instancia del logger
logger = Logger.get_logger()

# Configurar clave de API
genai.configure(api_key=GOOGLE_API_KEY)

# Variables globales para mantener el contexto de la conversación
historial_consultas = []
historial_respuestas = []

# Función para simular la escritura humana (efecto de tipeo)
def escribir_con_efecto(texto, velocidad_min=0.01, velocidad_max=0.03, end="\n"):
    for caracter in texto:
        print(caracter, end='', flush=True)
        # Pausa más larga en signos de puntuación
        if caracter in ['.', ',', '!', '?', ':']:
            time.sleep(random.uniform(velocidad_min*2, velocidad_max*2))
        else:
            time.sleep(random.uniform(velocidad_min, velocidad_max))
    print(end=end)

# Función para mostrar mensaje del humano
def mensaje_humano(texto):
    print(f"\n{Fore.GREEN}👤 Usuario: {Style.RESET_ALL}", end="")
    escribir_con_efecto(texto, 0.01, 0.03)
    time.sleep(0.2)

# Función para mostrar mensaje del asistente
def mensaje_asistente(texto):
    print(f"\n{Fore.BLUE}🤖 Asistente:{Style.RESET_ALL}")
    escribir_con_efecto(texto, 0.01, 0.03)
    time.sleep(0.2)

# Función para procesar una consulta completa
def procesar_consulta_avanzada(consulta, debug=False, contexto=None):
    """
    Procesa una consulta utilizando el enfoque avanzado con LLM.

    Args:
        consulta (str): Consulta del usuario
        debug (bool): Activar modo de depuración
        contexto (dict, optional): Contexto de la conversación anterior

    Returns:
        dict: Resultado del procesamiento
    """
    # Registrar la consulta
    logger.info(f"Procesando consulta: {consulta}")
    log_consulta(consulta, {"modo": "interactivo", "debug": debug, "con_contexto": contexto is not None})

    # Medir tiempo de ejecución
    inicio = time.time()

    try:
        # Usar la función centralizada de procesamiento de consultas
        if debug:
            print(f"\n{Fore.YELLOW}DEBUG: Procesando consulta utilizando el flujo unificado...{Style.RESET_ALL}")
            if contexto:
                print(f"\n{Fore.YELLOW}DEBUG: Usando contexto de conversación anterior{Style.RESET_ALL}")

        # Llamar a la función centralizada (sin pasar instancia de caché)
        resultado = procesar_consulta_completa(consulta, contexto, DB_PATH, debug, 1)

        # Calcular tiempo de ejecución
        tiempo_ejecucion = time.time() - inicio

        # Registrar métricas
        log_metrica("tiempo_ejecucion_cli", tiempo_ejecucion, {
            "consulta": consulta,
            "debug": debug,
            "from_cache": resultado.get("from_cache", False),
            "con_contexto": contexto is not None
        })

        # Formatear mensajes de debug con colores si está activado el modo debug
        if debug and not resultado.get("error"):
            print(f"\n{Fore.GREEN}DEBUG: Consulta procesada correctamente en {tiempo_ejecucion:.2f} segundos{Style.RESET_ALL}")

        # Registrar la respuesta
        log_respuesta(consulta, resultado["respuesta"], tiempo_ejecucion, resultado.get("from_cache", False))

        return resultado

    except Exception as e:
        # Manejar errores con el sistema centralizado
        error_info = ErrorHandler.handle_error(e, "CLI", mostrar_traceback=debug)
        log_error(f"Error al procesar consulta: {consulta}", e, {"debug": debug})

        # Calcular tiempo hasta el error
        tiempo_error = time.time() - inicio

        if debug:
            print(f"\n{Fore.RED}DEBUG: Error al procesar consulta: {error_info['mensaje']}{Style.RESET_ALL}")
            print(f"\n{Fore.RED}DEBUG: Tiempo hasta error: {tiempo_error:.2f} segundos{Style.RESET_ALL}")

        # Devolver un resultado con el error
        return {
            "error": error_info["mensaje"],
            "respuesta": ErrorHandler.get_user_message(error_info),
            "consulta": consulta
        }

# Función principal para modo interactivo
def modo_interactivo():
    """Función principal para el modo interactivo del asistente."""
    # Registrar inicio de la sesión
    logger.info("Iniciando asistente de agenda en modo interactivo")
    log_metrica("sesion_iniciada", 1)

    print(f"\n{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}💬 ASISTENTE DE AGENDA CON BÚSQUEDA AVANZADA LLM{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")

    try:
        # Verificar si la base de datos existe
        if not os.path.exists(DB_PATH):
            logger.info(f"Base de datos no encontrada. Cargando datos desde {EXCEL_PATH}")
            print(f"{Fore.YELLOW}📊 Cargando datos reales desde {EXCEL_PATH}...{Style.RESET_ALL}")

            try:
                resultado = cargar_agenda_real(EXCEL_PATH)

                if resultado["error"]:
                    error_msg = f"Error al cargar datos: {resultado['error']}"
                    logger.error(error_msg)
                    log_error(error_msg, None, {"excel_path": EXCEL_PATH})
                    print(f"{Fore.RED}❌ {error_msg}{Style.RESET_ALL}")
                    return

                registros = resultado["registros"]
                logger.info(f"Datos cargados: {len(registros)} registros")
                log_metrica("registros_cargados", len(registros))
                print(f"{Fore.GREEN}✅ Datos cargados: {len(registros)} registros{Style.RESET_ALL}")

                # Crear base de datos SQLite
                logger.info("Creando base de datos SQLite")
                print(f"{Fore.YELLOW}🗄️ Creando base de datos SQLite...{Style.RESET_ALL}")
                resultado_db = crear_base_datos(registros)

                if resultado_db["error"]:
                    error_msg = f"Error al crear base de datos: {resultado_db['error']}"
                    logger.error(error_msg)
                    log_error(error_msg, None, {"registros": len(registros)})
                    print(f"{Fore.RED}❌ {error_msg}{Style.RESET_ALL}")
                    return

                logger.info(f"Base de datos creada: {resultado_db['mensaje']}")
                print(f"{Fore.GREEN}✅ {resultado_db['mensaje']}{Style.RESET_ALL}")

            except Exception as e:
                error_info = ErrorHandler.handle_error(e, "DATOS", mostrar_traceback=True)
                log_error("Error al inicializar datos", e)
                print(f"{Fore.RED}❌ Error: {error_info['mensaje']}{Style.RESET_ALL}")
                return

        else:
            logger.info(f"Base de datos encontrada en {DB_PATH}")
            print(f"{Fore.GREEN}✅ Base de datos SQLite ya existe en {DB_PATH}{Style.RESET_ALL}")

        # Mostrar estadísticas del caché semántico
        cache_stats = semantic_cache.get_stats()
        logger.info(f"Estadísticas del caché semántico: {cache_stats}")
        print(f"{Fore.CYAN}📊 Caché semántico: {cache_stats['size']} entradas, {cache_stats['hit_rate']} de aciertos{Style.RESET_ALL}")

        # Mensaje de bienvenida
        mensaje_asistente("¡Hola! Soy tu asistente de agenda con búsqueda avanzada. Puedo entender consultas en lenguaje natural y buscar información de manera flexible. ¿En qué puedo ayudarte?")

        # Modo debug por defecto
        debug_mode = False

        # Contador de consultas
        consultas_procesadas = 0

        # Bucle principal
        while True:
            try:
                # Obtener consulta del usuario
                consulta = input(f"\n{Fore.GREEN}👤 Usuario: {Style.RESET_ALL}")

                # Verificar comandos especiales
                if consulta.lower() == 'salir':
                    logger.info("Usuario solicitó salir")
                    log_metrica("sesion_finalizada", 1, {"consultas_procesadas": consultas_procesadas})
                    mensaje_asistente("¡Hasta pronto! Ha sido un placer ayudarte.")
                    # Guardar caché semántico antes de salir
                    semantic_cache.save_to_disk()
                    print(f"{Fore.CYAN}📊 Estadísticas finales del caché semántico: {semantic_cache.get_stats()}{Style.RESET_ALL}")
                    # Limpiar historial de conversación
                    historial_consultas.clear()
                    historial_respuestas.clear()
                    break

                elif consulta.lower() == 'debug':
                    debug_mode = not debug_mode
                    logger.info(f"Modo debug: {'activado' if debug_mode else 'desactivado'}")
                    print(f"{Fore.YELLOW}Modo debug: {'activado' if debug_mode else 'desactivado'}{Style.RESET_ALL}")
                    continue

                elif consulta.lower() in ['ayuda', 'help', '?']:
                    logger.info("Usuario solicitó ayuda")
                    print(f"\n{Fore.CYAN}📋 Comandos disponibles:{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - salir: Salir del asistente{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - debug: Activar/desactivar modo debug{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - cache/caché/estadísticas: Mostrar estadísticas del caché{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - logs/log: Mostrar información de logs{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - contexto/context: Mostrar el contexto actual de la conversación{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - limpiar/reset: Limpiar el contexto de la conversación{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - log level [NIVEL]: Cambiar nivel de log (DEBUG, INFO, WARNING, ERROR){Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - ayuda/help/?: Mostrar esta ayuda{Style.RESET_ALL}")
                    continue

                elif consulta.lower() in ['cache', 'caché', 'estadísticas']:
                    stats = semantic_cache.get_stats()
                    logger.info(f"Usuario solicitó estadísticas del caché semántico: {stats}")
                    print(f"\n{Fore.CYAN}📊 Estadísticas del caché semántico:{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Tamaño actual: {stats['size']} / {stats['max_size']} entradas{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Aciertos: {stats['hits']}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Fallos: {stats['misses']}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Tasa de aciertos: {stats['hit_rate']}{Style.RESET_ALL}")
                    continue

                elif consulta.lower() in ['logs', 'log']:
                    logger.info("Usuario solicitó información de logs")
                    print(f"\n{Fore.CYAN}📊 Información de logs:{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Directorio de logs: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')}{Style.RESET_ALL}")
                    print(f"{Fore.CYAN}   - Archivos disponibles: {', '.join(os.listdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')))}{Style.RESET_ALL}")
                    continue

                elif consulta.lower() in ['contexto', 'context']:
                    logger.info("Usuario solicitó información del contexto de conversación")
                    print(f"\n{Fore.CYAN}📊 Información del contexto de conversación:{Style.RESET_ALL}")

                    if not historial_consultas:
                        print(f"{Fore.YELLOW}   No hay historial de conversación.{Style.RESET_ALL}")
                    else:
                        print(f"{Fore.CYAN}   - Total de interacciones: {len(historial_consultas)}{Style.RESET_ALL}")
                        print(f"{Fore.CYAN}   - Historial de consultas:{Style.RESET_ALL}")
                        for i, (consulta_hist, respuesta_hist) in enumerate(zip(historial_consultas, historial_respuestas)):
                            print(f"{Fore.GREEN}     {i+1}. Usuario: {consulta_hist[:50]}{'...' if len(consulta_hist) > 50 else ''}{Style.RESET_ALL}")
                            print(f"{Fore.BLUE}        Asistente: {respuesta_hist[:50]}{'...' if len(respuesta_hist) > 50 else ''}{Style.RESET_ALL}")
                    continue

                elif consulta.lower() in ['limpiar', 'reset', 'reiniciar', 'clear']:
                    # Limpiar el contexto de la conversación
                    historial_consultas.clear()
                    historial_respuestas.clear()

                    logger.info("Usuario solicitó limpiar el contexto de la conversación")
                    log_metrica("contexto_reiniciado", 1)

                    print(f"\n{Fore.CYAN}✅ Contexto de conversación limpiado. La próxima consulta no tendrá contexto previo.{Style.RESET_ALL}")
                    mensaje_asistente("He olvidado nuestra conversación anterior. ¿En qué puedo ayudarte ahora?")
                    continue

                elif consulta.lower().startswith('log level ') or consulta.lower().startswith('loglevel '):
                    # Extraer el nivel de log
                    parts = consulta.lower().split()
                    level_name = parts[-1].upper()  # Último elemento es el nivel

                    if level_name in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
                        from helpers.logger import set_log_level
                        success = set_log_level(level_name)

                        if success:
                            logger.info(f"Usuario cambió el nivel de log a: {level_name}")
                            print(f"\n{Fore.CYAN}✅ Nivel de log cambiado a: {level_name}{Style.RESET_ALL}")

                            if level_name == 'DEBUG':
                                print(f"{Fore.YELLOW}⚠️ Nivel DEBUG: Verás mucha información detallada en la consola.{Style.RESET_ALL}")
                            elif level_name == 'WARNING':
                                print(f"{Fore.YELLOW}⚠️ Nivel WARNING: Solo verás advertencias y errores en la consola.{Style.RESET_ALL}")
                            elif level_name == 'ERROR':
                                print(f"{Fore.YELLOW}⚠️ Nivel ERROR: Solo verás errores en la consola.{Style.RESET_ALL}")
                        else:
                            print(f"\n{Fore.RED}❌ No se pudo cambiar el nivel de log.{Style.RESET_ALL}")
                    else:
                        print(f"\n{Fore.RED}❌ Nivel de log no válido: {level_name}{Style.RESET_ALL}")
                        print(f"{Fore.YELLOW}Niveles válidos: DEBUG, INFO, WARNING, ERROR, CRITICAL{Style.RESET_ALL}")

                    continue

                # Medir tiempo de ejecución
                inicio = time.time()

                # Preparar contexto para la consulta
                contexto = None
                if historial_consultas and historial_respuestas:
                    contexto = {
                        "consulta_anterior": historial_consultas[-1],
                        "respuesta_anterior": historial_respuestas[-1],
                        "historial_consultas": historial_consultas,
                        "historial_respuestas": historial_respuestas
                    }
                    if debug_mode:
                        print(f"\n{Fore.CYAN}🔄 Usando contexto de conversación anterior ({len(historial_consultas)} consultas previas){Style.RESET_ALL}")

                # Procesar la consulta con contexto
                resultado = procesar_consulta_avanzada(consulta, debug_mode, contexto)
                consultas_procesadas += 1

                # Actualizar historial para mantener contexto
                historial_consultas.append(consulta)
                historial_respuestas.append(resultado["respuesta"])

                # Limitar el historial a los últimos 10 elementos para evitar que crezca demasiado
                if len(historial_consultas) > 10:
                    historial_consultas = historial_consultas[-10:]
                    historial_respuestas = historial_respuestas[-10:]

                # Calcular tiempo de ejecución
                fin = time.time()
                tiempo_ejecucion = fin - inicio

                # Mostrar información sobre el tiempo y el caché
                if debug_mode:
                    print(f"\n{Fore.YELLOW}⏱️ Tiempo de ejecución: {tiempo_ejecucion:.4f} segundos{Style.RESET_ALL}")

                # Mostrar información sobre el caché semántico si se usó
                stats = semantic_cache.get_stats()
                if stats['hits'] > 0:
                    print(f"{Fore.CYAN}💡 Caché semántico: {stats['hit_rate']} de aciertos{Style.RESET_ALL}")

                # Mostrar respuesta
                mensaje_asistente(resultado["respuesta"])

            except KeyboardInterrupt:
                logger.info("Usuario interrumpió la ejecución con Ctrl+C")
                print(f"\n{Fore.YELLOW}Ejecución interrumpida por el usuario (Ctrl+C){Style.RESET_ALL}")
                mensaje_asistente("Entiendo que quieres interrumpir. ¿Hay algo más en lo que pueda ayudarte?")
                continue

            except Exception as e:
                error_info = ErrorHandler.handle_error(e, "INTERACTIVO", mostrar_traceback=True)
                log_error("Error en modo interactivo", e, {"consulta": consulta})
                print(f"\n{Fore.RED}❌ Error: {error_info['mensaje']}{Style.RESET_ALL}")
                mensaje_asistente(ErrorHandler.get_user_message(error_info))

    except Exception as e:
        error_info = ErrorHandler.handle_error(e, "INICIALIZACION", mostrar_traceback=True)
        log_error("Error al inicializar el asistente", e)
        print(f"\n{Fore.RED}❌ Error fatal: {error_info['mensaje']}{Style.RESET_ALL}")
        print(f"{Fore.RED}El asistente no puede continuar. Por favor, revisa los logs para más detalles.{Style.RESET_ALL}")

# Función principal
if __name__ == "__main__":
    modo_interactivo()
