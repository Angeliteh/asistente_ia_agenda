#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para pre-entrenar el caché del asistente de agenda con consultas comunes.
Este script procesa una lista de consultas frecuentes para llenar el caché
y mejorar el rendimiento del sistema cuando se enfrenta a consultas similares.
"""

import os
import time
import argparse
from colorama import init, Fore, Style
from config import DB_PATH
from helpers.llm_search import procesar_consulta_completa, llm_cache

# Inicializar colorama para colores en la terminal
init()

def pre_entrenar_cache(consultas=None, mostrar_respuestas=False):
    """
    Pre-entrena el caché con consultas comunes.

    Args:
        consultas (list, optional): Lista de consultas para pre-entrenar
        mostrar_respuestas (bool): Si se deben mostrar las respuestas generadas
    """
    # Verificar que la base de datos existe
    if not os.path.exists(DB_PATH):
        print(f"{Fore.RED}Error: La base de datos no existe en {DB_PATH}.{Style.RESET_ALL}")
        return

    # Lista predeterminada de consultas comunes para pre-entrenar
    if consultas is None:
        consultas = [
            # Consultas individuales para personas clave
            "¿Quién es Luis Pérez?",
            "¿Quién es José Ángel Alvarado?",
            "¿Quién es Carmen Celina Ramirez?",
            "¿Quién es Guadalupe Alejandra Escobedo?",
            "¿Quién es Gabriela Jara Fuentes?",

            # Consultas de atributos específicos
            "¿Cuál es el teléfono de Luis Pérez?",
            "¿Cuál es el correo de José Ángel Alvarado?",
            "¿Dónde vive Carmen Celina Ramirez?",
            "¿Cuál es la función de Guadalupe Alejandra Escobedo?",
            "¿En qué zona trabaja Gabriela Jara Fuentes?",

            # Consultas de listado por zona
            "Dame todas las personas de la zona 109",
            "¿Quiénes trabajan en la zona 110?",
            "Lista de personas en la zona 111",

            # Consultas de listado por función
            "¿Quiénes son docentes?",
            "Lista de directores",
            "Muestra todos los subdirectores",
            "¿Cuántos veladores hay?",

            # Consultas de filtrado
            "Personas casadas",
            "Docentes con licenciatura",
            "Personas que viven en Durango",
            "Maestros de la zona 109"
        ]

    print(f"{Fore.CYAN}Pre-entrenando caché con {len(consultas)} consultas comunes...{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Estadísticas iniciales del caché: {llm_cache.get_stats()}{Style.RESET_ALL}")

    # Procesar cada consulta para llenar el caché
    inicio_total = time.time()
    for i, consulta in enumerate(consultas):
        print(f"\n{Fore.YELLOW}[{i+1}/{len(consultas)}] Procesando: {consulta}{Style.RESET_ALL}")

        inicio = time.time()
        resultado = procesar_consulta_completa(consulta, None, DB_PATH, False)
        fin = time.time()

        if mostrar_respuestas:
            print(f"{Fore.BLUE}Respuesta: {resultado['respuesta']}{Style.RESET_ALL}")

        print(f"{Fore.GREEN}Tiempo: {fin - inicio:.2f} segundos{Style.RESET_ALL}")

    # Guardar el caché en disco
    llm_cache.save_to_disk()

    fin_total = time.time()
    tiempo_total = fin_total - inicio_total

    print(f"\n{Fore.CYAN}Caché pre-entrenado con {len(consultas)} consultas comunes.{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Tiempo total: {tiempo_total:.2f} segundos{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Estadísticas finales del caché: {llm_cache.get_stats()}{Style.RESET_ALL}")

def limpiar_cache():
    """Limpia el caché completamente."""
    print(f"{Fore.YELLOW}Limpiando caché...{Style.RESET_ALL}")
    llm_cache.cache = {}
    llm_cache.hits = 0
    llm_cache.misses = 0
    llm_cache.save_to_disk()
    print(f"{Fore.GREEN}Caché limpiado correctamente.{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Estadísticas del caché: {llm_cache.get_stats()}{Style.RESET_ALL}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pre-entrenar el caché del asistente de agenda")
    parser.add_argument("--mostrar", action="store_true", help="Mostrar las respuestas generadas")
    parser.add_argument("--consulta", help="Procesar una consulta específica")
    parser.add_argument("--limpiar", action="store_true", help="Limpiar el caché antes de pre-entrenar")
    args = parser.parse_args()

    if args.limpiar:
        limpiar_cache()
        if not args.consulta:
            exit()

    if args.consulta:
        pre_entrenar_cache([args.consulta], args.mostrar)
    else:
        pre_entrenar_cache(None, args.mostrar)
