#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Adaptador para SQLite.
Este módulo proporciona funciones para convertir los datos de la agenda a una base de datos SQLite
y realizar consultas SQL directamente.
"""

import os
import sqlite3
import json
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

# Directorio para la base de datos
DB_DIR = "datos"
DB_PATH = os.path.join(DB_DIR, "agenda.db")

def crear_base_datos(registros: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Crea una base de datos SQLite a partir de los registros de la agenda.

    Args:
        registros: Lista de diccionarios con los datos de la agenda

    Returns:
        dict: Resultado de la operación
    """
    resultado = {
        "error": None,
        "mensaje": "",
        "db_path": DB_PATH
    }

    try:
        # Asegurarse de que el directorio existe
        os.makedirs(DB_DIR, exist_ok=True)

        # Eliminar la base de datos si ya existe
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)

        # Crear conexión a la base de datos
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Crear tabla para los contactos
        cursor.execute('''
        CREATE TABLE contactos (
            id INTEGER PRIMARY KEY,
            nombre TEXT,
            apellido_paterno TEXT,
            apellido_materno TEXT,
            nombre_completo TEXT,
            nombre_alternativo TEXT,
            telefono TEXT,
            celular TEXT,
            correo_electronico TEXT,
            direccion TEXT,
            codigo_postal TEXT,
            ciudad TEXT,
            estado TEXT,
            pais TEXT,
            fecha_nacimiento TEXT,
            edad INTEGER,
            genero TEXT,
            estado_civil TEXT,
            profesion TEXT,
            funcion TEXT,
            centro_trabajo TEXT,
            sector TEXT,
            zona TEXT,
            modalidad TEXT,
            estudios TEXT,
            fecha_ingreso TEXT,
            rfc TEXT,
            curp TEXT,
            antiguedad INTEGER,
            observaciones TEXT
        )
        ''')

        # Insertar registros
        for i, registro in enumerate(registros):
            # Preparar los campos
            campos = {
                "id": i + 1,
                "nombre_completo": registro.get("nombre", "")
            }

            # Extraer nombre, apellido paterno y materno
            nombre_completo = registro.get("nombre", "")
            partes_nombre = nombre_completo.split()

            if len(partes_nombre) >= 3:
                campos["nombre"] = " ".join(partes_nombre[:-2])
                campos["apellido_paterno"] = partes_nombre[-2]
                campos["apellido_materno"] = partes_nombre[-1]
            elif len(partes_nombre) == 2:
                campos["nombre"] = partes_nombre[0]
                campos["apellido_paterno"] = partes_nombre[1]
                campos["apellido_materno"] = ""
            else:
                campos["nombre"] = nombre_completo
                campos["apellido_paterno"] = ""
                campos["apellido_materno"] = ""

            # Copiar el resto de campos
            for campo, valor in registro.items():
                if campo != "nombre":
                    campos[campo.lower()] = valor

            # Preparar la consulta SQL
            campos_str = ", ".join(campos.keys())
            placeholders = ", ".join(["?" for _ in campos])

            # Ejecutar la consulta
            cursor.execute(
                f"INSERT INTO contactos ({campos_str}) VALUES ({placeholders})",
                list(campos.values())
            )

        # Crear índices para búsquedas rápidas
        cursor.execute("CREATE INDEX idx_nombre ON contactos (nombre_completo)")
        cursor.execute("CREATE INDEX idx_zona ON contactos (zona)")
        cursor.execute("CREATE INDEX idx_funcion ON contactos (funcion)")

        # Guardar cambios
        conn.commit()
        conn.close()

        resultado["mensaje"] = f"Base de datos creada con éxito en {DB_PATH} con {len(registros)} registros"

    except Exception as e:
        resultado["error"] = str(e)
        resultado["mensaje"] = f"Error al crear la base de datos: {str(e)}"

    return resultado

