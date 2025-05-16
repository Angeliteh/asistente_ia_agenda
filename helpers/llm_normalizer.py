#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Normalizador de claves semánticas utilizando LLM.
Este módulo proporciona funciones para normalizar claves semánticas
utilizando un modelo de lenguaje grande (LLM) para mejorar la consistencia
del caché semántico.
"""

from typing import Dict
import google.generativeai as genai
from config import GOOGLE_API_KEY
from helpers.llm_utils import llamar_llm

# Configurar API key explícitamente
genai.configure(api_key=GOOGLE_API_KEY)

# Caché de normalización (clave original -> clave normalizada)
normalizacion_cache: Dict[str, str] = {}

def normalizar_clave_con_llm(clave: str) -> str:
    """
    Normaliza una clave semántica utilizando el LLM para un mejor entendimiento semántico.

    Args:
        clave (str): Clave semántica original

    Returns:
        str: Clave normalizada
    """
    # Si la clave está vacía, devolver cadena vacía
    if not clave:
        return ""

    # Verificar si ya está en caché
    if clave in normalizacion_cache:
        return normalizacion_cache[clave]

    # Construir el prompt para el LLM
    prompt = f"""
    Normaliza esta clave semántica para un sistema de caché:

    "{clave}"

    Sigue estas reglas ESTRICTAMENTE:
    1. Convierte todo a minúsculas
    2. Elimina espacios y caracteres especiales
    3. Normaliza términos similares a una forma canónica, pero MANTÉN DISTINTAS CATEGORÍAS para diferentes tipos de información:
       - "teléfono", "celular", "móvil", "número", "tel", "cel" → "telefono"
       - "correo", "email", "mail", "e-mail", "correo electrónico" → "correo"
       - "dirección", "domicilio", "ubicación", "residencia", "vive" → "direccion"
       - "información", "datos", "detalles", "info" → "informacion"
       - "trabajo", "empleo", "puesto", "cargo", "función", "función específica" → "funcion"
       - "estudios", "nivel de estudios", "formación", "educación", "académico" → "estudios"
       - "doble plaza", "plaza doble", "dos plazas" → "doble_plaza"
       - "centro de trabajo", "CT", "escuela", "lugar de trabajo", "trabaja" → "centro_trabajo"
       - "fecha de ingreso", "antigüedad", "ingresó", "inicio" → "fecha_ingreso"
       - "zona", "sector", "área" → "zona"
       - "cantidad", "número de", "cuántos", "total de" → "conteo"
       - "docentes", "docentes frente a grupo", "profesores frente a grupo" → "docentes_frente_grupo"
       - "directores", "director" → "directores"
       - "subdirectores", "subdirector académico", "subdirector de gestión" → "subdirectores"
       - "maestros", "profesores" (cuando se usan genéricamente) → "personal_educativo"
    4. Para claves de personas, normaliza el nombre SIEMPRE en formato "nombre_apellido":
       - Elimina acentos y caracteres especiales
       - Usa solo nombre y apellido paterno (ej: "luis_perez")
       - NUNCA uses el formato "apellido_nombre"
       - Si el nombre aparece como "Pérez Luis", conviértelo a "luis_perez"
    5. Mantén la estructura básica "tipo:entidad:atributo"
    6. IMPORTANTE: Asegúrate de que consultas semánticamente similares generen EXACTAMENTE la MISMA clave normalizada

    Ejemplos OBLIGATORIOS a seguir:
    # Datos de contacto
    - "persona:Luis Pérez:teléfono" → "persona:luis_perez:telefono"
    - "persona:Luis Pérez:celular" → "persona:luis_perez:telefono"
    - "persona:Pérez Luis:correo" → "persona:luis_perez:correo"
    - "persona:Luis Pérez:email" → "persona:luis_perez:correo"
    - "persona:Juan Gómez:dirección" → "persona:juan_gomez:direccion"
    - "persona:Gómez Juan:domicilio" → "persona:juan_gomez:direccion"

    # Datos laborales
    - "persona:Luis Pérez:función específica" → "persona:luis_perez:funcion"
    - "persona:Luis Pérez:cargo" → "persona:luis_perez:funcion"
    - "persona:Luis Pérez:puesto" → "persona:luis_perez:funcion"

    # Datos académicos
    - "persona:Luis Pérez:nivel de estudios" → "persona:luis_perez:estudios"
    - "persona:Luis Pérez:formación académica" → "persona:luis_perez:estudios"

    # Datos administrativos
    - "persona:Luis Pérez:doble plaza" → "persona:luis_perez:doble_plaza"
    - "persona:Luis Pérez:plaza doble" → "persona:luis_perez:doble_plaza"

    # Datos de ubicación laboral
    - "persona:Luis Pérez:centro de trabajo" → "persona:luis_perez:centro_trabajo"
    - "persona:Luis Pérez:escuela" → "persona:luis_perez:centro_trabajo"

    # Datos de antigüedad
    - "persona:Luis Pérez:fecha de ingreso" → "persona:luis_perez:fecha_ingreso"
    - "persona:Luis Pérez:antigüedad" → "persona:luis_perez:fecha_ingreso"

    # Consultas de listado y estadísticas
    - "listado:zona:109:docentes" → "listado:zona_109:docentes_frente_grupo"
    - "listado:zona:109:docentes frente a grupo" → "listado:zona_109:docentes_frente_grupo"
    - "listado:zona:109:directores" → "listado:zona_109:directores"
    - "listado:zona:109:subdirectores" → "listado:zona_109:subdirectores"
    - "listado:zona:109:maestros" → "listado:zona_109:personal_educativo"
    - "conteo:zona:109:docentes" → "conteo:zona_109:docentes_frente_grupo"
    - "conteo:zona:109:directores" → "conteo:zona_109:directores"
    - "conteo:zona:109:subdirectores" → "conteo:zona_109:subdirectores"
    - "conteo:zona:109:maestros" → "conteo:zona_109:personal_educativo"

    # Datos generales
    - "persona:Ana Martínez:información" → "persona:ana_martinez:informacion"
    - "persona:Martínez Ana:datos" → "persona:ana_martinez:informacion"

    Devuelve SOLO la clave normalizada, sin explicaciones ni formato adicional.
    """

    # Llamar al LLM
    respuesta = llamar_llm(prompt)

    # Obtener solo el texto de la respuesta, sin formato adicional
    clave_normalizada = respuesta.text.strip()

    # Guardar en caché
    normalizacion_cache[clave] = clave_normalizada

    return clave_normalizada

def limpiar_cache_normalizacion() -> None:
    """
    Limpia el caché de normalización.
    """
    normalizacion_cache.clear()
