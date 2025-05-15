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
from colorama import init, Fore, Style
from helpers.llm_search import procesar_consulta_completa

# Inicializar colorama para colores en la terminal
init()

# Importar configuración centralizada
from config import DB_PATH

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

def ejecutar_consulta(consulta, contexto=None, mostrar_tiempos=False):
    """
    Ejecuta una consulta y muestra la respuesta final.

    Args:
        consulta (str): Consulta a ejecutar
        contexto (dict): Contexto de la consulta anterior
        mostrar_tiempos (bool): Si se deben mostrar los tiempos de ejecución

    Returns:
        dict: Contexto para la siguiente consulta
    """
    # Pedir al usuario que presione Enter para continuar o 's' para saltar
    respuesta = input(f"\n{Fore.YELLOW}Presiona Enter para ejecutar la consulta o 's' para saltar: \"{consulta}\"{Style.RESET_ALL}")
    if respuesta.lower() == 's':
        print(f"{Fore.RED}Consulta omitida.{Style.RESET_ALL}")
        return contexto

    print(f"\n{Fore.GREEN}👤 Consulta: {consulta}{Style.RESET_ALL}")

    # Medir tiempo total
    inicio_total = time.time()

    # Usar la función centralizada para procesar la consulta
    resultado_procesamiento = procesar_consulta_completa(consulta, contexto, DB_PATH, mostrar_tiempos)

    # Extraer componentes del resultado
    estrategia = resultado_procesamiento["estrategia"]
    resultado_sql = resultado_procesamiento["resultado_sql"]
    respuesta_texto = resultado_procesamiento["respuesta"]

    # Calcular tiempo total
    fin_total = time.time()
    tiempo_total = fin_total - inicio_total

    # Mostrar respuesta
    print(f"\n{Fore.BLUE}🤖 Respuesta:{Style.RESET_ALL}")
    print(respuesta_texto)

    if mostrar_tiempos:
        print(f"\n{Fore.GREEN}Tiempo total: {tiempo_total:.2f} segundos{Style.RESET_ALL}")

    # Crear contexto para la siguiente consulta
    contexto_siguiente = {
        "consulta_anterior": consulta,
        "estrategia_anterior": estrategia,
        "resultados_anteriores": resultado_sql["registros"] if resultado_sql["total"] > 0 else [],
        "respuesta_anterior": respuesta_texto,
        "historial_consultas": contexto.get("historial_consultas", []) + [consulta] if contexto else [consulta],
        "historial_respuestas": contexto.get("historial_respuestas", []) + [respuesta_texto] if contexto else [respuesta_texto]
    }

    return contexto_siguiente

def ejecutar_escenario(titulo, consultas, mostrar_tiempos=False):
    """
    Ejecuta un escenario de prueba con varias consultas relacionadas.

    Args:
        titulo (str): Título del escenario
        consultas (list): Lista de consultas a ejecutar
        mostrar_tiempos (bool): Si se deben mostrar los tiempos de ejecución
    """
    # Pedir al usuario que presione Enter para continuar o 's' para saltar
    respuesta = input(f"\n{Fore.YELLOW}Presiona Enter para ejecutar el escenario o 's' para saltar: \"{titulo}\"{Style.RESET_ALL}")
    if respuesta.lower() == 's':
        print(f"{Fore.RED}Escenario omitido.{Style.RESET_ALL}")
        return

    mostrar_titulo(titulo)

    contexto = None
    for consulta in consultas:
        contexto = ejecutar_consulta(consulta, contexto, mostrar_tiempos)
        if contexto is None:  # Si se omitió la consulta
            continue
        print("\n")