def ejecutar_consulta(consulta: str, parametros: Optional[Tuple] = None) -> Dict[str, Any]:
    """
    Ejecuta una consulta SQL en la base de datos.

    Args:
        consulta: Consulta SQL a ejecutar
        parametros: Parámetros para la consulta (opcional)

    Returns:
        dict: Resultado de la consulta
    """
    resultado = {
        "error": None,
        "registros": [],
        "columnas": [],
        "total": 0
    }

    try:
        # Verificar que la base de datos existe
        if not os.path.exists(DB_PATH):
            resultado["error"] = f"La base de datos no existe en {DB_PATH}"
            return resultado

        # Crear conexión a la base de datos
        conn = sqlite3.connect(DB_PATH)

        # Convertir resultados a diccionarios
        conn.row_factory = sqlite3.Row

        cursor = conn.cursor()

        # Ejecutar la consulta
        if parametros:
            cursor.execute(consulta, parametros)
        else:
            cursor.execute(consulta)

        # Obtener resultados
        filas = cursor.fetchall()

        # Convertir a lista de diccionarios
        resultado["columnas"] = [desc[0] for desc in cursor.description]
        resultado["registros"] = [dict(fila) for fila in filas]
        resultado["total"] = len(resultado["registros"])

        conn.close()

    except Exception as e:
        resultado["error"] = str(e)

    return resultado

def normalizar_texto(texto: str) -> str:
    """
    Normaliza un texto para búsquedas:
    - Convierte a minúsculas
    - Elimina espacios adicionales
    - Elimina acentos

    Args:
        texto: Texto a normalizar

    Returns:
        str: Texto normalizado
    """
    import unicodedata

    if not texto:
        return ""

    # Convertir a string si no lo es
    texto = str(texto)

    # Convertir a minúsculas
    texto = texto.lower()

    # Eliminar espacios adicionales
    texto = " ".join(texto.split())

    # Eliminar acentos
    texto = ''.join(c for c in unicodedata.normalize('NFD', texto)
                    if unicodedata.category(c) != 'Mn')

    return texto

# Mapeo de atributos a columnas de la base de datos
MAPEO_ATRIBUTOS = {
    "telefono": ["telefono", "celular", "teléfono", "móvil", "movil", "numero", "número", "contacto"],
    "direccion": ["direccion", "dirección", "domicilio", "casa", "ubicación", "ubicacion", "vive", "domicilio"],
    "correo_electronico": ["correo_electronico", "correo", "email", "mail", "correo electrónico", "e-mail"],
    "funcion": ["funcion", "función", "trabajo", "empleo", "puesto", "cargo", "director", "docente", "subdirector"],
    "estudios": ["estudios", "grado", "educación", "educacion", "formación", "formacion", "licenciatura", "maestría", "doctorado"],
    "estado_civil": ["estado_civil", "casado", "soltero", "divorciado", "viudo", "civil"],
    "zona": ["zona", "área", "area", "sector", "región", "region"],
    "centro_trabajo": ["centro_trabajo", "escuela", "centro", "trabajo", "institución", "institucion"],
    "fecha_ingreso": ["fecha_ingreso", "ingreso", "antigüedad", "antiguedad", "cuando ingresó", "cuando ingreso"]
}

def mapear_atributo(atributo: str) -> str:
    """
    Mapea un atributo de la consulta a una columna de la base de datos.

    Args:
        atributo: Atributo a mapear

    Returns:
        str: Columna de la base de datos
    """
    if not atributo:
        return ""

    atributo_norm = normalizar_texto(atributo)

    for columna, sinonimos in MAPEO_ATRIBUTOS.items():
        if atributo_norm in sinonimos or any(s in atributo_norm for s in sinonimos):
            return columna

    return atributo

