#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para probar la normalización de claves semánticas con LLM.
Este script verifica que consultas semánticamente similares generen
la misma clave normalizada.
"""

import time
import google.generativeai as genai
from config import GOOGLE_API_KEY
from helpers.llm_normalizer import normalizar_clave_con_llm, normalizacion_cache
from helpers.semantic_cache import semantic_cache

def probar_normalizacion():
    """
    Prueba la normalización de claves semánticas con diferentes ejemplos.
    """
    # Configurar API key explícitamente
    print(f"Configurando API key: {GOOGLE_API_KEY[:5]}...{GOOGLE_API_KEY[-5:]}")
    genai.configure(api_key=GOOGLE_API_KEY)

    print("=" * 60)
    print("PRUEBA DE NORMALIZACIÓN DE CLAVES SEMÁNTICAS CON LLM")
    print("=" * 60)

    # Probar con varios ejemplos para verificar consistencia
    print("\nPruebas de normalización:")
    print("-" * 40)

    # Ejemplos de claves semánticas agrupadas por similitud
    ejemplos = [
        # Grupo 1: Teléfonos y contacto
        ["persona:luis_perez:telefono", "persona:Luis Pérez:celular"],

        # Grupo 2: Correos
        ["persona:maria_rodriguez:correo", "persona:María Rodríguez:email"],

        # Grupo 3: Direcciones
        ["persona:juan_gomez:direccion", "persona:Juan Gómez:domicilio"],

        # Grupo 4: Información general
        ["persona:ana_martinez:informacion", "persona:Ana Martínez:datos"]
    ]

    for i, grupo in enumerate(ejemplos):
        print(f"\nGrupo {i+1}:")
        claves_normalizadas = []

        for clave in grupo:
            # Medir tiempo de normalización
            inicio = time.time()
            clave_normalizada = normalizar_clave_con_llm(clave)
            fin = time.time()

            claves_normalizadas.append(clave_normalizada)

            print(f"Original: {clave}")
            print(f"Normalizada: {clave_normalizada}")
            print(f"Tiempo: {(fin - inicio):.4f}s")
            print("-" * 30)

        # Verificar consistencia en el grupo
        consistente = all(clave == claves_normalizadas[0] for clave in claves_normalizadas)
        print(f"Consistencia: {'✅ CONSISTENTE' if consistente else '❌ INCONSISTENTE'}")

    # Probar el caché semántico
    print("\n" + "=" * 60)
    print("PRUEBA DEL CACHÉ SEMÁNTICO")
    print("=" * 60)

    # Definir claves para pruebas de caché
    clave_telefono = "persona:luis_perez:telefono"
    clave_celular = "persona:Luis Pérez:celular"

    # Guardar en caché
    resultado = {"respuesta": "El teléfono de Luis Pérez es 555-1234"}
    semantic_cache.set(clave_telefono, resultado)
    print(f"Guardado en caché: {clave_telefono} -> {resultado['respuesta']}")

    # Probar recuperación con clave similar
    print(f"\nIntentando recuperar con clave similar: {clave_celular}")

    resultado_recuperado = semantic_cache.get(clave_celular)
    if resultado_recuperado:
        print(f"Recuperado de caché: {clave_celular} -> {resultado_recuperado['respuesta']} ✅")
    else:
        print(f"No encontrado en caché: {clave_celular} ❌")

    # Mostrar estadísticas del caché
    print("\nEstadísticas del caché:")
    print(semantic_cache.get_stats())

if __name__ == "__main__":
    probar_normalizacion()
