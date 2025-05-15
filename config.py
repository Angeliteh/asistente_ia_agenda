#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuración centralizada para el Asistente de Agenda.
Este archivo contiene todas las constantes, rutas y parámetros utilizados por el sistema.
"""

import os

# API Keys
GOOGLE_API_KEY = "AIzaSyAcn-8Cs8iPE61xIfwrtLHdE3jKn8Ceih8"

# Rutas de archivos
DATA_DIR = "datos"
DB_PATH = os.path.join(DATA_DIR, "agenda.db")
EXCEL_PATH = os.path.join(DATA_DIR, "agenda_real.xlsx")

# Configuración de la base de datos
DB_TABLE = "contactos"
DB_INDICES = ["nombre_completo", "zona", "funcion"]
DB_PREVIEW_LIMIT = 20
DB_EXAMPLE_LIMIT = 3

# Configuración de modelos LLM
LLM_PRIMARY_MODEL = "gemini-2.0-flash"
LLM_FALLBACK_MODEL = "gemini-1.5-flash"
LLM_TEMPERATURE = 0.2
LLM_TOP_P = 0.95
LLM_TOP_K = 40
LLM_MAX_TOKENS = 2048
LLM_FALLBACK_MAX_TOKENS = 1024

# Configuración de seguridad para LLM
LLM_SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    }
]

# Límites y umbrales
MAX_RESULTS_DISPLAY = 50
MAX_HISTORY_SIZE = 10
MAX_REFINEMENTS = 2

# Mapeo de atributos (para normalización)
ATTRIBUTE_MAPPING = {
    "telefono": ["telefono", "celular", "teléfono", "móvil", "movil", "numero", "número", "contacto"],
    "correo": ["correo", "email", "e-mail", "correo_electronico", "correo electrónico", "mail"],
    "direccion": ["direccion", "dirección", "domicilio", "ubicación", "ubicacion", "vive", "casa"],
    "funcion": ["funcion", "función", "puesto", "cargo", "rol", "trabajo", "posición", "posicion"],
    "zona": ["zona", "área", "area", "sector", "región", "region"],
    "estudios": ["estudios", "educación", "educacion", "formación", "formacion", "título", "titulo", "grado"],
    "estado_civil": ["estado_civil", "estado civil", "civil", "casado", "soltero", "divorciado"],
    "antiguedad": ["antiguedad", "antigüedad", "tiempo", "años", "experiencia"]
}
