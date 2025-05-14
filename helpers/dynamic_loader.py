"""
Módulo de carga dinámica para el asistente de agenda.

Este módulo permite cargar datos desde cualquier estructura tabular
sin depender de nombres de columnas específicos.
"""

import pandas as pd
import json
import re
import os

def cargar_agenda_dinamica(ruta_excel):
    """
    Carga datos desde cualquier archivo Excel con estructura tabular,
    sin asumir nombres de columnas específicos.

    Args:
        ruta_excel (str): Ruta al archivo Excel

    Returns:
        dict: Diccionario con los siguientes elementos:
            - registros: Lista de diccionarios con los datos
            - esquema: Información sobre la estructura de los datos
            - mapeo_columnas: Diccionario que mapea nombres normalizados a originales
            - error: Mensaje de error (None si no hay errores)
    """
    try:
        # Verificar que el archivo existe
        if not os.path.exists(ruta_excel):
            return {
                "registros": [],
                "esquema": {},
                "mapeo_columnas": {},
                "error": f"El archivo {ruta_excel} no existe"
            }

        # Cargar el archivo Excel
        df = pd.read_excel(ruta_excel)

        # Verificar que hay datos
        if df.empty:
            return {
                "registros": [],
                "esquema": {},
                "mapeo_columnas": {},
                "error": "El archivo está vacío"
            }

        # Normalizar nombres de columnas
        columnas_originales = df.columns.tolist()
        columnas_normalizadas = [
            c.strip().lower().replace(" ", "_").replace("-", "_")
            for c in columnas_originales
        ]

        # Crear mapeo entre nombres originales y normalizados
        mapeo_columnas = dict(zip(columnas_normalizadas, columnas_originales))

        # Renombrar columnas en el DataFrame
        df.columns = columnas_normalizadas

        # Rellenar valores faltantes con cadenas vacías
        df = df.fillna("")

        # Detectar tipos de datos y posibles columnas clave
        esquema = detectar_esquema(df, columnas_normalizadas)

        # Convertir a lista de diccionarios
        registros = df.to_dict(orient="records")

        return {
            "registros": registros,
            "esquema": esquema,
            "mapeo_columnas": mapeo_columnas,
            "error": None
        }

    except Exception as e:
        return {
            "registros": [],
            "esquema": {},
            "mapeo_columnas": {},
            "error": str(e)
        }

def detectar_esquema(df, columnas):
    """
    Detecta automáticamente el esquema de los datos.

    Args:
        df (DataFrame): DataFrame de pandas con los datos
        columnas (list): Lista de nombres de columnas normalizados

    Returns:
        dict: Diccionario con información sobre cada columna
    """
    esquema = {}

    # Patrones para reconocer tipos de columnas por su nombre
    patrones = {
        "identificador": ["id", "codigo", "clave", "identificador"],
        "nombre": ["nombre", "name", "apellido", "apellidos", "completo"],
        "telefono": ["telefono", "tel", "celular", "movil", "phone"],
        "correo": ["correo", "email", "mail", "e-mail", "electronico"],
        "direccion": ["direccion", "domicilio", "ubicacion", "address"],
        "edad": ["edad", "años", "age", "year"],
        "genero": ["genero", "sexo", "gender", "sex"]
    }

    # Analizar cada columna
    for columna in columnas:
        # Detectar tipo de datos
        tipo_datos = inferir_tipo_datos(df[columna])

        # Detectar categoría de la columna por su nombre
        categoria = "desconocido"
        for cat, palabras_clave in patrones.items():
            if any(palabra in columna for palabra in palabras_clave):
                categoria = cat
                break

        # Guardar información en el esquema
        esquema[columna] = {
            "tipo_datos": tipo_datos,
            "categoria": categoria,
            "valores_unicos": df[columna].nunique() if len(df) > 0 else 0
        }

        # Detectar si es posible columna clave (identificador único)
        if esquema[columna]["valores_unicos"] == len(df) and len(df) > 0:
            esquema[columna]["posible_clave"] = True

    return esquema

def inferir_tipo_datos(serie):
    """
    Infiere el tipo de datos de una columna analizando sus valores.

    Args:
        serie (Series): Serie de pandas con los valores de una columna

    Returns:
        str: Tipo de datos inferido ('entero', 'decimal', 'fecha', 'booleano', 'categoria', 'texto')
    """
    # Si todos los valores son numéricos
    if pd.api.types.is_numeric_dtype(serie) and not serie.isnull().all():
        # Distinguir entre enteros y decimales
        if all(float(x).is_integer() for x in serie.dropna()):
            return "entero"
        else:
            return "decimal"

    # Si todos los valores son fechas
    elif pd.api.types.is_datetime64_dtype(serie):
        return "fecha"

    # Intentar convertir a fecha si no es ya un tipo fecha
    elif pd.to_datetime(serie, errors='coerce').notna().all() and not serie.isnull().all():
        return "fecha"

    # Si todos los valores son booleanos
    elif pd.api.types.is_bool_dtype(serie):
        return "booleano"

    # Intentar detectar booleanos en formato texto
    elif all(str(x).lower() in ['true', 'false', '1', '0', 'sí', 'si', 'no', 'verdadero', 'falso']
             for x in serie.dropna()):
        return "booleano"

    # Si hay pocos valores únicos en proporción al total, podría ser una categoría
    elif serie.nunique() < len(serie) * 0.2 and serie.nunique() < 10 and len(serie) > 5:
        return "categoria"

    # Por defecto, asumir texto
    else:
        return "texto"

# Esta función ya no se usa, se mantiene por compatibilidad
# El sistema ahora usa el enfoque de dos pasos en enhanced_query.py
def generar_prompt_dinamico(pregunta, datos, esquema, mapeo_columnas):
    """
    DEPRECATED: Esta función ya no se usa.
    El sistema ahora usa el enfoque de dos pasos en enhanced_query.py

    Se mantiene por compatibilidad con código existente.
    """
    from helpers.enhanced_query import generate_natural_response, extract_query_parameters, search_data

    # Extraer parámetros
    parametros = extract_query_parameters(pregunta)

    # Buscar datos relevantes
    datos_relevantes = search_data(parametros, datos)

    # Generar respuesta
    respuesta = generate_natural_response(pregunta, datos_relevantes)

    return f"""
    DEPRECATED: Esta función ya no se usa.
    El sistema ahora usa el enfoque de dos pasos en enhanced_query.py

    Consulta original: {pregunta}
    Respuesta generada: {respuesta}
    """
