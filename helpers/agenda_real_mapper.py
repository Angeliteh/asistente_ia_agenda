"""
Módulo para mapear y adaptar la estructura de la agenda real al formato esperado por el sistema.
"""

import pandas as pd
import os

def cargar_agenda_real(ruta_excel):
    """
    Carga datos desde la agenda real y los adapta al formato esperado por el sistema.

    Args:
        ruta_excel (str): Ruta al archivo Excel de la agenda real

    Returns:
        dict: Diccionario con los siguientes elementos:
            - registros: Lista de diccionarios con los datos adaptados
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

        # Mapeo de columnas de la agenda real a las columnas esperadas por el sistema
        mapeo_columnas = {
            # Nombre completo (combinación de apellidos y nombre)
            "nombre": ["APELLIDO PATERNO", "APELLIDO MATERNO", "NOMBRE(S)"],

            # Teléfonos
            "telefono": "TELÉFONO PARTICULAR",
            "celular": "TELÉFONO CELULAR\n",

            # Dirección
            "direccion": "DOMICILIO PARTICULAR",

            # Correo electrónico
            "correo_electronico": "DIRECCIÓN DE CORREO ELECTRÓNICO",

            # Otros datos personales
            "estado_civil": "ESTADO CIVIL",
            "rfc": "FILIACIÓN O RFC CON HOMONIMIA",
            "curp": "CURP",

            # Datos laborales
            "centro_trabajo": "NOMBRE DEL C.T.",
            "funcion": "FUNCIÓN ESPECÍFICA",
            "sector": "SECTOR",
            "zona": "ZONA",
            "modalidad": "MODALIDAD DEL CENTRO DE TRABAJO",
            "estudios": "ÚLTIMO GRADO DE ESTUDIOS",
            "fecha_ingreso": "FECHA INGRESO A LA SEP"
        }

        # Obtener todos los encabezados del Excel
        todos_encabezados = df.columns.tolist()

        # Crear registros adaptados
        registros = []
        for _, row in df.iterrows():
            # Construir nombre completo (formato: APELLIDO PATERNO APELLIDO MATERNO NOMBRE)
            nombre_completo = " ".join([
                str(row["APELLIDO PATERNO"]) if pd.notna(row["APELLIDO PATERNO"]) else "",
                str(row["APELLIDO MATERNO"]) if pd.notna(row["APELLIDO MATERNO"]) else "",
                str(row["NOMBRE(S)"]) if pd.notna(row["NOMBRE(S)"]) else ""
            ]).strip()

            # Construir nombre alternativo (formato: NOMBRE APELLIDO PATERNO APELLIDO MATERNO)
            # Esto ayudará en la búsqueda cuando el usuario busque por "José Angel" en lugar de "ALVARADO SOSA JOSE ANGEL"
            nombre_alternativo = " ".join([
                str(row["NOMBRE(S)"]) if pd.notna(row["NOMBRE(S)"]) else "",
                str(row["APELLIDO PATERNO"]) if pd.notna(row["APELLIDO PATERNO"]) else "",
                str(row["APELLIDO MATERNO"]) if pd.notna(row["APELLIDO MATERNO"]) else ""
            ]).strip()

            # Crear registro con todos los campos originales del Excel
            registro = {
                # Campos básicos para compatibilidad
                "nombre_completo": nombre_completo,
                "nombre_alternativo": nombre_alternativo
            }

            # Añadir todos los campos originales del Excel
            for encabezado in todos_encabezados:
                # Normalizar el nombre del campo para la base de datos (sin espacios ni caracteres especiales, todo minúsculas)
                campo_db = encabezado.lower()
                # Reemplazar caracteres especiales
                for char in [" ", ".", "(", ")", "\n", "=", "-", "/", "\\", ":", ";", ",", "'", '"', "?", "¿", "!", "¡", "%", "&", "$", "#", "@", "+", "*"]:
                    campo_db = campo_db.replace(char, "_")
                # Eliminar guiones bajos múltiples
                while "__" in campo_db:
                    campo_db = campo_db.replace("__", "_")
                # Eliminar guiones bajos al inicio y final
                campo_db = campo_db.strip("_")

                # Añadir el valor al registro
                if pd.notna(row[encabezado]):
                    registro[campo_db] = str(row[encabezado])
                else:
                    registro[campo_db] = ""

            registros.append(registro)

        # Crear esquema dinámico basado en los encabezados del Excel
        esquema = {
            "nombre_completo": {"tipo_datos": "texto", "categoria": "nombre"},
            "nombre_alternativo": {"tipo_datos": "texto", "categoria": "nombre"}
        }

        # Añadir todos los campos originales al esquema
        for encabezado in todos_encabezados:
            # Normalizar el nombre del campo para la base de datos (sin espacios ni caracteres especiales, todo minúsculas)
            campo_db = encabezado.lower()
            # Reemplazar caracteres especiales
            for char in [" ", ".", "(", ")", "\n", "=", "-", "/", "\\", ":", ";", ",", "'", '"', "?", "¿", "!", "¡", "%", "&", "$", "#", "@", "+", "*"]:
                campo_db = campo_db.replace(char, "_")
            # Eliminar guiones bajos múltiples
            while "__" in campo_db:
                campo_db = campo_db.replace("__", "_")
            # Eliminar guiones bajos al inicio y final
            campo_db = campo_db.strip("_")

            # Determinar el tipo de datos y categoría
            tipo_datos = "texto"
            categoria = "desconocido"

            # Categorizar algunos campos conocidos
            if "teléfono" in encabezado.lower() or "telefono" in encabezado.lower() or "celular" in encabezado.lower():
                categoria = "telefono"
            elif "dirección" in encabezado.lower() or "direccion" in encabezado.lower() or "domicilio" in encabezado.lower():
                categoria = "direccion"
            elif "correo" in encabezado.lower() or "email" in encabezado.lower():
                categoria = "correo"
            elif "nombre" in encabezado.lower() or "apellido" in encabezado.lower():
                categoria = "nombre"
            elif "rfc" in encabezado.lower() or "curp" in encabezado.lower() or "filiación" in encabezado.lower():
                categoria = "identificador"
            elif "fecha" in encabezado.lower():
                tipo_datos = "fecha"
            elif "doble plaza" in encabezado.lower():
                categoria = "doble_plaza"
            elif "clave" in encabezado.lower() and "c.t." in encabezado.lower():
                categoria = "clave_ct"

            # Añadir al esquema
            esquema[campo_db] = {"tipo_datos": tipo_datos, "categoria": categoria}

        # Añadir información sobre todos los encabezados originales
        esquema["encabezados_originales"] = todos_encabezados

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
