"""
Módulo para procesamiento mejorado de consultas a la agenda.
Implementa un enfoque de dos pasos con mejor separación de responsabilidades:
1. Primer prompt: Extraer parámetros de búsqueda
2. Búsqueda directa: Encontrar datos relevantes
3. Segundo prompt: Generar respuesta natural con contexto
"""

import json
import google.generativeai as genai
from config import GOOGLE_API_KEY
from helpers.session_context import SessionContext

# Configurar API
genai.configure(api_key=GOOGLE_API_KEY)

# Contexto global de sesión
global_session_context = SessionContext(max_history=5)

def extract_query_parameters(query):
    """
    Extrae parámetros de búsqueda de la consulta del usuario.

    Args:
        query (str): Consulta del usuario

    Returns:
        dict: Parámetros de búsqueda extraídos
    """
    # Prompt enfocado exclusivamente en extraer parámetros
    prompt = f"""
    Analiza esta consulta sobre una agenda de contactos y extrae SOLO los parámetros de búsqueda.

    Consulta: {query}

    Devuelve ÚNICAMENTE un objeto JSON con estos campos:
    - tipo_consulta: "atributo_persona" (busca info de alguien), "filtrado" (busca personas que cumplen condición), "conteo" (cuenta personas), "general" (otro tipo)
    - persona: Nombre de la persona mencionada (si aplica)
    - atributo: Atributo buscado como "telefono", "direccion", "correo", "edad", "genero" (si aplica)
    - condicion: Condición de filtrado como "mayor_que", "menor_que", "igual_a" (si aplica)
    - valor: Valor para la condición (si aplica)

    Ejemplos:
    Para "¿Cuál es el teléfono de Juan?":
    {{"tipo_consulta": "atributo_persona", "persona": "Juan", "atributo": "telefono"}}

    Para "¿Quién tiene más de 30 años?":
    {{"tipo_consulta": "filtrado", "atributo": "edad", "condicion": "mayor_que", "valor": 30}}

    Para "¿Cuántas personas hay en la agenda?":
    {{"tipo_consulta": "conteo"}}

    Para "¿Y su dirección?" (pregunta de seguimiento sobre alguien mencionado antes):
    {{"tipo_consulta": "atributo_persona", "atributo": "direccion"}}

    Responde SOLO con el JSON, sin texto adicional.
    """

    # Llamar al modelo para extraer parámetros
    modelo = genai.GenerativeModel(model_name="gemini-1.5-flash")
    respuesta = modelo.generate_content(prompt)

    try:
        # Limpiar y parsear la respuesta
        texto_respuesta = respuesta.text.strip()
        if texto_respuesta.startswith("```json"):
            texto_respuesta = texto_respuesta.replace("```json", "").replace("```", "").strip()
        elif texto_respuesta.startswith("```"):
            texto_respuesta = texto_respuesta.replace("```", "").strip()

        parametros = json.loads(texto_respuesta)
        return parametros
    except Exception as e:
        print(f"Error al parsear respuesta JSON: {e}")
        print(f"Respuesta recibida: {respuesta.text}")
        return {
            "tipo_consulta": "general",
            "error": str(e)
        }

