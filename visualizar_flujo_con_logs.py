#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para visualizar el flujo completo de información en el proceso de consulta.
Genera logs detallados en un archivo externo para análisis posterior.
"""

import json
import os
import datetime
import google.generativeai as genai
from config import GOOGLE_API_KEY
from helpers.dynamic_loader import cargar_agenda_dinamica
from helpers.enhanced_query import extract_query_parameters, search_data, generate_natural_response
from helpers.session_context import SessionContext
from colorama import init, Fore, Style, Back

# Inicializar colorama para colores en la terminal
init()

# Configurar clave de API
genai.configure(api_key=GOOGLE_API_KEY)

# Crear contexto de sesión
session_context = SessionContext(max_history=5)

# Configuración de logs
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Crear archivo de log con timestamp
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"flujo_consulta_{timestamp}.log")

def log_to_file(section, content, console_output=True):
    """
    Escribe una sección en el archivo de log y opcionalmente en la consola.

    Args:
        section (str): Título de la sección
        content (str): Contenido a escribir
        console_output (bool): Si es True, también muestra en consola
    """
    separator = "=" * 80

    # Formatear la sección para el archivo
    log_content = f"\n{separator}\n"
    log_content += f" {section} \n"
    log_content += f"{separator}\n"
    log_content += f"{content}\n"

    # Escribir en el archivo
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(log_content)

    # Mostrar en consola si se solicita
    if console_output:
        print(f"\n{Fore.WHITE}{separator}{Style.RESET_ALL}")
        print(f"{Fore.WHITE} {section} {Style.RESET_ALL}")
        print(f"{Fore.WHITE}{separator}{Style.RESET_ALL}")
        print(f"{Fore.WHITE}{content}{Style.RESET_ALL}")

def log_json(section, data, console_output=True):
    """
    Escribe datos JSON en el archivo de log y opcionalmente en la consola.

    Args:
        section (str): Título de la sección
        data (dict): Datos a escribir en formato JSON
        console_output (bool): Si es True, también muestra en consola
    """
    json_content = json.dumps(data, indent=2, ensure_ascii=False)

    # Escribir en el archivo y consola
    log_to_file(section, json_content, console_output)

    # Mostrar en consola con color si se solicita
    if console_output:
        print(f"{Fore.CYAN}{json_content}{Style.RESET_ALL}")

def log_prompt(section, prompt, console_output=True):
    """
    Escribe un prompt en el archivo de log y opcionalmente en la consola.

    Args:
        section (str): Título de la sección
        prompt (str): Prompt a escribir
        console_output (bool): Si es True, también muestra en consola
    """
    # Escribir en el archivo
    log_to_file(section, prompt, console_output)

    # Mostrar en consola con color si se solicita
    if console_output:
        print(f"{Fore.YELLOW}{prompt}{Style.RESET_ALL}")

def visualizar_flujo_consulta(pregunta, console_output=True):
    """
    Visualiza todo el flujo de procesamiento de una consulta y lo guarda en un archivo de log.

    Args:
        pregunta (str): La pregunta del usuario
        console_output (bool): Si es True, muestra la salida en consola

    Returns:
        dict: Resultado completo del procesamiento
    """
    # Registrar la pregunta del usuario
    log_to_file("PREGUNTA DEL USUARIO", pregunta, console_output)

    # Verificar si es una pregunta de seguimiento
    es_seguimiento = session_context.is_follow_up_query(pregunta)
    if es_seguimiento:
        log_to_file("ANÁLISIS DE CONTEXTO", "Esta parece ser una pregunta de seguimiento.", console_output)
        log_json("CONTEXTO ACTUAL", session_context.get_context_for_prompt(), console_output)

    # PASO 1: Cargar datos
    log_to_file("PASO 1: CARGANDO DATOS", "Cargando datos desde Excel...", console_output)

    # Cargar datos
    resultado = cargar_agenda_dinamica("datos/agenda.xlsx")
    registros = resultado["registros"]
    esquema = resultado["esquema"]
    mapeo_columnas = resultado["mapeo_columnas"]

    # Registrar resumen de datos cargados
    log_to_file(
        "DATOS CARGADOS",
        f"Se cargaron {len(registros)} registros con {len(esquema)} columnas.",
        console_output
    )

    # Registrar muestra de datos
    log_json("MUESTRA DE DATOS (Primer registro)", registros[0], console_output)

    # PASO 2: Extraer parámetros de la consulta
    log_to_file("PASO 2: EXTRAYENDO PARÁMETROS", "Enviando consulta al primer LLM...", console_output)

    # Construir el prompt de extracción
    prompt_extraccion = f"""
    Analiza esta consulta sobre una agenda de contactos y extrae SOLO los parámetros de búsqueda.

    Consulta: {pregunta}

    Devuelve ÚNICAMENTE un objeto JSON con estos campos:
    - tipo_consulta: "atributo_persona" (busca info de alguien), "filtrado" (busca personas que cumplen condición), "conteo" (cuenta personas), "general" (otro tipo)
    - persona: Nombre de la persona mencionada (si aplica)
    - atributo: Atributo buscado como "telefono", "direccion", "correo", "edad", "genero" (si aplica)
    - condicion: Condición de filtrado como "mayor_que", "menor_que", "igual_a" (si aplica)
    - valor: Valor para la condición (si aplica)

    Ejemplos:
    Para "¿Cuál es el teléfono de Juan?":
    {{"tipo_consulta": "atributo_persona", "persona": "Juan", "atributo": "telefono"}}

    Para "¿Quién tiene más de 30 años?":
    {{"tipo_consulta": "filtrado", "atributo": "edad", "condicion": "mayor_que", "valor": 30}}

    Para "¿Cuántas personas hay en la agenda?":
    {{"tipo_consulta": "conteo"}}

    Para "¿Y su dirección?" (pregunta de seguimiento sobre alguien mencionado antes):
    {{"tipo_consulta": "atributo_persona", "atributo": "direccion"}}

    Responde SOLO con el JSON, sin texto adicional.
    """

    # Registrar el prompt de extracción
    log_prompt("PROMPT DE EXTRACCIÓN (LLM 1)", prompt_extraccion, console_output)

    # Extraer parámetros
    parametros = extract_query_parameters(pregunta)

    # Registrar los parámetros extraídos
    log_json("PARÁMETROS EXTRAÍDOS", parametros, console_output)

    # PASO 3: Buscar datos relevantes
    log_to_file("PASO 3: BUSCANDO DATOS RELEVANTES", "Aplicando búsqueda directa...", console_output)

    # Buscar datos relevantes
    datos_relevantes = search_data(parametros, registros, session_context)

    # Registrar los datos relevantes
    log_json("DATOS RELEVANTES ENCONTRADOS", datos_relevantes, console_output)

    # PASO 4: Generar respuesta natural
    log_to_file("PASO 4: GENERANDO RESPUESTA NATURAL", "Enviando datos al segundo LLM...", console_output)

    # Generar respuesta natural
    resultado_respuesta = generate_natural_response(pregunta, datos_relevantes, session_context)
    respuesta = resultado_respuesta["response_text"]
    prompt_usado = resultado_respuesta["prompt_used"]

    # Registrar el prompt utilizado
    log_prompt("PROMPT PARA RESPUESTA NATURAL (LLM 2)", prompt_usado, console_output)

    # Registrar la respuesta generada
    log_to_file("RESPUESTA FINAL", respuesta, console_output)

    # Actualizar el contexto de la sesión
    session_context.add_interaction(pregunta, parametros, respuesta)

    # Registrar el contexto actualizado
    log_json("CONTEXTO ACTUALIZADO", session_context.get_context_for_prompt(), console_output)

    # Resumen del flujo
    resumen = f"""
        1. Pregunta del usuario: "{pregunta}"
        2. Es pregunta de seguimiento: {"Sí" if es_seguimiento else "No"}
        3. Tipo de consulta: {parametros.get('tipo_consulta', 'desconocido')}
        4. Persona buscada: {parametros.get('persona', 'ninguna')}
        5. Atributo buscado: {parametros.get('atributo', 'ninguno')}
        6. Datos relevantes encontrados: {len(datos_relevantes.get('relevant_data', []))} registros
        7. Respuesta natural generada
        8. Contexto actualizado para futuras consultas
    """

    log_to_file("RESUMEN DEL FLUJO", resumen, console_output)

    # Devolver resultado completo
    return {
        "query": pregunta,
        "parameters": parametros,
        "search_result": datos_relevantes,
        "response": respuesta,
        "is_follow_up": es_seguimiento
    }

def ejecutar_prueba_automatizada(consultas, silent=False):
    """
    Ejecuta una prueba automatizada con una lista de consultas.

    Args:
        consultas (list): Lista de consultas a procesar
        silent (bool): Si es True, no muestra salida en consola
    """
    log_to_file("INICIO DE PRUEBA AUTOMATIZADA", f"Procesando {len(consultas)} consultas...", not silent)

    # Procesar cada consulta
    resultados = []
    for i, consulta in enumerate(consultas, 1):
        log_to_file(f"CONSULTA #{i}", f"Procesando: {consulta}", not silent)
        resultado = visualizar_flujo_consulta(consulta, not silent)
        resultados.append(resultado)

        # Separador entre consultas
        log_to_file("SEPARADOR", "-" * 40, not silent)

    log_to_file("FIN DE PRUEBA AUTOMATIZADA", f"Se procesaron {len(consultas)} consultas.", not silent)

    # Devolver todos los resultados
    return resultados

def modo_interactivo():
    """Ejecuta el visualizador en modo interactivo"""
    print(f"{Fore.GREEN}=== VISUALIZADOR DE FLUJO DE CONSULTA CON LOGS ==={Style.RESET_ALL}")
    print(f"{Fore.GREEN}Este script muestra el flujo completo de información y genera logs detallados.{Style.RESET_ALL}")
    print(f"{Fore.GREEN}Los logs se guardan en: {LOG_FILE}{Style.RESET_ALL}")

    # Ejemplos de consultas
    ejemplos = [
        "¿Cuál es el teléfono de Juan Pérez?",
        "¿Dónde vive Ana Ramírez?",
        "¿Cuál es el correo electrónico de Carlos Martínez?",
        "¿Quién tiene más de 30 años?",
        "¿Cuántas personas hay en la agenda?"
    ]

    # Ejemplos de seguimiento
    seguimientos = [
        "¿Y cuál es su dirección?",
        "¿Qué edad tiene?",
        "¿Cuál es su correo?",
        "¿Y su teléfono?"
    ]

    # Ejemplos de pruebas automatizadas
    pruebas = [
        "Ejecutar prueba básica (5 consultas)",
        "Ejecutar prueba con seguimiento (8 consultas)",
        "Ejecutar prueba completa (12 consultas)"
    ]

    while True:
        # Mostrar ejemplos
        print(f"\n{Fore.YELLOW}Ejemplos de consultas:{Style.RESET_ALL}")
        for i, ejemplo in enumerate(ejemplos, 1):
            print(f"{Fore.YELLOW}{i}. {ejemplo}{Style.RESET_ALL}")

        if session_context.interactions:
            print(f"\n{Fore.YELLOW}Ejemplos de seguimiento:{Style.RESET_ALL}")
            for i, seguimiento in enumerate(seguimientos, len(ejemplos) + 1):
                print(f"{Fore.YELLOW}{i}. {seguimiento}{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}Pruebas automatizadas:{Style.RESET_ALL}")
        for i, prueba in enumerate(pruebas, len(ejemplos) + len(seguimientos) + 1):
            print(f"{Fore.YELLOW}{i}. {prueba}{Style.RESET_ALL}")

        print(f"\n{Fore.YELLOW}Comandos especiales:{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}- 'salir': Terminar el programa{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}- 'reset': Reiniciar el contexto de la sesión{Style.RESET_ALL}")

        # Solicitar consulta al usuario
        print(f"\n{Fore.GREEN}Ingresa el número de un ejemplo o escribe tu propia consulta:{Style.RESET_ALL}")
        entrada = input("> ")

        # Procesar comandos especiales
        if entrada.lower() == "salir":
            print(f"{Fore.GREEN}¡Hasta luego! Los logs se guardaron en: {LOG_FILE}{Style.RESET_ALL}")
            break
        elif entrada.lower() == "reset":
            session_context.reset_session()
            print(f"{Fore.GREEN}Contexto de sesión reiniciado.{Style.RESET_ALL}")
            continue

        # Procesar entrada
        try:
            indice = int(entrada) - 1
            total_ejemplos = len(ejemplos) + (len(seguimientos) if session_context.interactions else 0)

            # Consulta individual
            if 0 <= indice < len(ejemplos):
                consulta = ejemplos[indice]
                visualizar_flujo_consulta(consulta)
            # Consulta de seguimiento
            elif len(ejemplos) <= indice < total_ejemplos and session_context.interactions:
                consulta = seguimientos[indice - len(ejemplos)]
                visualizar_flujo_consulta(consulta)
            # Prueba automatizada
            elif total_ejemplos <= indice < total_ejemplos + len(pruebas):
                prueba_index = indice - total_ejemplos

                if prueba_index == 0:  # Prueba básica
                    print(f"{Fore.GREEN}Ejecutando prueba básica...{Style.RESET_ALL}")
                    ejecutar_prueba_automatizada(ejemplos, silent=False)
                elif prueba_index == 1:  # Prueba con seguimiento
                    print(f"{Fore.GREEN}Ejecutando prueba con seguimiento...{Style.RESET_ALL}")
                    # Reiniciar contexto para prueba limpia
                    session_context.reset_session()
                    consultas_seguimiento = [ejemplos[0], seguimientos[0], ejemplos[1], seguimientos[1]]
                    ejecutar_prueba_automatizada(consultas_seguimiento, silent=False)
                elif prueba_index == 2:  # Prueba completa
                    print(f"{Fore.GREEN}Ejecutando prueba completa...{Style.RESET_ALL}")
                    # Reiniciar contexto para prueba limpia
                    session_context.reset_session()
                    consultas_completas = ejemplos + seguimientos + ["¿Quién es la persona más joven?", "¿Hay alguien que viva en Colonia Centro?", "¿Cuál es el género de Ana?"]
                    ejecutar_prueba_automatizada(consultas_completas, silent=False)
                else:
                    print(f"{Fore.RED}Opción de prueba no válida.{Style.RESET_ALL}")
            else:
                consulta = entrada
                visualizar_flujo_consulta(consulta)
        except ValueError:
            consulta = entrada
            visualizar_flujo_consulta(consulta)

if __name__ == "__main__":
    # Inicializar archivo de log
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write(f"LOGS DE FLUJO DE CONSULTA - {timestamp}\n")
        f.write(f"Archivo generado: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Ejecutar en modo interactivo
    modo_interactivo()
