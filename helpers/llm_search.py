"""
Módulo para búsqueda avanzada utilizando LLM.
Implementa funciones para analizar consultas, generar SQL y evaluar resultados.
"""

import json
import sqlite3
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from config import (
    GOOGLE_API_KEY,
    DB_PATH,
    DB_TABLE,
    DB_PREVIEW_LIMIT,
    DB_EXAMPLE_LIMIT,
    MAX_RESULTS_DISPLAY
)
from helpers.llm_utils import llamar_llm, parsear_respuesta_json

# Configurar API
genai.configure(api_key=GOOGLE_API_KEY)

def analizar_consulta(consulta: str, contexto: Optional[Dict[str, Any]] = None, db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Analiza una consulta en lenguaje natural y genera una estrategia de búsqueda.

    Args:
        consulta (str): Consulta del usuario
        contexto (dict, optional): Contexto de la consulta anterior
        db_path (str): Ruta a la base de datos SQLite

    Returns:
        dict: Estrategia de búsqueda con información sobre nombres, atributos, etc.
    """
    # Obtener vista previa de la base de datos
    vista_previa = obtener_vista_previa_db(db_path)

    # Preparar información de contexto si existe
    contexto_texto = ""
    if contexto:
        contexto_texto = f"""
        CONTEXTO DE LA CONSULTA ANTERIOR:
        - Consulta anterior: "{contexto.get('consulta_anterior', '')}"
        - Respuesta anterior: "{contexto.get('respuesta_anterior', '')}"

        Resultados anteriores:
        {json.dumps(contexto.get('resultados_anteriores', []), indent=2, ensure_ascii=False)}

        IMPORTANTE SOBRE EL CONTEXTO:
        1. Si la consulta actual parece ser una pregunta de seguimiento (por ejemplo, usa pronombres como "su", "él", "ella" o es muy corta),
           utiliza el contexto anterior para determinar a qué persona se refiere.
        2. Si la consulta actual pide información que ya se proporcionó en respuestas anteriores, DEBES usar esa información.
        3. Mantén CONSISTENCIA con las respuestas anteriores. Si antes dijiste que una persona tiene cierta información,
           no puedes decir ahora que no la tiene.
        4. Analiza la respuesta anterior para extraer información relevante que pueda ser útil para la consulta actual.
        5. Si la consulta actual es sobre un atributo específico (como dirección, teléfono, etc.) y ese atributo
           aparece en la respuesta anterior, DEBES usar esa información.
        """

    # Preparar información de la base de datos
    db_info = f"""
    INFORMACIÓN DE LA BASE DE DATOS:
    - Total de registros: {vista_previa.get('total_registros', 'N/A')}
    - Columnas disponibles: {', '.join(vista_previa.get('columnas', []))}

    Nombres únicos en la base de datos (muestra):
    {json.dumps(vista_previa.get('nombres_unicos', []), indent=2, ensure_ascii=False)}

    Ejemplos de registros:
    {json.dumps(vista_previa.get('ejemplos', []), indent=2, ensure_ascii=False)}

    IMPORTANTE:
    1. Si el usuario menciona un nombre parcial (por ejemplo, solo "Luis") y solo hay una persona con ese nombre en la base de datos, asume que se refiere a esa persona.
    2. Si hay múltiples personas con ese nombre parcial, considera todas las posibilidades y sugiere preguntar al usuario para aclarar.
    3. Utiliza la información de la base de datos para entender mejor la estructura y el contenido de los datos.
    """

    # Extraer información de respuestas anteriores si existe
    info_respuestas_anteriores = ""
    if contexto and "historial_respuestas" in contexto and len(contexto["historial_respuestas"]) > 0:
        # Analizar las respuestas anteriores para extraer información relevante
        info_respuestas_anteriores = f"""
        INFORMACIÓN EXTRAÍDA DE RESPUESTAS ANTERIORES:

        He analizado las respuestas anteriores y he encontrado la siguiente información relevante:
        """

        # Buscar patrones comunes en las respuestas anteriores
        for i, respuesta in enumerate(contexto.get("historial_respuestas", [])):
            consulta_correspondiente = contexto.get("historial_consultas", [])[i] if i < len(contexto.get("historial_consultas", [])) else ""
            info_respuestas_anteriores += f"""
            Consulta: "{consulta_correspondiente}"
            Respuesta: "{respuesta}"
            """

    prompt = f"""
    Analiza esta consulta sobre una agenda de contactos:

    Consulta: {consulta}

    {contexto_texto}

    {info_respuestas_anteriores}

    {db_info}

    MAPEO DE CONCEPTOS A CAMPOS DE LA BASE DE DATOS:

    1. ROLES Y FUNCIONES:
       - "docentes", "maestros", "profesores" → función_específica = 'DOCENTE FRENTE A GRUPO'
       - "directores" → función_específica = 'DIRECTOR'
       - "subdirectores académicos" → función_específica = 'SUBDIRECTOR ACADÉMICO'
       - "subdirectores de gestión" → función_específica = 'SUBDIRECTOR DE GESTIÓN'
       - "subdirectores" (genérico) → función_específica IN ('SUBDIRECTOR ACADÉMICO', 'SUBDIRECTOR DE GESTIÓN')
       - "personal de aula de medios", "encargados de tecnología" → función_específica = 'TICAD'S (AULA DE MEDIOS)'
       - "veladores", "personal de vigilancia" → función_específica = 'VELADOR'
       - "ASPE", "personal de apoyo" → función_específica = 'ASPE'
       - "a qué se dedica", "función", "cargo", "puesto" → función_específica

    2. DATOS DE CONTACTO:
       - "teléfono", "número", "celular", "móvil" → teléfono_celular, teléfono_particular
       - "correo", "email", "correo electrónico" → dirección_de_correo_electrónica
       - "dirección", "domicilio", "dónde vive" → domicilio_particular

    3. DATOS LABORALES:
       - "centro de trabajo", "escuela", "dónde trabaja" → nombre_del_c_t
       - "clave del centro de trabajo" → clave_de_c_t_en_el_que_labora
       - "doble plaza" → el_trabajador_cuenta_con_doble_plaza
       - "fecha de ingreso", "antigüedad", "cuándo empezó" → fecha_ingreso_a_la_sep
       - "sector" → sector
       - "zona" → zona

    4. DATOS ACADÉMICOS:
       - "estudios", "formación", "preparación" → último_grado_de_estudios

    5. DATOS PERSONALES:
       - "estado civil", "casado", "soltero" → estado_civil
       - "CURP" → curp
       - "RFC" → filiación_o_rfc_con_homonimia

    IMPORTANTE:
    - NO confundas "docentes" con directores o subdirectores. Son roles diferentes.
    - El campo j_jefe_de_sector_s_supervisor_d_director_sd_subdirector indica el rol administrativo (D=Director, SD=Subdirector), pero NO indica si alguien es docente.
    - Cuando el usuario pregunte por "docentes" o "maestros", SIEMPRE busca en función_específica = 'DOCENTE FRENTE A GRUPO'
    - Analiza cuidadosamente la consulta del usuario y determina qué campos de la base de datos son relevantes según este mapeo.

    Proporciona un análisis detallado siguiendo estos pasos:

    1. ¿Qué está preguntando el usuario exactamente?

    2. ¿Qué nombres de personas se mencionan? Considera lo siguiente:
       - En español, los nombres completos suelen tener la estructura: [Nombre(s)] [Apellido Paterno] [Apellido Materno]
       - Sin embargo, en bases de datos pueden estar almacenados como: [Apellido Paterno] [Apellido Materno] [Nombre(s)]
       - Si solo se menciona un nombre (como "Luis"), busca en la lista de nombres únicos y considera TODAS las posibles coincidencias
       - Si el nombre aparece en cualquier parte del nombre completo (como nombre o apellido), considéralo una coincidencia
       - Si la consulta es de seguimiento y no menciona un nombre específico, usa el nombre de la consulta anterior
       - Considera posibles errores ortográficos (como "Luiz" en lugar de "Luis")

    3. ¿Qué atributos o información se está solicitando?
       - Si la consulta pide información que ya se proporcionó en respuestas anteriores, DEBES indicarlo
       - Si la consulta actual es "¿Dónde vive?" y en una respuesta anterior mencionaste la dirección, DEBES usar esa información

    4. ¿Hay alguna condición o filtro en la consulta?

    5. ¿Cómo buscarías esta información en una base de datos?
       - Si la información ya se proporcionó en respuestas anteriores, indica que no es necesario buscar en la base de datos

    IMPORTANTE PARA CONSULTAS DE LISTADO:
    - Si la consulta pide listar múltiples registros (como "dame 50 números de teléfono" o "muestra todos los docentes"),
      identifícala como tipo_consulta: "listado" y especifica el límite de registros solicitados.
    - Para consultas de listado, especifica claramente los campos a mostrar y los criterios de ordenamiento.
    - Si la consulta pide "todos" los registros de cierto tipo, establece un límite razonable (por ejemplo, 100)
      para evitar sobrecarga, pero asegúrate de que la consulta SQL pueda recuperar todos los registros si es necesario.

    Basándote en tu análisis, genera una estrategia de búsqueda en formato JSON:

    ```json
    {{
      "tipo_consulta": "informacion" | "filtrado" | "conteo",
      "nombres_posibles": ["nombre1", "nombre2", ...],
      "atributos_solicitados": ["atributo1", "atributo2", ...],
      "condiciones": [
        {{
          "campo": "campo1",
          "operador": "=",
          "valor": "valor1"
        }}
      ],
      "explicacion": "Explicación de tu estrategia de búsqueda",
      "clave_semantica": "tipo:entidad:atributo"
    }}
    ```

    Donde:
    - tipo_consulta: "informacion" (busca info de alguien), "filtrado" (busca personas que cumplen condición), "conteo" (cuenta personas)
    - nombres_posibles: Lista de posibles variaciones del nombre mencionado
    - atributos_solicitados: Lista de atributos que se están solicitando (telefono, celular, correo_electronico, direccion, etc.)
    - condiciones: Lista de condiciones para filtrar resultados
    - explicacion: Explicación de tu estrategia de búsqueda
    - clave_semantica: Una clave única que capture la esencia de la consulta, con el formato "tipo:entidad:atributo"
      * Para consultas sobre personas: "persona:nombre_normalizado:atributo" (ej: "persona:luis_perez:telefono")
      * Para listados: "listado:campo:valor" (ej: "listado:zona:109")
      * Para conteos: "conteo:campo:valor" (ej: "conteo:funcion:directores")

    Responde SOLO con el JSON, sin texto adicional.
    """

    # Usar la función común para llamar al LLM
    respuesta = llamar_llm(prompt)

    # Usar la función común para parsear la respuesta JSON
    try:
        estrategia = parsear_respuesta_json(respuesta)
        return estrategia
    except Exception as e:
        # Si hay un error en el parseo, devolver un objeto con información del error
        return {
            "tipo_consulta": "general",
            "error": str(e),
            "respuesta_original": respuesta.text
        }

def generar_sql_desde_estrategia(estrategia: Dict[str, Any], db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Genera una consulta SQL a partir de una estrategia de búsqueda.

    Args:
        estrategia (dict): Estrategia de búsqueda
        db_path (str): Ruta a la base de datos SQLite

    Returns:
        dict: Consulta SQL y parámetros
    """
    # Obtener vista previa de la base de datos
    vista_previa = obtener_vista_previa_db(db_path)

    # Preparar información de la base de datos
    db_info = f"""
    INFORMACIÓN DE LA BASE DE DATOS:
    - Total de registros: {vista_previa.get('total_registros', 'N/A')}
    - Columnas disponibles: {', '.join(vista_previa.get('columnas', []))}

    Nombres únicos en la base de datos (muestra):
    {json.dumps(vista_previa.get('nombres_unicos', []), indent=2, ensure_ascii=False)}

    IMPORTANTE:
    1. Si en la estrategia se menciona un nombre parcial y solo hay una coincidencia en la base de datos, optimiza la consulta para esa persona específica.
    2. Si hay múltiples coincidencias posibles, diseña la consulta para encontrar todas y ordenarlas por relevancia.
    3. Utiliza la información de la base de datos para entender mejor la estructura y el contenido de los datos.
    """

    prompt = f"""
    Basándote en esta estrategia de búsqueda:

    {json.dumps(estrategia, indent=2)}

    {db_info}

    Genera una consulta SQL para buscar en la tabla 'contactos' con los siguientes campos disponibles:
    {', '.join(vista_previa.get('columnas', []))}

    IMPORTANTE: Usa SOLO los campos que existen en la tabla. No inventes campos que no existen.

    MAPEO DE CONCEPTOS A CAMPOS DE LA BASE DE DATOS:

    1. ROLES Y FUNCIONES:
       - "docentes", "maestros", "profesores" → función_específica = 'DOCENTE FRENTE A GRUPO'
       - "directores" → función_específica = 'DIRECTOR'
       - "subdirectores académicos" → función_específica = 'SUBDIRECTOR ACADÉMICO'
       - "subdirectores de gestión" → función_específica = 'SUBDIRECTOR DE GESTIÓN'
       - "subdirectores" (genérico) → función_específica IN ('SUBDIRECTOR ACADÉMICO', 'SUBDIRECTOR DE GESTIÓN')
       - "personal de aula de medios", "encargados de tecnología" → función_específica = 'TICAD'S (AULA DE MEDIOS)'
       - "veladores", "personal de vigilancia" → función_específica = 'VELADOR'
       - "ASPE", "personal de apoyo" → función_específica = 'ASPE'
       - "a qué se dedica", "función", "cargo", "puesto" → función_específica

    2. DATOS DE CONTACTO:
       - "teléfono", "número", "celular", "móvil" → teléfono_celular, teléfono_particular
       - "correo", "email", "correo electrónico" → dirección_de_correo_electrónica
       - "dirección", "domicilio", "dónde vive" → domicilio_particular

    3. DATOS LABORALES:
       - "centro de trabajo", "escuela", "dónde trabaja" → nombre_del_c_t
       - "clave del centro de trabajo" → clave_de_c_t_en_el_que_labora
       - "doble plaza" → el_trabajador_cuenta_con_doble_plaza
       - "fecha de ingreso", "antigüedad", "cuándo empezó" → fecha_ingreso_a_la_sep
       - "sector" → sector
       - "zona" → zona

    4. DATOS ACADÉMICOS:
       - "estudios", "formación", "preparación" → último_grado_de_estudios

    5. DATOS PERSONALES:
       - "estado civil", "casado", "soltero" → estado_civil
       - "CURP" → curp
       - "RFC" → filiación_o_rfc_con_homonimia

    IMPORTANTE:
    - NO uses el campo j_jefe_de_sector_s_supervisor_d_director_sd_subdirector para buscar docentes
    - Usa el campo función_específica para determinar el rol específico de cada persona
    - Cuando el usuario pregunte por "docentes" o "maestros", SIEMPRE busca en función_específica = 'DOCENTE FRENTE A GRUPO'

    IMPORTANTE SOBRE LA ESTRUCTURA DE NOMBRES:
    - En español, los nombres completos suelen tener la estructura: [Nombre(s)] [Apellido Paterno] [Apellido Materno]
    - Sin embargo, en esta base de datos están almacenados como: [Apellido Paterno] [Apellido Materno] [Nombre(s)]
    - Por ejemplo, "Luis Pérez Ibáñez" está almacenado como "PEREZ IBAÑEZ LUIS"
    - Cuando el usuario busca "Luis", debe encontrar a "PEREZ IBAÑEZ LUIS" porque "Luis" es su nombre
    - Cuando el usuario busca "Pérez", debe encontrar a "PEREZ IBAÑEZ LUIS" porque "Pérez" es su apellido paterno
    - La búsqueda debe ser inteligente y considerar todas estas posibilidades

    INSTRUCCIONES PARA GENERAR CONSULTAS SQL FLEXIBLES:
    1. Para búsquedas de nombres específicos, usa combinaciones de condiciones que aseguren que se trata de la misma persona
       - MAL: WHERE nombre_s LIKE '%LUIS%' OR apellido_paterno LIKE '%PEREZ%' (demasiado amplio)
       - BIEN: WHERE (nombre_s LIKE '%LUIS%' AND apellido_paterno LIKE '%PEREZ%') OR nombre_completo LIKE '%LUIS%PEREZ%'

    2. SIEMPRE usa LIKE con comodines (%término%) en lugar de igualdad exacta (=) para todos los campos de texto
       - MAL: WHERE nombre_s = 'LUIS'
       - BIEN: WHERE nombre_s LIKE '%LUIS%'

    3. SIEMPRE busca en TODOS los campos relacionados con el tipo de información solicitada
       - Para nombres: nombre_s, apellido_paterno, apellido_materno, nombre_completo, nombre_alternativo
       - Para teléfonos: teléfono_particular Y teléfono_celular (ambos campos)
       - Para correos: dirección_de_correo_electrónico

    4. SIEMPRE usa un sistema de puntuación (CASE WHEN) para clasificar la relevancia de los resultados
       - Asigna puntuaciones más altas a coincidencias más exactas
       - Ordena los resultados por esta puntuación (ORDER BY relevancia DESC)

    5. Para consultas de información específica (como teléfonos), selecciona TODOS los campos relevantes
       - Si buscan teléfono, incluye TANTO telefono COMO celular en el SELECT

    6. Para búsquedas por nombre, considera posibles variaciones en el orden
       - Busca "LUIS PEREZ" y también "PEREZ LUIS"
       - Usa LIKE '%LUIS%PEREZ%' y también LIKE '%PEREZ%LUIS%'

    EJEMPLOS DE CONSULTAS SQL FLEXIBLES:

    1. Para buscar el teléfono de Luis Pérez:
    ```sql
    SELECT id, nombre_s, apellido_paterno, apellido_materno, nombre_completo, teléfono_particular, teléfono_celular,
    CASE
        WHEN nombre_completo LIKE '%LUIS%PEREZ%' THEN 100
        WHEN nombre_completo LIKE '%PEREZ%LUIS%' THEN 90
        WHEN nombre_s LIKE '%LUIS%' AND apellido_paterno LIKE '%PEREZ%' THEN 80
        WHEN nombre_s LIKE '%LUIS%' AND apellido_paterno LIKE '%PEREZ%' THEN 70
        ELSE 0
    END AS relevancia
    FROM contactos
    WHERE
        nombre_completo LIKE '%LUIS%PEREZ%' OR
        nombre_completo LIKE '%PEREZ%LUIS%' OR
        (nombre_s LIKE '%LUIS%' AND apellido_paterno LIKE '%PEREZ%')
    ORDER BY relevancia DESC
    LIMIT 10
    ```

    2. Para listar todos los docentes de la zona 109:
    ```sql
    SELECT id, nombre_completo, función_específica, nombre_del_c_t, zona
    FROM contactos
    WHERE
        función_específica = 'DOCENTE FRENTE A GRUPO'
        AND zona = '109'
    ORDER BY nombre_completo
    ```

    3. Para buscar directores:
    ```sql
    SELECT id, nombre_completo, función_específica, nombre_del_c_t, zona
    FROM contactos
    WHERE
        j_jefe_de_sector_s_supervisor_d_director_sd_subdirector = 'D'
    ORDER BY nombre_completo
    ```

    4. Para buscar subdirectores:
    ```sql
    SELECT id, nombre_completo, función_específica, nombre_del_c_t, zona
    FROM contactos
    WHERE
        j_jefe_de_sector_s_supervisor_d_director_sd_subdirector = 'SD'
    ORDER BY nombre_completo
    ```

    IMPORTANTE PARA CONSULTAS DE LISTADO:
    - Si la estrategia indica que es una consulta de tipo "listado", asegúrate de que la consulta SQL pueda recuperar TODOS los registros solicitados.
    - NO USES LIMIT en consultas de listado a menos que se especifique explícitamente un número máximo de resultados.
    - Para consultas que piden "todos los X", NUNCA uses LIMIT, ya que necesitamos recuperar todos los registros.
    - Ordena los resultados de manera lógica según el tipo de consulta (por nombre_completo para listas de personas, por función para listas de roles, etc.).
    - Para consultas que piden múltiples registros, asegúrate de seleccionar solo los campos necesarios para mejorar el rendimiento.
    - Si la consulta es del tipo "muestra todos los docentes de la zona 109", asegúrate de incluir las condiciones correctas (función_específica = 'DOCENTE FRENTE A GRUPO' AND zona = '109').
    - Si la consulta es del tipo "muestra todos los directores de la zona 109", usa (j_jefe_de_sector_s_supervisor_d_director_sd_subdirector = 'D' AND zona = '109').
    - Si la consulta es del tipo "muestra todos los subdirectores de la zona 109", usa (j_jefe_de_sector_s_supervisor_d_director_sd_subdirector = 'SD' AND zona = '109').

    Formato de respuesta (solo JSON, sin texto adicional):

    ```json
    {{
      "sql_query": "TU CONSULTA SQL AQUÍ",
      "parameters": ["parámetro1", "parámetro2", ...],
      "explanation": "Explicación de tu estrategia de búsqueda"
    }}
    ```
    """

    # Usar la función común para llamar al LLM
    respuesta = llamar_llm(prompt)

    # Usar la función común para parsear la respuesta JSON
    try:
        resultado = parsear_respuesta_json(respuesta)
        return {
            "consulta": resultado["sql_query"],
            "parametros": resultado["parameters"],
            "explicacion": resultado["explanation"]
        }
    except Exception as e:
        # Si hay un error en el parseo, devolver un objeto con información del error
        return {
            "error": str(e),
            "respuesta_original": respuesta.text
        }

def obtener_vista_previa_db(db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Obtiene una vista previa de la base de datos para proporcionar contexto al LLM.

    Args:
        db_path (str): Ruta a la base de datos SQLite

    Returns:
        dict: Información sobre la estructura y contenido de la base de datos
    """
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Obtener estructura de la tabla
        cursor.execute(f"PRAGMA table_info({DB_TABLE})")
        columnas = [row["name"] for row in cursor.fetchall()]

        # Obtener conteo total de registros
        cursor.execute(f"SELECT COUNT(*) as total FROM {DB_TABLE}")
        total_registros = cursor.fetchone()["total"]

        # Obtener lista de nombres únicos (para referencia rápida)
        cursor.execute(f"""
            SELECT DISTINCT nombre_completo
            FROM {DB_TABLE}
            ORDER BY nombre_completo
            LIMIT {DB_PREVIEW_LIMIT}
        """)
        nombres_unicos = [row["nombre_completo"] for row in cursor.fetchall()]

        # Obtener algunos ejemplos de registros
        cursor.execute(f"SELECT * FROM {DB_TABLE} LIMIT {DB_EXAMPLE_LIMIT}")
        ejemplos = []
        for row in cursor.fetchall():
            ejemplo = {}
            for key in row.keys():
                ejemplo[key] = row[key]
            ejemplos.append(ejemplo)

        conn.close()

        return {
            "columnas": columnas,
            "total_registros": total_registros,
            "nombres_unicos": nombres_unicos,
            "ejemplos": ejemplos,
            "error": None
        }
    except Exception as e:
        return {
            "error": str(e)
        }

def ejecutar_consulta_llm(consulta_sql: str, parametros: List[Any], db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Ejecuta una consulta SQL generada por el LLM.

    Args:
        consulta_sql (str): Consulta SQL a ejecutar
        parametros (list): Parámetros para la consulta
        db_path (str): Ruta a la base de datos SQLite

    Returns:
        dict: Resultados de la consulta
    """
    try:
        # Conectar a la base de datos
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        # Ejecutar consulta
        cursor = conn.cursor()
        cursor.execute(consulta_sql, parametros)

        # Obtener resultados
        rows = cursor.fetchall()

        # Convertir a lista de diccionarios
        registros = []
        for row in rows:
            registro = {}
            for key in row.keys():
                registro[key] = row[key]
            registros.append(registro)

        # Obtener el total real de registros que coinciden con la consulta
        # Esto es importante para consultas que usan LIMIT
        total_real = len(registros)

        # Si la consulta contiene LIMIT, intentamos obtener el total real sin el límite
        if "LIMIT" in consulta_sql.upper():
            try:
                # Crear una consulta para contar el total sin el límite
                count_sql = f"SELECT COUNT(*) as total FROM ({consulta_sql.split('LIMIT')[0].strip()}) as subquery"
                cursor.execute(count_sql, parametros)
                count_result = cursor.fetchone()
                if count_result and "total" in dict(count_result):
                    total_real = dict(count_result)["total"]
            except:
                # Si falla, usamos el total de registros obtenidos
                pass

        conn.close()

        return {
            "total": total_real,
            "registros": registros,
            "error": None
        }
    except Exception as e:
        return {
            "total": 0,
            "registros": [],
            "error": str(e)
        }

def evaluar_resultados(consulta_original: str, resultados: Dict[str, Any], estrategia: Dict[str, Any], db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Evalúa los resultados de una consulta y sugiere refinamientos si es necesario.

    Args:
        consulta_original (str): Consulta original del usuario
        resultados (dict): Resultados de la consulta SQL
        estrategia (dict): Estrategia de búsqueda utilizada
        db_path (str): Ruta a la base de datos SQLite

    Returns:
        dict: Evaluación de los resultados y posibles refinamientos
    """
    # Obtener vista previa de la base de datos
    vista_previa = obtener_vista_previa_db(db_path)

    # Preparar información de la base de datos
    db_info = f"""
    INFORMACIÓN DE LA BASE DE DATOS:
    - Total de registros: {vista_previa.get('total_registros', 'N/A')}
    - Columnas disponibles: {', '.join(vista_previa.get('columnas', []))}

    Nombres únicos en la base de datos (muestra):
    {json.dumps(vista_previa.get('nombres_unicos', []), indent=2, ensure_ascii=False)}
    """

    prompt = f"""
    Consulta original del usuario: "{consulta_original}"

    Estrategia de búsqueda utilizada:
    {json.dumps(estrategia, indent=2)}

    Resultados obtenidos ({resultados["total"]} registros en total):
    {json.dumps(resultados["registros"][:50] if len(resultados["registros"]) > 50 else resultados["registros"], indent=2)}

    {db_info}

    IMPORTANTE SOBRE LA ESTRUCTURA DE NOMBRES:
    - En español, los nombres completos suelen tener la estructura: [Nombre(s)] [Apellido Paterno] [Apellido Materno]
    - Sin embargo, en esta base de datos están almacenados como: [Apellido Paterno] [Apellido Materno] [Nombre(s)]
    - Por ejemplo, "Luis Pérez Ibáñez" está almacenado como "PEREZ IBAÑEZ LUIS"
    - Cuando el usuario busca "Luis", debe encontrar a "PEREZ IBAÑEZ LUIS" porque "Luis" es su nombre
    - Cuando el usuario busca "Pérez", debe encontrar a "PEREZ IBAÑEZ LUIS" porque "Pérez" es su apellido paterno

    MAPEO DE CONCEPTOS A CAMPOS DE LA BASE DE DATOS:

    1. ROLES Y FUNCIONES:
       - "docentes", "maestros", "profesores" → función_específica = 'DOCENTE FRENTE A GRUPO'
       - "directores" → función_específica = 'DIRECTOR'
       - "subdirectores académicos" → función_específica = 'SUBDIRECTOR ACADÉMICO'
       - "subdirectores de gestión" → función_específica = 'SUBDIRECTOR DE GESTIÓN'
       - "subdirectores" (genérico) → función_específica IN ('SUBDIRECTOR ACADÉMICO', 'SUBDIRECTOR DE GESTIÓN')
       - "personal de aula de medios", "encargados de tecnología" → función_específica = 'TICAD'S (AULA DE MEDIOS)'
       - "veladores", "personal de vigilancia" → función_específica = 'VELADOR'
       - "ASPE", "personal de apoyo" → función_específica = 'ASPE'

    IMPORTANTE SOBRE ROLES EDUCATIVOS:
    - Si la consulta era sobre "docentes" o "maestros" pero los resultados NO muestran personas con función_específica = "DOCENTE FRENTE A GRUPO", la búsqueda NO es correcta
    - Si la consulta era sobre "directores" pero los resultados NO muestran personas con función_específica = "DIRECTOR", la búsqueda NO es correcta
    - Si la consulta era sobre "subdirectores" pero los resultados NO muestran personas con función_específica = "SUBDIRECTOR ACADÉMICO" o "SUBDIRECTOR DE GESTIÓN", la búsqueda NO es correcta
    - Verifica que los campos utilizados en la búsqueda correspondan correctamente a los conceptos mencionados en la consulta

    Evalúa estos resultados:
    1. ¿Son relevantes para la consulta original?
    2. ¿Hay demasiados resultados o muy pocos?
    3. ¿Se encontró la información específica que se buscaba?
    4. ¿Los resultados son precisos y completos?
    5. ¿Se interpretó correctamente el nombre mencionado en la consulta?

    IMPORTANTE PARA RESULTADOS VACÍOS:
    Si no se encontraron resultados (total = 0), DEBES proporcionar una estrategia alternativa detallada:

    1. Para búsquedas de nombres:
       - Si el usuario buscó un nombre completo (como "Luis Pérez"), sugiere buscar solo por el nombre o solo por el apellido
       - Si el usuario buscó solo un nombre (como "Luis"), sugiere buscar variantes como "Luís", "Luiz", etc.
       - Sugiere buscar en otros campos como nombre_alternativo
       - Proporciona una nueva estrategia con condiciones de búsqueda más flexibles

    2. Para búsquedas de teléfonos/contactos:
       - Si el usuario buscó el teléfono de alguien, asegúrate de que la estrategia busque tanto en el campo "telefono" como en "celular"
       - Sugiere buscar variantes del nombre de la persona
       - Proporciona una nueva estrategia que busque en ambos campos de teléfono

    3. Para búsquedas por función o cargo:
       - Si el usuario buscó por una función específica (como "director"), sugiere buscar variantes como "directora", "dirección", etc.
       - Proporciona una nueva estrategia con términos de búsqueda más amplios

    4. Para búsquedas por zona o ubicación:
       - Si el usuario buscó por una zona específica, sugiere verificar si el formato de la zona es correcto
       - Proporciona una nueva estrategia con búsqueda más flexible para la zona

    IMPORTANTE:
    - Si no se encontraron resultados pero hay nombres similares en la base de datos, sugiere buscar esos nombres.
    - Si el usuario buscó un nombre parcial (como "Luis") y hay una única persona con ese nombre en la base de datos, sugiere buscar específicamente a esa persona.
    - Si hay múltiples personas con nombres similares, sugiere preguntar al usuario para aclarar a cuál se refiere.
    - Considera que el usuario puede referirse a una persona usando solo su nombre, solo su apellido, o cualquier combinación de estos.

    PARA CONSULTAS DE LISTADO:
    - Si la consulta pide listar múltiples registros, evalúa si se han recuperado todos los registros solicitados.
    - Si la consulta pide un número específico de registros (como "50 números de teléfono"), verifica que se hayan recuperado exactamente ese número si están disponibles.
    - Si hay demasiados resultados, sugiere formas de filtrarlos o agruparlos para hacerlos más manejables.

    PRIORIZACIÓN DE MENSAJES RECIENTES:
    - Si la consulta parece ser una aclaración o refinamiento de una consulta anterior, prioriza la precisión y completitud en la respuesta.
    - Si el usuario ha hecho varias consultas sobre el mismo tema, sugiere proporcionar una respuesta más detallada y completa.

    Si los resultados no son satisfactorios, DEBES proporcionar una nueva estrategia de búsqueda completa y detallada.

    Formato de respuesta (solo JSON, sin texto adicional):

    ```json
    {{
      "satisfactorio": true | false,
      "evaluacion": "Tu evaluación de los resultados",
      "refinamiento": {{
        "sugerencia": "Sugerencia para refinar la búsqueda",
        "nueva_estrategia": {{
          "tipo_consulta": "informacion | filtrado | conteo",
          "nombres_posibles": ["nombre1", "nombre2", ...],
          "atributos_solicitados": ["atributo1", "atributo2", ...],
          "condiciones": [
            {{
              "campo": "campo1",
              "operador": "LIKE",
              "valor": "valor1"
            }}
          ],
          "explicacion": "Explicación de la nueva estrategia de búsqueda"
        }}
      }}
    }}
    ```
    """

    # Usar la función común para llamar al LLM
    respuesta = llamar_llm(prompt)

    # Usar la función común para parsear la respuesta JSON
    try:
        evaluacion = parsear_respuesta_json(respuesta)
        return evaluacion
    except Exception as e:
        # Si hay un error en el parseo, devolver un objeto con información del error
        return {
            "satisfactorio": False,
            "error": str(e),
            "respuesta_original": respuesta.text
        }

def generar_respuesta_desde_resultados(consulta_original: str, resultados: Dict[str, Any], estrategia: Dict[str, Any], evaluacion: Dict[str, Any], db_path: str = DB_PATH) -> str:
    """
    Genera una respuesta natural basada en los resultados de la consulta.

    Args:
        consulta_original (str): Consulta original del usuario
        resultados (dict): Resultados de la consulta SQL
        estrategia (dict): Estrategia de búsqueda utilizada
        evaluacion (dict): Evaluación de los resultados
        db_path (str): Ruta a la base de datos SQLite

    Returns:
        str: Respuesta natural generada
    """
    # Obtener vista previa de la base de datos
    vista_previa = obtener_vista_previa_db(db_path)

    # Preparar información de la base de datos
    db_info = f"""
    INFORMACIÓN DE LA BASE DE DATOS:
    - Total de registros: {vista_previa.get('total_registros', 'N/A')}

    Nombres únicos en la base de datos (muestra):
    {json.dumps(vista_previa.get('nombres_unicos', []), indent=2, ensure_ascii=False)}
    """

    # Extraer información de respuestas anteriores si existe
    info_respuestas_anteriores = ""
    if "historial_respuestas" in estrategia and len(estrategia["historial_respuestas"]) > 0:
        info_respuestas_anteriores = f"""
        HISTORIAL DE CONSULTAS Y RESPUESTAS:
        """

        # Incluir historial de consultas y respuestas
        for i, respuesta in enumerate(estrategia.get("historial_respuestas", [])):
            consulta_correspondiente = estrategia.get("historial_consultas", [])[i] if i < len(estrategia.get("historial_consultas", [])) else ""
            info_respuestas_anteriores += f"""
            Consulta: "{consulta_correspondiente}"
            Respuesta: "{respuesta}"
            """

    # Filtrar resultados para mostrar solo los más relevantes
    # y limitar el número para evitar tokens excesivos
    resultados_filtrados = []

    # Si es una consulta de información sobre una persona específica
    if estrategia.get("tipo_consulta") == "informacion" and estrategia.get("nombres_posibles") and len(estrategia.get("nombres_posibles", [])) > 0:
        # Ordenar por relevancia si existe ese campo
        if resultados["registros"] and "relevancia" in resultados["registros"][0]:
            resultados_ordenados = sorted(resultados["registros"], key=lambda x: x.get("relevancia", 0), reverse=True)
        else:
            resultados_ordenados = resultados["registros"]

        # Filtrar solo los resultados con alta relevancia (si hay campo de relevancia)
        if resultados_ordenados and "relevancia" in resultados_ordenados[0]:
            max_relevancia = resultados_ordenados[0].get("relevancia", 0)
            # Solo incluir resultados con al menos 80% de la relevancia máxima
            resultados_filtrados = [r for r in resultados_ordenados if r.get("relevancia", 0) >= max_relevancia * 0.8]
        else:
            resultados_filtrados = resultados_ordenados
    else:
        # Para otros tipos de consultas, usar todos los resultados
        resultados_filtrados = resultados["registros"]

    # Limitar el número de resultados para evitar tokens excesivos
    resultados_limitados = resultados_filtrados[:MAX_RESULTS_DISPLAY] if len(resultados_filtrados) > MAX_RESULTS_DISPLAY else resultados_filtrados

    prompt = f"""
    Eres un asistente de agenda personal que mantiene una conversación continua con el usuario.

    CONSULTA ORIGINAL DEL USUARIO:
    {consulta_original}

    ESTRATEGIA DE BÚSQUEDA UTILIZADA:
    {json.dumps(estrategia, indent=2)}

    RESULTADOS OBTENIDOS ({resultados["total"]} registros en total, mostrando {len(resultados_limitados)}):
    {json.dumps(resultados_limitados, indent=2)}

    EVALUACIÓN DE LOS RESULTADOS:
    {json.dumps(evaluacion, indent=2)}

    {info_respuestas_anteriores}

    {db_info}

    IMPORTANTE SOBRE LA ESTRUCTURA DE NOMBRES:
    - En español, los nombres completos suelen tener la estructura: [Nombre(s)] [Apellido Paterno] [Apellido Materno]
    - Sin embargo, en esta base de datos están almacenados como: [Apellido Paterno] [Apellido Materno] [Nombre(s)]
    - Por ejemplo, "Luis Pérez Ibáñez" está almacenado como "PEREZ IBAÑEZ LUIS"
    - Cuando el usuario busca "Luis", debe encontrar a "PEREZ IBAÑEZ LUIS" porque "Luis" es su nombre
    - Cuando el usuario busca "Pérez", debe encontrar a "PEREZ IBAÑEZ LUIS" porque "Pérez" es su apellido paterno
    - Al responder, usa el formato natural de nombres ([Nombre(s)] [Apellido Paterno] [Apellido Materno])

    MAPEO DE CONCEPTOS A CAMPOS DE LA BASE DE DATOS:

    1. ROLES Y FUNCIONES:
       - "docentes", "maestros", "profesores" → función_específica = 'DOCENTE FRENTE A GRUPO'
       - "directores" → función_específica = 'DIRECTOR'
       - "subdirectores académicos" → función_específica = 'SUBDIRECTOR ACADÉMICO'
       - "subdirectores de gestión" → función_específica = 'SUBDIRECTOR DE GESTIÓN'
       - "subdirectores" (genérico) → función_específica IN ('SUBDIRECTOR ACADÉMICO', 'SUBDIRECTOR DE GESTIÓN')
       - "personal de aula de medios", "encargados de tecnología" → función_específica = 'TICAD'S (AULA DE MEDIOS)'
       - "veladores", "personal de vigilancia" → función_específica = 'VELADOR'
       - "ASPE", "personal de apoyo" → función_específica = 'ASPE'
       - "a qué se dedica", "función", "cargo", "puesto" → función_específica

    2. DATOS DE CONTACTO:
       - "teléfono", "número", "celular", "móvil" → teléfono_celular, teléfono_particular
       - "correo", "email", "correo electrónico" → dirección_de_correo_electrónica
       - "dirección", "domicilio", "dónde vive" → domicilio_particular

    3. DATOS LABORALES:
       - "centro de trabajo", "escuela", "dónde trabaja" → nombre_del_c_t
       - "clave del centro de trabajo" → clave_de_c_t_en_el_que_labora
       - "doble plaza" → el_trabajador_cuenta_con_doble_plaza
       - "fecha de ingreso", "antigüedad", "cuándo empezó" → fecha_ingreso_a_la_sep
       - "sector" → sector
       - "zona" → zona

    4. DATOS ACADÉMICOS:
       - "estudios", "formación", "preparación" → último_grado_de_estudios

    5. DATOS PERSONALES:
       - "estado civil", "casado", "soltero" → estado_civil
       - "CURP" → curp
       - "RFC" → filiación_o_rfc_con_homonimia

    IMPORTANTE SOBRE ROLES EDUCATIVOS:
    - Si la consulta era sobre "docentes" o "maestros", asegúrate de mostrar SOLO personas con función_específica = "DOCENTE FRENTE A GRUPO"
    - Si la consulta era sobre "directores", asegúrate de mostrar SOLO personas con función_específica = "DIRECTOR"
    - Si la consulta era sobre "subdirectores", asegúrate de mostrar SOLO personas con función_específica = "SUBDIRECTOR ACADÉMICO" o "SUBDIRECTOR DE GESTIÓN"

    INSTRUCCIONES:

    1. Responde basándote en los RESULTADOS OBTENIDOS Y EN EL CONTEXTO ANTERIOR si es relevante.
    2. Habla de forma natural y conversacional, como lo haría una persona real.
    3. Mantén un tono amable, servicial y ligeramente informal.
    4. Si no hay resultados relevantes en la consulta actual PERO la información aparece en respuestas anteriores, USA ESA INFORMACIÓN.
    5. Si hay múltiples resultados, SOLO MUESTRA LOS MÁS RELEVANTES para la consulta.
       - Si el usuario pregunta por una persona específica (ej: "teléfono de Luis Pérez"), SOLO muestra información de esa persona exacta.
       - NUNCA incluyas información de otras personas que solo coincidan parcialmente con el nombre (ej: si buscan "Luis Pérez", no incluyas a "Claudia Pérez").
       - Solo menciona otras personas si hay ambigüedad real (ej: hay dos "Luis Pérez" diferentes) o si el usuario explícitamente pide listar varias personas.
    6. NO uses fórmulas repetitivas como "Según los datos..." o "La información indica...".
    7. NO preguntes "¿Necesitas algo más?" o "¿Te puedo ayudar con algo más?".
    8. Si la evaluación indica que los resultados no son satisfactorios, busca en el contexto anterior si ya proporcionaste esa información.
    9. MANTÉN CONSISTENCIA con tus respuestas anteriores. Si antes dijiste que una persona tiene cierta información, no puedes decir ahora que no la tienes.

    IMPORTANTE PARA NOMBRES:
    - Si el usuario busca un nombre parcial (como "Luis") y encuentras a "PEREZ IBAÑEZ LUIS", responde refiriéndote a él como "Luis Pérez Ibáñez", NO como "Pérez Ibáñez Luis".
    - Entiende que "Luis", "Pérez", "Ibáñez", "Luis Pérez", "Pérez Ibáñez" y "Luis Pérez Ibáñez" se refieren a la misma persona.
    - Cuando muestres nombres, siempre usa el formato natural ([Nombre(s)] [Apellido Paterno] [Apellido Materno]).
    - Si hay un campo nombre_alternativo, úsalo para verificar diferentes formas del nombre.
    - Si no se encontraron resultados pero hay nombres similares en la base de datos, sugiere buscar esos nombres.
    - Si hay múltiples personas con nombres similares, pregunta al usuario a cuál se refiere, proporcionando las opciones disponibles.

    INSTRUCCIONES PARA CONSULTAS DE LISTADO:
    - Si la consulta pide listar múltiples registros (como "dame todos los números de teléfono" o "muestra todos los docentes"),
      proporciona ABSOLUTAMENTE TODOS los resultados solicitados de manera clara y estructurada.
    - NUNCA omitas resultados ni digas "entre otros" o "por ejemplo". Muestra TODOS los resultados.
    - Para listas largas, usa SIEMPRE este formato consistente:

      1. Nombre: Juan Pérez - Teléfono: 123456789
      2. Nombre: María López - Teléfono: 987654321

    - Sé EXTREMADAMENTE PRECISO con los datos numéricos. Si hay 20 docentes en la zona 109, muestra los 20.
    - Si la consulta pide "todos" los registros de cierto tipo, proporciona el número total y luego lista TODOS los registros.
    - Prioriza la precisión y completitud sobre la conversacionalidad para consultas de listado masivo.
    - EVITA DUPLICAR TEXTO en tus respuestas. Revisa tu respuesta antes de enviarla para asegurarte de que no hay texto duplicado.
    - Usa un formato CONSISTENTE para todas las entradas de la lista. No cambies el formato a mitad de la lista.

    GENERA UNA RESPUESTA NATURAL Y HUMANA:
    """

    # Configurar safety settings
    safety_settings = [
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_ONLY_HIGH"
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_ONLY_HIGH"
        }
    ]

    # Usar la función común para llamar al LLM con límite de tokens y configuración de seguridad
    respuesta = llamar_llm(prompt, max_output_tokens=2048, safety_settings=safety_settings)

    # Limpiar la respuesta para evitar duplicaciones
    texto_respuesta = respuesta.text.strip()

    # Verificar si hay duplicaciones de párrafos y eliminarlas
    lineas = texto_respuesta.split('\n')
    lineas_unicas = []
    for linea in lineas:
        if linea not in lineas_unicas:
            lineas_unicas.append(linea)

    texto_limpio = '\n'.join(lineas_unicas)

    return texto_limpio

def procesar_consulta_completa(consulta: str, contexto: Optional[Dict[str, Any]] = None, db_path: str = DB_PATH, debug: bool = False, max_refinamientos: int = 1) -> Dict[str, Any]:
    """
    Procesa una consulta completa utilizando el flujo de 5 pasos con refinamiento automático.

    Esta función centraliza todo el proceso de consulta, desde el análisis inicial
    hasta la generación de la respuesta final, siguiendo el flujo de 5 pasos:
    1. Analizar consulta
    2. Generar SQL
    3. Ejecutar SQL
    4. Evaluar resultados
    5. Generar respuesta

    Si no se encuentran resultados, la función intentará automáticamente refinar la búsqueda
    utilizando estrategias alternativas sugeridas por la evaluación.

    Args:
        consulta (str): Consulta del usuario en lenguaje natural
        contexto (dict, optional): Contexto de la conversación anterior
        db_path (str): Ruta a la base de datos SQLite
        debug (bool): Activar modo de depuración para mostrar información detallada
        max_refinamientos (int): Número máximo de refinamientos automáticos a intentar

    Returns:
        dict: Resultado completo del procesamiento con todos los pasos intermedios
    """
    # Usar la implementación modular en consulta_processor.py
    from helpers.consulta_processor import procesar_consulta

    # Llamar a la función de procesamiento (sin caché tradicional)
    return procesar_consulta(consulta, contexto, db_path, debug, max_refinamientos)

