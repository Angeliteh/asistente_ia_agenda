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

        # Obtener todos los campos únicos de los registros
        campos_unicos = set()
        for registro in registros:
            campos_unicos.update(registro.keys())

        # Asegurarse de que los campos básicos estén presentes
        campos_basicos = ["id", "nombre_completo", "nombre_alternativo"]
        for campo in campos_basicos:
            if campo not in campos_unicos:
                campos_unicos.add(campo)

        # Crear la definición de la tabla dinámicamente
        campos_sql = ["id INTEGER PRIMARY KEY"]
        for campo in campos_unicos:
            if campo != "id":  # id ya está definido
                # Normalizar el nombre del campo para asegurar que sea válido en SQLite
                campo_normalizado = campo

                # Verificar si el campo contiene caracteres especiales
                if any(char in campo for char in ["=", "-", "/", "\\", ":", ";", ",", "'", '"', "?", "¿", "!", "¡", "%", "&", "$", "#", "@", "+", "*", " ", ".", "(", ")"]):
                    # Normalizar el campo
                    campo_normalizado = campo.lower()
                    # Reemplazar caracteres especiales
                    for char in [" ", ".", "(", ")", "\n", "=", "-", "/", "\\", ":", ";", ",", "'", '"', "?", "¿", "!", "¡", "%", "&", "$", "#", "@", "+", "*"]:
                        campo_normalizado = campo_normalizado.replace(char, "_")
                    # Eliminar guiones bajos múltiples
                    while "__" in campo_normalizado:
                        campo_normalizado = campo_normalizado.replace("__", "_")
                    # Eliminar guiones bajos al inicio y final
                    campo_normalizado = campo_normalizado.strip("_")

                # Determinar el tipo de datos
                tipo = "TEXT"  # Por defecto, todo es texto
                if campo in ["edad", "antiguedad"]:
                    tipo = "INTEGER"

                # Asegurarse de que el campo no esté vacío
                if not campo_normalizado:
                    campo_normalizado = f"campo_{len(campos_sql)}"

                # Añadir comillas para evitar problemas con palabras reservadas
                campos_sql.append(f'"{campo_normalizado}" {tipo}')

        # Crear la tabla
        cursor.execute(f'''
        CREATE TABLE contactos (
            {", ".join(campos_sql)}
        )
        ''')

        # Insertar registros
        for i, registro in enumerate(registros):
            # Añadir ID al registro
            campos = {"id": i + 1}

            # Copiar todos los campos del registro
            for campo, valor in registro.items():
                # Normalizar el nombre del campo para asegurar que sea válido en SQLite
                campo_normalizado = campo

                # Verificar si el campo contiene caracteres especiales
                if any(char in campo for char in ["=", "-", "/", "\\", ":", ";", ",", "'", '"', "?", "¿", "!", "¡", "%", "&", "$", "#", "@", "+", "*", " ", ".", "(", ")"]):
                    # Normalizar el campo
                    campo_normalizado = campo.lower()
                    # Reemplazar caracteres especiales
                    for char in [" ", ".", "(", ")", "\n", "=", "-", "/", "\\", ":", ";", ",", "'", '"', "?", "¿", "!", "¡", "%", "&", "$", "#", "@", "+", "*"]:
                        campo_normalizado = campo_normalizado.replace(char, "_")
                    # Eliminar guiones bajos múltiples
                    while "__" in campo_normalizado:
                        campo_normalizado = campo_normalizado.replace("__", "_")
                    # Eliminar guiones bajos al inicio y final
                    campo_normalizado = campo_normalizado.strip("_")

                # Asegurarse de que el campo no esté vacío
                if not campo_normalizado:
                    campo_normalizado = f"campo_{len(campos)}"

                campos[campo_normalizado] = valor

            # Preparar la consulta SQL
            campos_str = ", ".join([f'"{campo}"' for campo in campos.keys()])
            placeholders = ", ".join(["?" for _ in campos])

            # Ejecutar la consulta
            cursor.execute(
                f"INSERT INTO contactos ({campos_str}) VALUES ({placeholders})",
                list(campos.values())
            )

        # Crear índices para búsquedas rápidas
        # Verificar si las columnas existen antes de crear índices
        cursor.execute("PRAGMA table_info(contactos)")
        columnas_existentes = [info[1] for info in cursor.fetchall()]

        # Crear índice para nombre_completo si existe
        if "nombre_completo" in columnas_existentes:
            cursor.execute('CREATE INDEX idx_nombre ON contactos ("nombre_completo")')

        # Buscar columnas relacionadas con zona
        columnas_zona = [col for col in columnas_existentes if "zona" in col.lower()]
        if columnas_zona:
            cursor.execute(f'CREATE INDEX idx_zona ON contactos ("{columnas_zona[0]}")')

        # Buscar columnas relacionadas con función
        columnas_funcion = [col for col in columnas_existentes if "funcion" in col.lower() or "función" in col.lower()]
        if columnas_funcion:
            cursor.execute(f'CREATE INDEX idx_funcion ON contactos ("{columnas_funcion[0]}")')

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
    "telefono_particular": ["telefono", "teléfono", "telefono particular", "teléfono particular", "numero", "número", "contacto"],
    "telefono_celular": ["celular", "móvil", "movil", "celular", "teléfono celular", "telefono celular", "móvil", "movil"],
    "domicilio_particular": ["direccion", "dirección", "domicilio", "casa", "ubicación", "ubicacion", "vive", "domicilio"],
    "direccion_de_correo_electronico": ["correo_electronico", "correo", "email", "mail", "correo electrónico", "e-mail"],
    "funcion_especifica": ["funcion", "función", "trabajo", "empleo", "puesto", "cargo", "director", "docente", "subdirector"],
    "ultimo_grado_de_estudios": ["estudios", "grado", "educación", "educacion", "formación", "formacion", "licenciatura", "maestría", "doctorado"],
    "estado_civil": ["estado_civil", "casado", "soltero", "divorciado", "viudo", "civil"],
    "zona": ["zona", "área", "area", "sector", "región", "region"],
    "nombre_del_ct": ["centro_trabajo", "escuela", "centro", "trabajo", "institución", "institucion", "nombre del ct", "nombre del centro de trabajo"],
    "fecha_ingreso_a_la_sep": ["fecha_ingreso", "ingreso", "antigüedad", "antiguedad", "cuando ingresó", "cuando ingreso"],
    "el_trabajador_cuenta_con_doble_plaza": ["doble plaza", "plaza doble", "dos plazas", "tiene doble plaza", "cuenta con doble plaza"],
    "clave_de_ct_en_el_que_labora": ["clave ct labora", "clave del ct donde labora", "clave centro trabajo labora", "clave donde labora", "ct donde labora"],
    "clave_del_ct_en_el_que_cobra_recibo_de_pago": ["clave ct cobra", "clave del ct donde cobra", "clave centro trabajo cobra", "clave donde cobra", "ct donde cobra"],
    "clave_presupuestal_completa_igual_al_talon_de_pago_partiendo_del_07": ["clave presupuestal", "clave de presupuesto", "presupuestal"],
    "tel_del_ct": ["teléfono ct", "telefono ct", "teléfono del centro", "telefono del centro", "tel ct", "tel del ct"],
    "observacion": ["observaciones", "observación", "observacion", "notas", "comentarios", "información adicional", "informacion adicional"]
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

    # Verificar si hay una coincidencia directa en el mapeo
    for columna, sinonimos in MAPEO_ATRIBUTOS.items():
        if atributo_norm in sinonimos or any(s in atributo_norm for s in sinonimos):
            return columna

    # Si no hay coincidencia directa, normalizar el atributo como se hace con los campos
    campo_normalizado = atributo.lower()
    # Reemplazar caracteres especiales
    for char in [" ", ".", "(", ")", "\n", "=", "-", "/", "\\", ":", ";", ",", "'", '"', "?", "¿", "!", "¡", "%", "&", "$", "#", "@", "+", "*"]:
        campo_normalizado = campo_normalizado.replace(char, "_")
    # Eliminar guiones bajos múltiples
    while "__" in campo_normalizado:
        campo_normalizado = campo_normalizado.replace("__", "_")
    # Eliminar guiones bajos al inicio y final
    campo_normalizado = campo_normalizado.strip("_")

    # Verificar si existe una columna con este nombre normalizado
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(contactos)")
        columnas_existentes = [info[1] for info in cursor.fetchall()]
        conn.close()

        # Buscar coincidencias exactas o parciales
        for col in columnas_existentes:
            if col.lower() == campo_normalizado:
                return col

        # Buscar coincidencias parciales si no hay exactas
        for col in columnas_existentes:
            if campo_normalizado in col.lower() or col.lower() in campo_normalizado:
                return col
    except:
        pass  # Si hay algún error, simplemente continuar

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

    # Obtener las columnas existentes en la tabla
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(contactos)")
        columnas_existentes = [info[1] for info in cursor.fetchall()]
        conn.close()
    except:
        # Si hay algún error, usar una lista vacía
        columnas_existentes = []

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

                    # Verificar si las columnas existen antes de añadirlas a las condiciones
                    if "nombre_s" in columnas_existentes:
                        condiciones.append("LOWER(nombre_s) LIKE ?")
                        params.append(f"%{token}%")

                    if "apellido_paterno" in columnas_existentes:
                        condiciones.append("LOWER(apellido_paterno) LIKE ?")
                        params.append(f"%{token}%")

                    if "apellido_materno" in columnas_existentes:
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