# Definir escenarios de prueba
ESCENARIOS = [
    {
        "id": 1,
        "titulo": "INFORMACIÓN INDIVIDUAL",
        "descripcion": "Consultas sobre información de personas específicas",
        "consultas": [
            "¿Quién es Luis Pérez Ibáñez?",
            "¿Cuál es su número de teléfono?",
            "¿Dónde vive?",
            "¿Cuál es su función?",
            "¿Cuándo ingresó?"
        ]
    },
    {
        "id": 2,
        "titulo": "ERRORES ORTOGRÁFICOS Y NOMBRES PARCIALES",
        "descripcion": "Consultas con errores ortográficos o nombres parciales",
        "consultas": [
            "dame el telefono de luiz perez",
            "quien es jose anjel",
            "informacion de peres ibañes",
            "dame el telefono de luis",
            "quien es jose",
            "informacion de perez"
        ]
    },
    {
        "id": 3,
        "titulo": "LISTADO Y FILTRADO",
        "descripcion": "Consultas que piden listar múltiples registros",
        "consultas": [
            "muestra todos los docentes de la zona 109",
            "dame todos los números de teléfono de los subdirectores",
            "lista todos los correos electrónicos de los directores",
            "muestra todas las personas con licenciatura",
            "dame los nombres y funciones de todos los que trabajan en la zona 109"
        ]
    },
    {
        "id": 4,
        "titulo": "CONSULTAS COMPLEJAS",
        "descripcion": "Consultas con múltiples condiciones",
        "consultas": [
            "¿quiénes son docentes con licenciatura?",
            "busca personas casadas que trabajen en la zona 109",
            "¿quién tiene más antigüedad en el centro de trabajo?",
            "muestra todas las personas que ingresaron antes del 2000",
            "¿cuántas personas tienen maestría?"
        ]
    },
    {
        "id": 5,
        "titulo": "SEGUIMIENTO Y CONTEXTO",
        "descripcion": "Consultas de seguimiento que dependen del contexto",
        "consultas": [
            "¿Quién es el director?",
            "¿Cuál es su correo electrónico?",
            "¿Y su número de teléfono?",
            "¿Dónde trabaja él?",
            "¿Tiene estudios de maestría?"
        ]
    },
    {
        "id": 6,
        "titulo": "CAMBIO DE CONTEXTO",
        "descripcion": "Consultas que cambian de contexto",
        "consultas": [
            "¿Quién es Luis Pérez?",
            "¿Cuál es su función?",
            "Ahora dime quién es José Angel Alvarado",
            "¿Cuál es su función?",
            "¿Y su correo electrónico?"
        ]
    }
]

def main():
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description='Prueba unificada del sistema de búsqueda avanzada con LLM.')
    parser.add_argument('--escenario', type=int, help='ID del escenario a ejecutar (1-6)')
    parser.add_argument('--consulta', type=str, help='Consulta específica a ejecutar')
    parser.add_argument('--tiempos', action='store_true', help='Mostrar tiempos de ejecución')
    args = parser.parse_args()

    # Verificar que la base de datos existe
    if not os.path.exists(DB_PATH):
        print(f"{Fore.RED}Error: La base de datos no existe en {DB_PATH}.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}Ejecuta primero 'python asistente_llm_search.py' para crear la base de datos.{Style.RESET_ALL}")
        return

    mostrar_titulo("PRUEBA UNIFICADA DEL SISTEMA DE BÚSQUEDA AVANZADA CON LLM")

    # Si se especificó una consulta, ejecutarla
    if args.consulta:
        mostrar_subtitulo(f"CONSULTA ESPECÍFICA: {args.consulta}")
        ejecutar_consulta(args.consulta, None, args.tiempos)
        return

    # Si se especificó un escenario, ejecutarlo
    if args.escenario:
        for escenario in ESCENARIOS:
            if escenario["id"] == args.escenario:
                ejecutar_escenario(
                    f"ESCENARIO {escenario['id']}: {escenario['titulo']}",
                    escenario["consultas"],
                    args.tiempos
                )
                return
        print(f"{Fore.RED}Error: No se encontró el escenario con ID {args.escenario}.{Style.RESET_ALL}")
        return

    # Si no se especificó nada, ejecutar todos los escenarios
    for escenario in ESCENARIOS:
        ejecutar_escenario(
            f"ESCENARIO {escenario['id']}: {escenario['titulo']}",
            escenario["consultas"],
            args.tiempos
        )
        print("\n\n")

if __name__ == "__main__":
    main()