def generar_consulta_sql(parametros: Dict[str, Any]) -> Dict[str, Any]:
    """
    Genera una consulta SQL a partir de parámetros extraídos de la consulta en lenguaje natural.

    Args:
        parametros: Diccionario con los parámetros extraídos

    Returns:
        dict: Consulta SQL generada y parámetros
    """
    resultado = {
        "consulta": "",
        "parametros": [],
        "tipo": parametros.get("tipo_consulta", "")
    }

    # Mapear atributo si existe
    if "atributo" in parametros and parametros["atributo"]:
        parametros["atributo"] = mapear_atributo(parametros["atributo"])

    # Consulta de información específica
    if parametros.get("tipo_consulta") == "informacion":
        persona = parametros.get("persona", "")
        atributo = parametros.get("atributo", "")

        if persona:
            # Normalizar nombre para búsqueda
            persona_norm = normalizar_texto(persona)

            # Dividir en tokens para búsqueda más flexible
            tokens = persona_norm.split()

            # Construir condiciones para cada token
            condiciones = []
            params = []

            # Búsqueda exacta primero (mayor prioridad)
            condiciones.append("LOWER(nombre_completo) LIKE ?")
            params.append(f"%{persona_norm}%")

            condiciones.append("LOWER(nombre_alternativo) LIKE ?")
            params.append(f"%{persona_norm}%")

            # Búsqueda por nombre invertido (apellidos primero)
            # Ejemplo: "Luis Pérez" también busca "Pérez Luis"
            if len(tokens) >= 2:
                nombre_invertido = " ".join(tokens[::-1])
                condiciones.append("LOWER(nombre_completo) LIKE ?")
                params.append(f"%{nombre_invertido}%")

                condiciones.append("LOWER(nombre_alternativo) LIKE ?")
                params.append(f"%{nombre_invertido}%")

            # Búsqueda por tokens individuales
            for token in tokens:
                if len(token) > 2:  # Ignorar tokens muy cortos
                    condiciones.append("LOWER(nombre_completo) LIKE ?")
                    params.append(f"%{token}%")

                    condiciones.append("LOWER(nombre_alternativo) LIKE ?")
                    params.append(f"%{token}%")

                    condiciones.append("LOWER(nombre) LIKE ?")
                    params.append(f"%{token}%")

                    condiciones.append("LOWER(apellido_paterno) LIKE ?")
                    params.append(f"%{token}%")

                    condiciones.append("LOWER(apellido_materno) LIKE ?")
                    params.append(f"%{token}%")

            # Búsqueda por combinaciones de tokens (para nombres compuestos)
            if len(tokens) >= 3:
                for i in range(len(tokens) - 1):
                    token_combinado = f"{tokens[i]} {tokens[i+1]}"
                    condiciones.append("LOWER(nombre_completo) LIKE ?")
                    params.append(f"%{token_combinado}%")

                    condiciones.append("LOWER(nombre_alternativo) LIKE ?")
                    params.append(f"%{token_combinado}%")

            # Construir consulta SQL
            if atributo:
                # Si el atributo es teléfono, incluir también celular
                campos_select = atributo
                if atributo == "telefono":
                    campos_select = "telefono, celular"

                # Consulta de un atributo específico de una persona
                resultado["consulta"] = f"""
                SELECT {campos_select}, nombre_completo,
                       CASE
                           WHEN LOWER(nombre_completo) LIKE ? THEN 1
                           WHEN LOWER(nombre_alternativo) LIKE ? THEN 1
                           ELSE 0
                       END as exact_match
                FROM contactos
                WHERE {" OR ".join(condiciones)}
                ORDER BY exact_match DESC, nombre_completo
                """
                # Añadir parámetros para exact_match
                params_exact = [f"%{persona_norm}%", f"%{persona_norm}%"] + params
                resultado["parametros"] = params_exact
            else:
                # Consulta de toda la información de una persona
                resultado["consulta"] = f"""
                SELECT *,
                       CASE
                           WHEN LOWER(nombre_completo) LIKE ? THEN 1
                           WHEN LOWER(nombre_alternativo) LIKE ? THEN 1
                           ELSE 0
                       END as exact_match
                FROM contactos
                WHERE {" OR ".join(condiciones)}
                ORDER BY exact_match DESC, nombre_completo
                """
                # Añadir parámetros para exact_match
                params_exact = [f"%{persona_norm}%", f"%{persona_norm}%"] + params
                resultado["parametros"] = params_exact

    # Consulta de filtrado
    elif parametros.get("tipo_consulta") == "filtrado":
        atributo = parametros.get("atributo", "")
        condicion = parametros.get("condicion", "")
        valor = parametros.get("valor", "")

        # Detectar consultas de listado
        query_text = parametros.get("query", "").lower()
        is_listing_query = any(term in query_text.lower() for term in [
            "quién", "quien", "quienes", "quiénes", "cuáles", "cuales",
            "qué personas", "que personas", "lista", "listar", "enumera",
            "enumerar", "dime todos", "dime todas", "menciona", "dame"
        ])

        # Normalizar valor para búsqueda
        if valor:
            valor_norm = normalizar_texto(valor)

        if atributo and (condicion or is_listing_query):
            # Mapear condiciones a operadores SQL
            operadores = {
                "igual_a": "=",
                "mayor_que": ">",
                "menor_que": "<"
            }

            # Si es una consulta de listado sin condición específica
            if is_listing_query and not condicion:
                condicion = "igual_a"

            # Añadir información sobre el tipo de consulta
            resultado["is_listing_query"] = is_listing_query

            # Manejar casos especiales para ciertos atributos
            if atributo == "funcion" and valor:
                # Para funciones, permitir búsqueda parcial (LIKE)
                resultado["consulta"] = """
                SELECT nombre_completo, funcion, centro_trabajo, zona
                FROM contactos
                WHERE LOWER(funcion) LIKE ?
                ORDER BY funcion, nombre_completo
                """
                resultado["parametros"] = [f"%{valor_norm}%"]
                resultado["descripcion"] = f"Personas con función que contiene '{valor}'"

            elif atributo == "zona" and valor:
                # Para zonas, mostrar más información relevante
                resultado["consulta"] = """
                SELECT nombre_completo, zona, funcion, centro_trabajo
                FROM contactos
                WHERE zona = ?
                ORDER BY funcion, nombre_completo
                """
                resultado["parametros"] = [valor]
                resultado["descripcion"] = f"Personas que trabajan en la zona {valor}"

            elif atributo == "estudios" and valor:
                # Para estudios, permitir búsqueda parcial
                resultado["consulta"] = """
                SELECT nombre_completo, estudios, funcion
                FROM contactos
                WHERE LOWER(estudios) LIKE ?
                ORDER BY funcion, nombre_completo
                """
                resultado["parametros"] = [f"%{valor_norm}%"]
                resultado["descripcion"] = f"Personas con estudios que contienen '{valor}'"

            elif atributo == "centro_trabajo" and valor:
                # Para centro de trabajo, permitir búsqueda parcial
                resultado["consulta"] = """
                SELECT nombre_completo, centro_trabajo, funcion, zona
                FROM contactos
                WHERE LOWER(centro_trabajo) LIKE ?
                ORDER BY funcion, nombre_completo
                """
                resultado["parametros"] = [f"%{valor_norm}%"]
                resultado["descripcion"] = f"Personas que trabajan en '{valor}'"

            # Consulta general para otros atributos
            elif atributo and condicion and valor:
                # Determinar si usar LIKE o comparación exacta
                if condicion == "igual_a" and isinstance(valor, str):
                    # Para texto, usar LIKE para mayor flexibilidad
                    resultado["consulta"] = f"""
                    SELECT nombre_completo, {atributo}, funcion
                    FROM contactos
                    WHERE LOWER({atributo}) LIKE ?
                    ORDER BY funcion, nombre_completo
                    """
                    resultado["parametros"] = [f"%{valor_norm}%"]
                else:
                    # Para otros tipos, usar comparación exacta
                    resultado["consulta"] = f"""
                    SELECT nombre_completo, {atributo}, funcion
                    FROM contactos
                    WHERE {atributo} {operadores.get(condicion, '=')} ?
                    ORDER BY funcion, nombre_completo
                    """
                    resultado["parametros"] = [valor]

                resultado["descripcion"] = f"Personas con {atributo} {condicion} '{valor}'"

    # Consulta de conteo
    elif parametros.get("tipo_consulta") == "conteo":
        atributo = parametros.get("atributo", "")
        valor = parametros.get("valor", "")

        # Normalizar valor para búsqueda
        if valor:
            valor_norm = normalizar_texto(valor)

        if atributo and valor:
            # Conteo con filtro
            resultado["consulta"] = f"""
            SELECT COUNT(*) as total
            FROM contactos
            WHERE LOWER({atributo}) LIKE ?
            """
            resultado["parametros"] = [f"%{valor_norm}%"]
            resultado["descripcion"] = f"Conteo de personas con {atributo} que contiene '{valor}'"
        else:
            # Conteo total
            resultado["consulta"] = """
            SELECT COUNT(*) as total
            FROM contactos
            """
            resultado["descripcion"] = "Conteo total de personas en la agenda"

    return resultado

