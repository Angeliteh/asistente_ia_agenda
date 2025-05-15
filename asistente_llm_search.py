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
from helpers.llm_search import procesar_consulta_completa, llm_cache

# Inicializar colorama para colores en la terminal
init()

# Configurar clave de API
genai.configure(api_key=GOOGLE_API_KEY)

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
def procesar_consulta_avanzada(consulta, debug=False):
    """
    Procesa una consulta utilizando el enfoque avanzado con LLM.

    Args:
        consulta (str): Consulta del usuario
        debug (bool): Activar modo de depuración

    Returns:
        dict: Resultado del procesamiento
    """
    # Usar la función centralizada de procesamiento de consultas
    if debug:
        print(f"\n{Fore.YELLOW}DEBUG: Procesando consulta utilizando el flujo unificado...{Style.RESET_ALL}")

    # Llamar a la función centralizada
    resultado = procesar_consulta_completa(consulta, None, DB_PATH, debug)

    # Formatear mensajes de debug con colores si está activado el modo debug
    if debug and not resultado.get("error"):
        print(f"\n{Fore.GREEN}DEBUG: Consulta procesada correctamente{Style.RESET_ALL}")

    return resultado

# Función principal para modo interactivo
def modo_interactivo():
    print(f"\n{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}💬 ASISTENTE DE AGENDA CON BÚSQUEDA AVANZADA LLM{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")

    # Verificar si la base de datos existe
    if not os.path.exists(DB_PATH):
        print(f"{Fore.YELLOW}📊 Cargando datos reales desde {EXCEL_PATH}...{Style.RESET_ALL}")
        resultado = cargar_agenda_real(EXCEL_PATH)

        if resultado["error"]:
            print(f"{Fore.RED}❌ Error al cargar datos: {resultado['error']}{Style.RESET_ALL}")
            return

        registros = resultado["registros"]
        print(f"{Fore.GREEN}✅ Datos cargados: {len(registros)} registros{Style.RESET_ALL}")

        # Crear base de datos SQLite
        print(f"{Fore.YELLOW}🗄️ Creando base de datos SQLite...{Style.RESET_ALL}")
        resultado_db = crear_base_datos(registros)

        if resultado_db["error"]:
            print(f"{Fore.RED}❌ Error al crear base de datos: {resultado_db['error']}{Style.RESET_ALL}")
            return

        print(f"{Fore.GREEN}✅ {resultado_db['mensaje']}{Style.RESET_ALL}")
    else:
        print(f"{Fore.GREEN}✅ Base de datos SQLite ya existe en {DB_PATH}{Style.RESET_ALL}")

    # Mostrar estadísticas del caché
    cache_stats = llm_cache.get_stats()
    print(f"{Fore.CYAN}📊 Caché: {cache_stats['size']} entradas, {cache_stats['hit_rate']} de aciertos{Style.RESET_ALL}")

    # Mensaje de bienvenida
    mensaje_asistente("¡Hola! Soy tu asistente de agenda con búsqueda avanzada. Puedo entender consultas en lenguaje natural y buscar información de manera flexible. ¿En qué puedo ayudarte?")

    # Modo debug por defecto
    debug_mode = False

    # Bucle principal
    while True:
        # Obtener consulta del usuario
        consulta = input(f"\n{Fore.GREEN}👤 Usuario: {Style.RESET_ALL}")

        # Verificar comandos especiales
        if consulta.lower() == 'salir':
            mensaje_asistente("¡Hasta pronto! Ha sido un placer ayudarte.")
            # Guardar caché antes de salir
            llm_cache.save_to_disk()
            print(f"{Fore.CYAN}📊 Estadísticas finales del caché: {llm_cache.get_stats()}{Style.RESET_ALL}")
            break
        elif consulta.lower() == 'debug':
            debug_mode = not debug_mode
            print(f"{Fore.YELLOW}Modo debug: {'activado' if debug_mode else 'desactivado'}{Style.RESET_ALL}")
            continue
        elif consulta.lower() in ['cache', 'caché', 'estadísticas']:
            stats = llm_cache.get_stats()
            print(f"\n{Fore.CYAN}📊 Estadísticas del caché:{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   - Tamaño actual: {stats['size']} / {stats['max_size']} entradas{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   - Aciertos: {stats['hits']}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   - Fallos: {stats['misses']}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}   - Tasa de aciertos: {stats['hit_rate']}{Style.RESET_ALL}")
            continue

        # Medir tiempo de ejecución
        inicio = time.time()

        # Procesar la consulta
        resultado = procesar_consulta_avanzada(consulta, debug_mode)

        # Calcular tiempo de ejecución
        fin = time.time()
        tiempo_ejecucion = fin - inicio

        # Mostrar información sobre el tiempo y el caché
        if debug_mode:
            print(f"\n{Fore.YELLOW}⏱️ Tiempo de ejecución: {tiempo_ejecucion:.4f} segundos{Style.RESET_ALL}")

        # Mostrar información sobre el caché si se usó
        if llm_cache.hits > 0 and llm_cache.hits + llm_cache.misses > 0:
            hit_rate = (llm_cache.hits / (llm_cache.hits + llm_cache.misses)) * 100
            print(f"{Fore.CYAN}💡 Caché: {hit_rate:.1f}% de aciertos{Style.RESET_ALL}")

        # Mostrar respuesta
        mensaje_asistente(resultado["respuesta"])

# Función principal
if __name__ == "__main__":
    modo_interactivo()