def search_data(parameters, records, session_context=None):
    """
    Busca datos relevantes según los parámetros extraídos.

    Args:
        parameters (dict): Parámetros de búsqueda
        records (list): Registros de la agenda
        session_context (SessionContext): Contexto de la sesión (opcional)

    Returns:
        dict: Datos relevantes encontrados
    """
    result = {
        "query_type": parameters.get("tipo_consulta", "general"),
        "relevant_data": [],
        "parameters": parameters
    }

    # Completar parámetros con información del contexto si es necesario
    if session_context and session_context.is_follow_up_query(parameters.get("query", "")):
        # Si es una consulta de seguimiento y no especifica persona, usar la última mencionada
        if not parameters.get("persona") and session_context.last_mentioned_person:
            parameters["persona"] = session_context.last_mentioned_person
            result["context_used"] = True
            result["context_info"] = f"Used last mentioned person: {session_context.last_mentioned_person}"

    # Consulta de atributo de persona
    if parameters.get("tipo_consulta") == "atributo_persona":
        person_name = parameters.get("persona", "").lower()
        attribute = parameters.get("atributo")

        # Lista para almacenar coincidencias
        matches = []

        # Primera pasada: buscar coincidencias exactas
        for record in records:
            full_name = record.get("nombre", "").lower()
            if full_name == person_name:
                matches.append(record)

        # Segunda pasada: buscar coincidencias parciales si no hay exactas
        if not matches:
            for record in records:
                full_name = record.get("nombre", "").lower()
                if person_name in full_name:
                    matches.append(record)
                elif any(part.lower() == person_name for part in full_name.split()):
                    matches.append(record)

        # Procesar coincidencias encontradas
        for record in matches:
            if attribute:
                # Si se busca un atributo específico, devolver solo ese
                person_data = {
                    "nombre": record.get("nombre")
                }
                # Añadir el atributo buscado si existe
                if attribute in record:
                    person_data[attribute] = record.get(attribute)
                # Si no existe el atributo específico, incluir todo el registro para contexto
                else:
                    person_data = record
                result["relevant_data"].append(person_data)
            else:
                # Si no se especifica atributo, devolver el registro completo
                result["relevant_data"].append(record)

    # Consulta de filtrado
    elif parameters.get("tipo_consulta") == "filtrado":
        attribute = parameters.get("atributo")
        condition = parameters.get("condicion")
        value = parameters.get("valor")

        if attribute and condition:
            for record in records:
                if attribute in record:
                    # Convertir a número si es posible para comparaciones numéricas
                    try:
                        record_value = float(record[attribute]) if isinstance(record[attribute], (int, float, str)) else record[attribute]
                        comparison_value = float(value) if value and isinstance(value, (int, float, str)) else value

                        # Aplicar la condición
                        if condition == "mayor_que" and comparison_value is not None:
                            if record_value > comparison_value:
                                result["relevant_data"].append(record)
                        elif condition == "menor_que" and comparison_value is not None:
                            if record_value < comparison_value:
                                result["relevant_data"].append(record)
                        elif condition == "igual_a" and comparison_value is not None:
                            if record_value == comparison_value:
                                result["relevant_data"].append(record)
                    except (ValueError, TypeError):
                        # Si no se puede convertir a número, hacer comparación de texto
                        if condition == "igual_a" and value is not None:
                            if str(record[attribute]).lower() == str(value).lower():
                                result["relevant_data"].append(record)

    # Consulta de conteo
    elif parameters.get("tipo_consulta") == "conteo":
        # Para conteo general
        result["count"] = len(records)

        # Si hay atributo específico para contar (ej: "cuántos hombres hay")
        attribute = parameters.get("atributo")
        value = parameters.get("valor")

        if attribute and value:
            # Contar registros que cumplen la condición
            specific_count = sum(1 for r in records if attribute in r and str(r[attribute]).lower() == str(value).lower())
            result["specific_count"] = specific_count
            result["criteria"] = f"{attribute}={value}"

    # Consulta general o no reconocida
    else:
        # Para consultas generales, incluir una muestra pequeña
        result["relevant_data"] = records[:3] if len(records) > 3 else records
        result["total_records"] = len(records)

    return result