def consulta_a_texto(resultado_consulta: Dict[str, Any]) -> str:
    """
    Convierte el resultado de una consulta SQL a texto legible.

    Args:
        resultado_consulta: Resultado de la consulta SQL

    Returns:
        str: Texto legible con los resultados
    """
    if resultado_consulta.get("error"):
        return f"Error en la consulta: {resultado_consulta['error']}"

    if not resultado_consulta.get("registros"):
        return "No se encontraron resultados para esta consulta."

    # Convertir a DataFrame para facilitar el formateo
    df = pd.DataFrame(resultado_consulta["registros"])

    # Verificar si hay una columna de coincidencia exacta
    if "exact_match" in df.columns:
        # Filtrar solo las coincidencias exactas
        exact_matches = df[df["exact_match"] == 1]

        # Si hay coincidencias exactas, usar solo esas
        if len(exact_matches) > 0:
            df = exact_matches

        # Eliminar la columna de coincidencia exacta para que no se muestre
        df = df.drop(columns=["exact_match"])

    # Obtener descripción de la consulta si existe
    descripcion = resultado_consulta.get("descripcion", "")

    # Formatear según el tipo de resultado
    if "total" in df.columns and len(df) == 1:
        # Resultado de conteo
        total = df.iloc[0]["total"]
        if descripcion:
            texto = f"Encontré la siguiente información:\n\n"
            texto += f"Total: {total}\n"
            texto += f"Descripción: {descripcion}\n"
        else:
            texto = f"Encontré la siguiente información:\n\n"
            texto += f"Total: {total}\n"
    elif len(df) == 1:
        # Un solo registro
        registro = df.iloc[0]
        texto = "Encontré la siguiente información:\n\n"

        # Ordenar columnas para mostrar primero las más importantes
        columnas_ordenadas = []

        # Columnas prioritarias
        columnas_prioritarias = [
            "nombre_completo", "nombre_alternativo", "funcion", "centro_trabajo",
            "zona", "telefono", "celular", "correo_electronico", "direccion",
            "estudios", "estado_civil", "fecha_ingreso", "rfc", "curp"
        ]

        # Añadir primero las columnas prioritarias si existen
        for col in columnas_prioritarias:
            if col in df.columns:
                columnas_ordenadas.append(col)

        # Añadir el resto de columnas
        for col in df.columns:
            if col not in columnas_ordenadas and col != "id":
                columnas_ordenadas.append(col)

        # Mostrar valores
        for columna in columnas_ordenadas:
            if pd.notna(registro[columna]) and registro[columna] != "":
                # Formatear nombre de columna
                nombre_columna = columna.replace('_', ' ').title()

                # Formatear valor según el tipo de columna
                valor = registro[columna]

                # Formatear fechas
                if columna in ["fecha_ingreso", "fecha_nacimiento"] and isinstance(valor, str) and len(valor) > 10:
                    valor = valor[:10]  # Mostrar solo YYYY-MM-DD

                texto += f"{nombre_columna}: {valor}\n"
    else:
        # Múltiples registros
        texto = f"Encontré {len(df)} resultados"
        if descripcion:
            texto += f" ({descripcion})"
        texto += ":\n\n"

        # Determinar columnas a mostrar
        if "funcion" in df.columns and "nombre_completo" in df.columns:
            # Agrupar por función para una mejor organización
            grupos = df.groupby("funcion")

            for funcion, grupo in grupos:
                texto += f"--- {funcion} ({len(grupo)} personas) ---\n"

                for i, fila in grupo.iterrows():
                    texto += f"{i+1}. {fila['nombre_completo']}"

                    # Añadir información adicional (excepto función que ya se muestra en el encabezado)
                    columnas_adicionales = [col for col in df.columns if col not in ["nombre_completo", "funcion", "id"]]

                    # Limitar a 3 columnas adicionales para no saturar
                    columnas_adicionales = columnas_adicionales[:3]

                    for col in columnas_adicionales:
                        if col in fila and pd.notna(fila[col]) and fila[col] != "":
                            texto += f", {col.replace('_', ' ').title()}: {fila[col]}"

                    texto += "\n"

                texto += "\n"
        else:
            # Mostrar solo las columnas más relevantes
            columnas_mostrar = ["nombre_completo"]
            for col in df.columns:
                if col != "nombre_completo" and col != "id":
                    columnas_mostrar.append(col)

            # Limitar a 4 columnas para no saturar
            columnas_mostrar = columnas_mostrar[:4]

            # Crear tabla
            for i, fila in df.iterrows():
                texto += f"{i+1}. {fila['nombre_completo']}"

                # Añadir información adicional
                for col in columnas_mostrar[1:]:
                    if col in fila and pd.notna(fila[col]) and fila[col] != "":
                        texto += f", {col.replace('_', ' ').title()}: {fila[col]}"

                texto += "\n"

    return texto
