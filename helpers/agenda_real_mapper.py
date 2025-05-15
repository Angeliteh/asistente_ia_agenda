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

            # Crear registro adaptado
            registro = {
                "nombre": nombre_completo,
                "nombre_alternativo": nombre_alternativo,
                "telefono": str(row["TELÉFONO PARTICULAR"]) if pd.notna(row["TELÉFONO PARTICULAR"]) else "",
                "celular": str(row["TELÉFONO CELULAR\n"]) if pd.notna(row["TELÉFONO CELULAR\n"]) else "",
                "direccion": str(row["DOMICILIO PARTICULAR"]) if pd.notna(row["DOMICILIO PARTICULAR"]) else "",
                "correo_electronico": str(row["DIRECCIÓN DE CORREO ELECTRÓNICO"]) if pd.notna(row["DIRECCIÓN DE CORREO ELECTRÓNICO"]) else "",
                "estado_civil": str(row["ESTADO CIVIL"]) if pd.notna(row["ESTADO CIVIL"]) else "",
                "rfc": str(row["FILIACIÓN O RFC CON HOMONIMIA"]) if pd.notna(row["FILIACIÓN O RFC CON HOMONIMIA"]) else "",
                "curp": str(row["CURP"]) if pd.notna(row["CURP"]) else "",
                "centro_trabajo": str(row["NOMBRE DEL C.T."]) if pd.notna(row["NOMBRE DEL C.T."]) else "",
                "funcion": str(row["FUNCIÓN ESPECÍFICA"]) if pd.notna(row["FUNCIÓN ESPECÍFICA"]) else "",
                "sector": str(row["SECTOR"]) if pd.notna(row["SECTOR"]) else "",
                "zona": str(row["ZONA"]) if pd.notna(row["ZONA"]) else "",
                "modalidad": str(row["MODALIDAD DEL CENTRO DE TRABAJO"]) if pd.notna(row["MODALIDAD DEL CENTRO DE TRABAJO"]) else "",
                "estudios": str(row["ÚLTIMO GRADO DE ESTUDIOS"]) if pd.notna(row["ÚLTIMO GRADO DE ESTUDIOS"]) else "",
                "fecha_ingreso": str(row["FECHA INGRESO A LA SEP"]) if pd.notna(row["FECHA INGRESO A LA SEP"]) else ""
            }

            registros.append(registro)

        # Crear esquema simplificado
        esquema = {
            "nombre": {"tipo_datos": "texto", "categoria": "nombre"},
            "nombre_alternativo": {"tipo_datos": "texto", "categoria": "nombre"},
            "telefono": {"tipo_datos": "texto", "categoria": "telefono"},
            "celular": {"tipo_datos": "texto", "categoria": "telefono"},
            "direccion": {"tipo_datos": "texto", "categoria": "direccion"},
            "correo_electronico": {"tipo_datos": "texto", "categoria": "correo"},
            "estado_civil": {"tipo_datos": "categoria", "categoria": "desconocido"},
            "rfc": {"tipo_datos": "texto", "categoria": "identificador"},
            "curp": {"tipo_datos": "texto", "categoria": "identificador"},
            "centro_trabajo": {"tipo_datos": "texto", "categoria": "desconocido"},
            "funcion": {"tipo_datos": "texto", "categoria": "desconocido"},
            "sector": {"tipo_datos": "texto", "categoria": "desconocido"},
            "zona": {"tipo_datos": "texto", "categoria": "desconocido"},
            "modalidad": {"tipo_datos": "texto", "categoria": "desconocido"},
            "estudios": {"tipo_datos": "texto", "categoria": "desconocido"},
            "fecha_ingreso": {"tipo_datos": "fecha", "categoria": "desconocido"}
        }

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
