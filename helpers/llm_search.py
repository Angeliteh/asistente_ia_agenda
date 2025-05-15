"""
Módulo para búsqueda avanzada utilizando LLM.
Implementa funciones para analizar consultas, generar SQL y evaluar resultados.
"""

import json
import os
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
from helpers.cache_manager import SmartLLMCache

# Crear una instancia global del caché
llm_cache = SmartLLMCache(max_size=200)

# Intentar cargar el caché desde disco al iniciar
llm_cache.load_from_disk()

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
      "explicacion": "Explicación de tu estrategia de búsqueda"
    }}
    ```

    Donde:
    - tipo_consulta: "informacion" (busca info de alguien), "filtrado" (busca personas que cumplen condición), "conteo" (cuenta personas)
    - nombres_posibles: Lista de posibles variaciones del nombre mencionado
    - atributos_solicitados: Lista de atributos que se están solicitando (telefono, celular, correo_electronico, direccion, etc.)
    - condiciones: Lista de condiciones para filtrar resultados
    - explicacion: Explicación de tu estrategia de búsqueda

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

    Genera una consulta SQL para buscar en la tabla 'contactos' con los siguientes campos:
    - id, nombre, apellido_paterno, apellido_materno, nombre_completo, nombre_alternativo, telefono, celular, correo_electronico, direccion, funcion, centro_trabajo, zona, sector, estudios, estado_civil, fecha_ingreso, rfc, curp

    IMPORTANTE SOBRE LA ESTRUCTURA DE NOMBRES:
    - En español, los nombres completos suelen tener la estructura: [Nombre(s)] [Apellido Paterno] [Apellido Materno]
    - Sin embargo, en esta base de datos están almacenados como: [Apellido Paterno] [Apellido Materno] [Nombre(s)]
    - Por ejemplo, "Luis Pérez Ibáñez" está almacenado como "PEREZ IBAÑEZ LUIS"
    - Cuando el usuario busca "Luis", debe encontrar a "PEREZ IBAÑEZ LUIS" porque "Luis" es su nombre
    - Cuando el usuario busca "Pérez", debe encontrar a "PEREZ IBAÑEZ LUIS" porque "Pérez" es su apellido paterno
    - La búsqueda debe ser inteligente y considerar todas estas posibilidades

    Tu consulta SQL debe:
    1. Manejar posibles variaciones o errores en los nombres
    2. Priorizar coincidencias exactas pero también considerar coincidencias parciales
    3. Incluir solo los campos relevantes para la consulta
    4. Ordenar los resultados por relevancia
    5. Usar un sistema de puntuación (CASE WHEN) para clasificar la relevancia de los resultados
    6. Si solo hay una persona que coincide con el nombre parcial en la base de datos, optimiza la consulta para encontrar específicamente a esa persona
    7. Buscar en todos los campos relacionados con nombres (nombre, apellido_paterno, apellido_materno, nombre_completo, nombre_alternativo)

    IMPORTANTE PARA CONSULTAS DE LISTADO:
    - Si la estrategia indica que es una consulta de tipo "listado", asegúrate de que la consulta SQL pueda recuperar TODOS los registros solicitados.
    - NO USES LIMIT en consultas de listado a menos que se especifique explícitamente un número máximo de resultados.
    - Para consultas que piden "todos los X", NUNCA uses LIMIT, ya que necesitamos recuperar todos los registros.
    - Ordena los resultados de manera lógica según el tipo de consulta (por nombre_completo para listas de personas, por función para listas de roles, etc.).
    - Para consultas que piden múltiples registros, asegúrate de seleccionar solo los campos necesarios para mejorar el rendimiento.
    - Si la consulta es del tipo "muestra todos los docentes de la zona 109", asegúrate de incluir las condiciones correctas (función = 'DOCENTE' AND zona = '109').

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

    Evalúa estos resultados:
    1. ¿Son relevantes para la consulta original?
    2. ¿Hay demasiados resultados o muy pocos?
    3. ¿Se encontró la información específica que se buscaba?
    4. ¿Los resultados son precisos y completos?
    5. ¿Se interpretó correctamente el nombre mencionado en la consulta?

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

    Si los resultados no son satisfactorios, sugiere cómo refinar la búsqueda.

    Formato de respuesta (solo JSON, sin texto adicional):

    ```json
    {{
      "satisfactorio": true | false,
      "evaluacion": "Tu evaluación de los resultados",
      "refinamiento": {{
        "sugerencia": "Sugerencia para refinar la búsqueda",
        "nueva_estrategia": {{
          // Nueva estrategia de búsqueda si es necesario
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

    # Limitar el número de resultados para evitar tokens excesivos
    # pero asegurarnos de que el modelo sepa cuántos hay en total
    resultados_limitados = resultados["registros"][:MAX_RESULTS_DISPLAY] if len(resultados["registros"]) > MAX_RESULTS_DISPLAY else resultados["registros"]

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

    INSTRUCCIONES:

    1. Responde basándote en los RESULTADOS OBTENIDOS Y EN EL CONTEXTO ANTERIOR si es relevante.
    2. Habla de forma natural y conversacional, como lo haría una persona real.
    3. Mantén un tono amable, servicial y ligeramente informal.
    4. Si no hay resultados relevantes en la consulta actual PERO la información aparece en respuestas anteriores, USA ESA INFORMACIÓN.
    5. Si hay múltiples resultados, SOLO MUESTRA LOS MÁS RELEVANTES para la consulta.
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

def procesar_consulta_completa(consulta: str, contexto: Optional[Dict[str, Any]] = None, db_path: str = DB_PATH, debug: bool = False) -> Dict[str, Any]:
    """
    Procesa una consulta completa utilizando el flujo de 5 pasos.

    Esta función centraliza todo el proceso de consulta, desde el análisis inicial
    hasta la generación de la respuesta final, siguiendo el flujo de 5 pasos:
    1. Analizar consulta
    2. Generar SQL
    3. Ejecutar SQL
    4. Evaluar resultados
    5. Generar respuesta

    Args:
        consulta (str): Consulta del usuario en lenguaje natural
        contexto (dict, optional): Contexto de la conversación anterior
        db_path (str): Ruta a la base de datos SQLite
        debug (bool): Activar modo de depuración para mostrar información detallada

    Returns:
        dict: Resultado completo del procesamiento con todos los pasos intermedios
    """
    # Verificar que la base de datos existe
    if not os.path.exists(db_path):
        return {
            "error": f"La base de datos no existe en {db_path}.",
            "respuesta": "Lo siento, no puedo acceder a la base de datos en este momento."
        }

    # Paso 1: Analizar la consulta y generar una estrategia de búsqueda
    if debug:
        print(f"DEBUG: Analizando consulta: {consulta}")

    estrategia = analizar_consulta(consulta, contexto, db_path)

    if debug:
        print("DEBUG: Estrategia de búsqueda:")
        print(json.dumps(estrategia, indent=2, ensure_ascii=False))

    # Verificar si hubo un error en el análisis
    if "error" in estrategia:
        return {
            "error": f"Error al analizar la consulta: {estrategia['error']}",
            "respuesta": "Lo siento, no pude entender bien tu consulta. ¿Podrías reformularla?"
        }

    # Verificar si hay un resultado en caché para esta estrategia
    cached_result = llm_cache.get(estrategia)
    if cached_result:
        if debug:
            print("DEBUG: ¡Resultado encontrado en caché!")
            print(f"DEBUG: Estadísticas del caché: {llm_cache.get_stats()}")
        return cached_result

    if debug:
        print("DEBUG: No se encontró en caché, procesando consulta completa...")

    # Paso 2: Generar consulta SQL a partir de la estrategia
    if debug:
        print("DEBUG: Generando consulta SQL...")

    consulta_sql = generar_sql_desde_estrategia(estrategia, db_path)

    if debug:
        print("DEBUG: Consulta SQL generada:")
        print(consulta_sql.get("consulta", "Error: No se generó consulta SQL"))
        if consulta_sql.get("parametros"):
            print("DEBUG: Parámetros SQL:")
            print(consulta_sql["parametros"])

    # Verificar si hubo un error en la generación de SQL
    if "error" in consulta_sql:
        return {
            "error": f"Error al generar SQL: {consulta_sql['error']}",
            "respuesta": "Lo siento, tuve un problema al procesar tu consulta. ¿Podrías intentar con una consulta más simple?"
        }

    # Paso 3: Ejecutar consulta SQL
    if debug:
        print("DEBUG: Ejecutando consulta SQL...")

    resultado_sql = ejecutar_consulta_llm(consulta_sql["consulta"], consulta_sql["parametros"], db_path)

    if debug:
        print("DEBUG: Resultados SQL:")
        print(f"Total: {resultado_sql['total']} registros")
        if resultado_sql["total"] > 0 and resultado_sql["total"] <= 3:
            print(json.dumps(resultado_sql["registros"], indent=2, ensure_ascii=False))
        elif resultado_sql["total"] > 3:
            print(json.dumps(resultado_sql["registros"][:3], indent=2, ensure_ascii=False))
            print(f"... y {resultado_sql['total'] - 3} más")

    # Verificar si hubo un error en la ejecución
    if resultado_sql.get("error"):
        return {
            "error": f"Error al ejecutar SQL: {resultado_sql['error']}",
            "respuesta": "Lo siento, ocurrió un error al buscar en la base de datos. Por favor, intenta con otra consulta."
        }

    # Paso 4: Evaluar resultados
    if debug:
        print("DEBUG: Evaluando resultados...")

    evaluacion = evaluar_resultados(consulta, resultado_sql, estrategia, db_path)

    if debug:
        print("DEBUG: Evaluación de resultados:")
        print(json.dumps(evaluacion, indent=2, ensure_ascii=False))

    # Paso 5: Generar respuesta natural
    if debug:
        print("DEBUG: Generando respuesta natural...")

    respuesta = generar_respuesta_desde_resultados(consulta, resultado_sql, estrategia, evaluacion, db_path)

    # Construir el resultado completo
    resultado = {
        "consulta": consulta,
        "estrategia": estrategia,
        "consulta_sql": consulta_sql,
        "resultado_sql": resultado_sql,
        "evaluacion": evaluacion,
        "respuesta": respuesta,
        "error": resultado_sql.get("error")
    }

    # Guardar en caché
    llm_cache.set(estrategia, resultado)

    if debug:
        print(f"DEBUG: Resultado guardado en caché. Estadísticas: {llm_cache.get_stats()}")

    return resultado