def generate_natural_response(query, search_result, session_context=None):
    """
    Genera una respuesta natural basada en los datos encontrados y el contexto.

    Args:
        query (str): Consulta original del usuario
        search_result (dict): Resultado de la búsqueda
        session_context (SessionContext): Contexto de la sesión (opcional)

    Returns:
        str: Respuesta natural generada
    """
    # Preparar el historial de conversación en formato claro
    conversation_history = []
    is_follow_up = False

    if session_context:
        is_follow_up = session_context.is_follow_up_query(query)

        # Obtener las interacciones recientes
        for interaction in session_context.interactions:
            # Asegurarse de que la estructura es correcta
            user_query = interaction.get("query", "")
            assistant_response = interaction.get("response", "")
            conversation_history.append({
                "user": user_query,
                "assistant": assistant_response
            })

    # Construir un contexto más claro y explícito
    context_section = ""
    if conversation_history:
        context_section = "HISTORIAL DE CONVERSACIÓN:\n"
        for i, exchange in enumerate(conversation_history):
            context_section += f"Usuario: {exchange.get('user', '')}\n"
            context_section += f"Asistente: {exchange.get('assistant', '')}\n"
            if i < len(conversation_history) - 1:
                context_section += "---\n"

    # Información sobre la última persona mencionada
    last_person_info = ""
    if session_context and session_context.last_mentioned_person:
        last_person_info = f"La última persona mencionada fue: {session_context.last_mentioned_person}"

    # Prompt centralizado y mejorado
    prompt = f"""
    Eres un asistente de agenda personal que mantiene una conversación continua con el usuario.
    Tienes memoria de la conversación y puedes referirte a información mencionada previamente.

    CONSULTA ACTUAL DEL USUARIO:
    {query}

    {f"HISTORIAL DE CONVERSACIÓN:\n{context_section}" if context_section else ""}

    {last_person_info if last_person_info else ""}

    {"Esta parece ser una pregunta de seguimiento relacionada con la conversación anterior." if is_follow_up else ""}

    DATOS RELEVANTES ENCONTRADOS:
    {json.dumps(search_result, ensure_ascii=False, indent=2)}

    INSTRUCCIONES:

    1. ROL Y PERSONALIDAD:
       - Eres un asistente humano que ayuda a gestionar una agenda de contactos.
       - Hablas de forma natural y conversacional, como lo haría una persona real.
       - Mantienes un tono amable, servicial y ligeramente informal.

    2. MANEJO DEL CONTEXTO:
       - Usa el historial de la conversación para dar respuestas coherentes.
       - Si se menciona "él", "ella" o "su" sin especificar, asume que se refiere a la última persona mencionada.
       - Mantén la continuidad de la conversación, recordando lo que se ha dicho antes.
       - Si es una pregunta de seguimiento, relaciona tu respuesta con la información previa.
       - Usa el contexto para responder preguntas de seguimiento, como "¿Y su dirección?" o "¿Cuál es su edad?".
       - Prioriza el uso del contexto para responder consultas
       - IMPORTANTE MANTEN UNA SENSANCION DE UNIDAD IMAGINA QUE ERES UN SER HUMANO Y SIMULA LO MEJOR POSIBLE UNA EXPERIENCIA UNIFICADA ENTRE MENSAJES

    3. ESTILO DE RESPUESTA:
       - Usa un lenguaje natural con variedad en la estructura de tus frases.
       - Puedes usar expresiones coloquiales como "Pues", "Claro", "Por supuesto" ocasionalmente.
       - Añade pequeños comentarios personales cuando sea apropiado.
       - Adapta tu tono según el tipo de pregunta (informativa, personal, etc.).
       - Varía la longitud de tus respuestas para sonar más natural.

    4. CONTENIDO:
       - Responde ÚNICAMENTE basándote en los datos proporcionados.
       - Sé preciso con la información, pero exprésala de forma conversacional.
       - Si no hay datos relevantes, indica claramente que no tienes esa información.

    5. EVITAR:
       - NO uses fórmulas repetitivas como "Según los datos..." o "La información indica...".
       - NO preguntes "¿Necesitas algo más?" o "¿Te puedo ayudar con algo más?".
       - NO uses emojis ni excesivos signos de exclamación.
       - NO uses frases artificiales como "Procesando..." o "Buscando información...".
       - NO repitas exactamente las mismas estructuras de frase en respuestas consecutivas.

    GENERA UNA RESPUESTA NATURAL Y HUMANA:
    """

    # Llamar al modelo para generar la respuesta
    modelo = genai.GenerativeModel(model_name="gemini-1.5-flash")
    respuesta = modelo.generate_content(prompt)

    # Devolver tanto la respuesta como el prompt utilizado
    return {
        "response_text": respuesta.text,
        "prompt_used": prompt
    }

def process_query(query, records, schema=None, column_mapping=None, debug=False):
    """
    Procesa una consulta usando el enfoque mejorado de dos pasos.

    Args:
        query (str): Consulta del usuario
        records (list): Registros de la agenda
        schema (dict): Esquema de la base de datos (opcional)
        column_mapping (dict): Mapeo de columnas (opcional)
        debug (bool): Activar modo de depuración

    Returns:
        dict: Resultado del procesamiento con todos los detalles
    """
    # Paso 1: Extraer parámetros de la consulta
    parameters = extract_query_parameters(query)

    # Añadir la consulta original a los parámetros para referencia
    parameters["query"] = query

    if debug:
        print(f"\n=== DEBUG: EXTRACTED PARAMETERS ===")
        print(json.dumps(parameters, indent=2, ensure_ascii=False))

    # Paso 2: Buscar datos relevantes
    search_result = search_data(parameters, records, global_session_context)

    if debug:
        print(f"\n=== DEBUG: SEARCH RESULT ===")
        print(json.dumps(search_result, indent=2, ensure_ascii=False))

    # Paso 3: Generar respuesta natural
    response_data = generate_natural_response(query, search_result, global_session_context)
    response_text = response_data["response_text"]
    prompt_used = response_data["prompt_used"]

    if debug:
        print(f"\n=== DEBUG: PROMPT USED ===")
        print(prompt_used)
        print(f"\n=== DEBUG: GENERATED RESPONSE ===")
        print(response_text)

    # Actualizar el contexto de la sesión
    global_session_context.add_interaction(query, parameters, response_text)

    # Devolver resultado completo
    result = {
        "query": query,
        "parameters": parameters,
        "search_result": search_result,
        "response": response_text,
        "prompt_used": prompt_used,
        "is_follow_up": global_session_context.is_follow_up_query(query)
    }

    return result
