#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Prueba automatizada del asistente de agenda.
Este script simula consultas reales usando los datos del Excel.
"""

import time
import random
import os
from colorama import init, Fore, Style
import google.generativeai as genai
from config import GOOGLE_API_KEY
from helpers.dynamic_loader import cargar_agenda_dinamica
from helpers.enhanced_query import process_query

# Inicializar colorama para colores en la terminal
init()

# Configurar clave de API
genai.configure(api_key=GOOGLE_API_KEY)

# Ruta al archivo de datos
DATOS_FILE = "datos/agenda.xlsx"

# Función para simular la escritura humana (efecto de tipeo)
def escribir_con_efecto(texto, velocidad_min=0.03, velocidad_max=0.08):
    for caracter in texto:
        print(caracter, end='', flush=True)
        # Pausa más larga en signos de puntuación
        if caracter in ['.', ',', '!', '?', ':']:
            time.sleep(random.uniform(velocidad_min*2, velocidad_max*2))
        else:
            time.sleep(random.uniform(velocidad_min, velocidad_max))
    print()

# Función para simular el tiempo de procesamiento del asistente
def simular_procesamiento(tiempo_min=0.5, tiempo_max=2.0):
    tiempo = random.uniform(tiempo_min, tiempo_max)

    # Diferentes mensajes de "pensando"
    mensajes = [
        f"{Fore.YELLOW}🔄 Procesando...{Style.RESET_ALL}",
        f"{Fore.YELLOW}🤔 Déjame pensar...{Style.RESET_ALL}",
        f"{Fore.YELLOW}🔍 Buscando en la agenda...{Style.RESET_ALL}",
        f"{Fore.YELLOW}⌛ Un momento...{Style.RESET_ALL}",
        f"{Fore.YELLOW}💭 Mmm...{Style.RESET_ALL}"
    ]

    print(random.choice(mensajes))
    time.sleep(tiempo)

# Función para mostrar mensaje del humano con errores de tipeo ocasionales
def mensaje_humano(texto, probabilidad_error=0.3):
    print(f"\n{Fore.GREEN}👤 Usuario: {Style.RESET_ALL}", end="")

    # Simular errores de tipeo
    if random.random() < probabilidad_error and len(texto) > 10:
        # Elegir tipo de error
        tipo_error = random.choice(["typo", "backspace", "pausa"])

        if tipo_error == "typo":
            # Insertar un carácter incorrecto y corregirlo
            pos = random.randint(5, len(texto) - 5)
            char_incorrecto = random.choice("qwertyuiopasdfghjklzxcvbnm")
            texto_con_error = texto[:pos] + char_incorrecto + texto[pos:]

            # Escribir hasta el error
            for i in range(pos + 1):
                print(texto_con_error[i], end='', flush=True)
                time.sleep(random.uniform(0.03, 0.1))

            # Pausa para "darse cuenta"
            time.sleep(0.3)

            # Borrar el error
            print("\b \b", end='', flush=True)
            time.sleep(0.2)

            # Continuar escribiendo
            for i in range(pos, len(texto)):
                print(texto[i], end='', flush=True)
                time.sleep(random.uniform(0.03, 0.1))
            print()

        elif tipo_error == "backspace":
            # Escribir una palabra incorrecta y borrarla
            palabras = texto.split()
            if len(palabras) > 3:
                pos_palabra = random.randint(1, len(palabras) - 2)
                palabra_original = palabras[pos_palabra]
                palabra_incorrecta = palabra_original[:2] + random.choice("qwertyuiopasdfghjklzxcvbnm") + palabra_original[2:]

                # Reconstruir texto hasta la palabra incorrecta
                texto_hasta = " ".join(palabras[:pos_palabra])

                # Escribir hasta ahí
                escribir_con_efecto(texto_hasta + " ", 0.03, 0.1, end="")

                # Escribir palabra incorrecta
                escribir_con_efecto(palabra_incorrecta, 0.03, 0.1, end="")

                # Borrar palabra incorrecta
                for _ in range(len(palabra_incorrecta)):
                    print("\b \b", end='', flush=True)
                    time.sleep(0.05)

                # Escribir palabra correcta y resto del texto
                escribir_con_efecto(palabra_original + " " + " ".join(palabras[pos_palabra+1:]), 0.03, 0.1)
            else:
                escribir_con_efecto(texto, 0.03, 0.1)

        elif tipo_error == "pausa":
            # Hacer una pausa en medio de la escritura
            pos = random.randint(len(texto)//3, 2*len(texto)//3)

            # Escribir hasta la pausa
            for i in range(pos):
                print(texto[i], end='', flush=True)
                time.sleep(random.uniform(0.03, 0.1))

            # Pausa como si estuviera pensando
            time.sleep(random.uniform(0.5, 1.5))

            # Continuar escribiendo
            for i in range(pos, len(texto)):
                print(texto[i], end='', flush=True)
                time.sleep(random.uniform(0.03, 0.1))
            print()
    else:
        escribir_con_efecto(texto, 0.03, 0.1)

    time.sleep(0.5)

# Función para escribir con efecto y control de final de línea
def escribir_con_efecto(texto, velocidad_min=0.03, velocidad_max=0.08, end="\n"):
    for caracter in texto:
        print(caracter, end='', flush=True)
        # Pausa más larga en signos de puntuación
        if caracter in ['.', ',', '!', '?', ':']:
            time.sleep(random.uniform(velocidad_min*2, velocidad_max*2))
        else:
            time.sleep(random.uniform(velocidad_min, velocidad_max))
    print(end=end)

# Función para mostrar mensaje del asistente con más humanidad
def mensaje_asistente(texto, personalidad=0.7):
    simular_procesamiento()
    print(f"\n{Fore.BLUE}🤖 Asistente:{Style.RESET_ALL}")

    # Añadir elementos conversacionales según probabilidad
    if random.random() < personalidad:
        # Posibles muletillas iniciales
        muletillas_inicio = [
            "Mmm, ", "Veamos... ", "A ver... ", "Déjame ver... ",
            "Bueno, ", "Pues ", "Ah, ", "Oh, "
        ]

        # Posibles expresiones finales
        expresiones_finales = [
            " ¿Necesitas algo más?", " ¿Te sirve esta información?",
            " ¿Hay algo más que quieras saber?", " ¿Te puedo ayudar con algo más?",
            " 😊", " 👍", " ¿Está bien?"
        ]

        # Posibles expresiones intermedias
        expresiones_intermedias = [
            ", ¿sabes?", ", mira,", ", fíjate,", ", verás,"
        ]

        # Aplicar transformaciones
        texto_original = texto

        # Añadir muletilla inicial (30% de probabilidad)
        if random.random() < 0.3 and not texto.startswith(("Sí", "No", "Hay", "El", "La")):
            texto = random.choice(muletillas_inicio) + texto[0].lower() + texto[1:]

        # Añadir expresión intermedia (20% de probabilidad)
        if random.random() < 0.2 and len(texto) > 20 and "," in texto:
            partes = texto.split(",", 1)
            if len(partes) > 1:
                texto = partes[0] + random.choice(expresiones_intermedias) + partes[1]

        # Añadir expresión final (40% de probabilidad)
        if random.random() < 0.4 and not texto.endswith(("?", "!", "...")):
            texto = texto.rstrip(".") + random.choice(expresiones_finales)

    # Dividir respuestas largas en fragmentos para pausas naturales
    if len(texto) > 100:
        fragmentos = []
        palabras = texto.split(' ')
        fragmento_actual = ""

        for palabra in palabras:
            if len(fragmento_actual) + len(palabra) < 80:
                fragmento_actual += palabra + " "
            else:
                fragmentos.append(fragmento_actual)
                fragmento_actual = palabra + " "

        if fragmento_actual:
            fragmentos.append(fragmento_actual)

        for fragmento in fragmentos:
            escribir_con_efecto(fragmento, 0.01, 0.03)
            time.sleep(0.2)
    else:
        escribir_con_efecto(texto, 0.01, 0.03)

    # Pausa variable después de responder
    time.sleep(random.uniform(0.5, 1.2))

# Función para procesar una consulta real
def procesar_consulta_real(pregunta, registros, esquema, mapeo_columnas):
    # Usar el enfoque centralizado de consultas
    resultado = process_query(pregunta, registros, esquema, mapeo_columnas)

    # Devolver solo la respuesta textual
    return resultado["response"]

# Función principal para ejecutar la prueba automatizada
def ejecutar_prueba_automatizada():
    print(f"\n{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}📱 PRUEBA AUTOMATIZADA DEL ASISTENTE DE AGENDA{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")

    # Cargar datos reales
    print(f"{Fore.YELLOW}📊 Cargando datos reales desde {DATOS_FILE}...{Style.RESET_ALL}")
    resultado = cargar_agenda_dinamica(DATOS_FILE)

    if resultado["error"]:
        print(f"{Fore.RED}❌ Error al cargar datos: {resultado['error']}{Style.RESET_ALL}")
        return

    registros = resultado["registros"]
    esquema = resultado["esquema"]
    mapeo_columnas = resultado["mapeo_columnas"]

    print(f"{Fore.GREEN}✅ Datos cargados: {len(registros)} registros{Style.RESET_ALL}")

    # Definir variantes de consultas para cada tipo
    variantes_consultas = {
        "telefono_juan": [
            "¿Cuál es el teléfono de Juan Pérez?",
            "Me puedes dar el número de Juan?",
            "Necesito llamar a Juan, ¿tienes su teléfono?",
            "¿Tienes el número de Juan por ahí?"
        ],
        "direccion_ana": [
            "¿Qué dirección tiene Ana Ramírez?",
            "¿Dónde vive Ana?",
            "Necesito ir a casa de Ana, ¿cuál era su dirección?",
            "¿Me puedes decir dónde vive Ana Ramírez?"
        ],
        "correo_carlos": [
            "¿Cuál es el correo electrónico de Carlos Martínez?",
            "Necesito el email de Carlos",
            "¿Tienes el correo de Carlos por ahí?",
            "¿Me pasas el mail de Carlos?"
        ],
        "edad_lucia": [
            "¿Cuántos años tiene Lucía Gómez?",
            "¿Sabes la edad de Lucía?",
            "¿Qué edad tiene Lucía?",
            "¿Cuántos años cumplió Lucía?"
        ],
        "persona_joven": [
            "¿Quién es la persona más joven?",
            "¿Cuál es el contacto más joven que tengo?",
            "¿Quién tiene menos años en mi agenda?",
            "De todos mis contactos, ¿quién es el más joven?"
        ],
        "mayores_30": [
            "¿Quién tiene más de 30 años?",
            "¿Qué contactos son mayores de 30?",
            "Dime quiénes pasan de 30 años",
            "¿Hay alguien mayor de 30 en mi agenda?"
        ],
        "total_personas": [
            "¿Cuántas personas hay en la agenda?",
            "¿Cuántos contactos tengo guardados?",
            "¿Cuánta gente hay en total?",
            "¿Número total de contactos?"
        ],
        "total_hombres": [
            "¿Cuántos hombres hay?",
            "¿Cuántos contactos masculinos tengo?",
            "¿Número de hombres en la agenda?",
            "¿Cuántos de mis contactos son hombres?"
        ],
        "info_juan": [
            "Dame toda la información de Juan Pérez",
            "Quiero saber todo sobre Juan",
            "¿Qué datos tenemos de Juan Pérez?",
            "Muéstrame el perfil completo de Juan"
        ],
        "comparacion_edad": [
            "¿Quién es mayor, Juan o Ana?",
            "Entre Juan y Ana, ¿quién tiene más años?",
            "¿Ana es mayor que Juan o al revés?",
            "¿Quién nació primero, Juan o Ana?"
        ],
        "colonia_centro": [
            "¿Hay alguien que viva en Colonia Centro?",
            "¿Quién vive en Colonia Centro?",
            "¿Tengo contactos en Colonia Centro?",
            "¿Alguno de mis contactos tiene dirección en Colonia Centro?"
        ]
    }

    # Seleccionar una variante aleatoria para cada tipo de consulta
    consultas_seleccionadas = []
    for tipo, variantes in variantes_consultas.items():
        consultas_seleccionadas.append(random.choice(variantes))

    # Mensaje de bienvenida
    mensaje_asistente("¡Hola! Soy tu asistente de agenda. Puedo responder preguntas sobre tus contactos. ¿En qué puedo ayudarte?")

    # Procesar cada consulta
    for i, consulta in enumerate(consultas_seleccionadas):
        # Simular pregunta del usuario
        mensaje_humano(consulta)

        # Procesar la consulta con datos reales
        respuesta = procesar_consulta_real(consulta, registros, esquema, mapeo_columnas)

        # Mostrar respuesta del asistente
        mensaje_asistente(respuesta)

        # Añadir consultas de seguimiento ocasionalmente (30% de probabilidad)
        if i < len(consultas_seleccionadas) - 1 and random.random() < 0.3:
            # Extraer nombre de la consulta anterior si es posible
            palabras = consulta.split()
            posibles_nombres = [palabra for palabra in palabras if palabra[0].isupper() and len(palabra) > 3]

            # Si encontramos un posible nombre, usarlo para seguimiento
            if posibles_nombres:
                persona = posibles_nombres[0].rstrip('?.,;:!')

                # Posibles preguntas de seguimiento
                seguimientos = [
                    f"Y también, ¿cuál era el correo de {persona}?",
                    f"Por cierto, ¿qué edad tiene {persona}?",
                    f"Ya que estamos, ¿dónde vive {persona}?",
                    f"Mmm, y ¿cuál era el teléfono de {persona}?"
                ]

                # Seleccionar una pregunta de seguimiento
                seguimiento = random.choice(seguimientos)

                # Simular una pausa antes de la pregunta de seguimiento
                time.sleep(random.uniform(1.0, 2.0))

                # Hacer la pregunta de seguimiento
                mensaje_humano(seguimiento)

                # Procesar la consulta de seguimiento
                respuesta_seguimiento = procesar_consulta_real(seguimiento, registros, esquema, mapeo_columnas)

                # Mostrar respuesta del asistente
                mensaje_asistente(respuesta_seguimiento)

        # Añadir reacciones a las respuestas (20% de probabilidad)
        elif random.random() < 0.2:
            # Posibles reacciones
            reacciones = [
                "Ah, perfecto!",
                "Gracias!",
                "Ok, entendido",
                "Genial, gracias",
                "Mmm, interesante",
                "Vaya, no lo sabía"
            ]

            # Seleccionar una reacción
            reaccion = random.choice(reacciones)

            # Simular una pausa antes de la reacción
            time.sleep(random.uniform(0.8, 1.5))

            # Mostrar la reacción
            mensaje_humano(reaccion)

            # Respuesta del asistente a la reacción
            respuestas_reaccion = [
                "¡De nada! ¿Necesitas algo más?",
                "Para eso estoy. ¿Alguna otra consulta?",
                "¡Claro! ¿Puedo ayudarte con algo más?",
                "Me alegra ser útil. ¿Qué más quieres saber?"
            ]

            respuesta_reaccion = random.choice(respuestas_reaccion)
            mensaje_asistente(respuesta_reaccion)

            # No es necesario actualizar contexto en esta versión simplificada

        # Pausa variable entre consultas
        time.sleep(random.uniform(1.0, 2.5))

    # Mensaje de despedida
    mensaje_humano("Gracias por la información, eso es todo por ahora.")
    mensaje_asistente("¡Ha sido un placer ayudarte! Si necesitas consultar algo más de tu agenda, aquí estaré. ¡Hasta pronto!")

    print(f"\n{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}🏁 FIN DE LA PRUEBA AUTOMATIZADA{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'=' * 60}{Style.RESET_ALL}")

if __name__ == "__main__":
    ejecutar_prueba_automatizada()
