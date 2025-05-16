#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Servidor API para el Asistente de Agenda con SQLite.
Expone la funcionalidad del asistente a través de endpoints REST.
"""

import json
import time
import sqlite3
from flask import Flask, request, jsonify
from flask_cors import CORS
from helpers.llm_search import (
    procesar_consulta_completa,
    obtener_vista_previa_db,
    llm_cache
)
from helpers.error_handler import ErrorHandler, DatosError
from helpers.logger import Logger, log_consulta, log_respuesta, log_metrica, log_error

# Inicializar Flask
app = Flask(__name__)
CORS(app)  # Permitir solicitudes de diferentes orígenes

# Inicializar logger
logger = Logger.get_logger()

# Importar configuración centralizada
from config import DB_PATH

# Configuración
DEBUG = True
PORT = 5000
HOST = '0.0.0.0'  # Escuchar en todas las interfaces

# Registrar inicio del servidor
logger.info(f"Iniciando servidor API en {HOST}:{PORT}")
log_metrica("servidor_iniciado", 1, {"host": HOST, "port": PORT})

# Verificar conexión a la base de datos
logger.info("Verificando conexión a la base de datos SQLite...")
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM contactos")
    record_count = cursor.fetchone()[0]
    conn.close()
    logger.info(f"Conexión exitosa: {record_count} registros en la base de datos")
    log_metrica("registros_cargados", record_count)

    # Obtener vista previa de la base de datos
    vista_previa = obtener_vista_previa_db(DB_PATH)
    logger.info("Muestra de nombres únicos cargada")
    if DEBUG:
        print("Muestra de nombres únicos:")
        print(json.dumps(vista_previa.get('nombres_unicos', [])[:5], indent=2, ensure_ascii=False))
except Exception as e:
    error_info = ErrorHandler.handle_error(e, "DATOS")
    log_error("Error al conectar con la base de datos", e)
    record_count = 0

# Historial de conversación para mantener contexto
historial_consultas = []
historial_respuestas = []

# Variable para evitar procesamiento duplicado de solicitudes
last_request_id = None

@app.route('/')
def index():
    """Página de inicio simple para verificar que el servidor está funcionando"""
    return jsonify({
        "status": "online",
        "message": "API del Asistente de Agenda",
        "endpoints": [
            "/api/query",
            "/api/health",
            "/api/reset",
            "/api/context",
            "/api/cache",
            "/api/cache/clear"
        ],
        "cache_stats": llm_cache.get_stats()
    })

@app.route('/api/health')
def health_check():
    """Endpoint para verificar el estado del servidor"""
    return jsonify({
        "status": "healthy",
        "data_loaded": record_count > 0,
        "record_count": record_count,
        "context_history": len(historial_consultas),
        "cache_stats": llm_cache.get_stats()
    })

@app.route('/api/cache', methods=['GET'])
def cache_info():
    """Endpoint para obtener información del caché"""
    return jsonify({
        "stats": llm_cache.get_stats(),
        "status": "active"
    })

@app.route('/api/cache/clear', methods=['POST'])
def cache_clear():
    """Endpoint para limpiar el caché"""
    llm_cache.cache = {}
    llm_cache.hits = 0
    llm_cache.misses = 0
    llm_cache.save_to_disk()
    return jsonify({
        "status": "success",
        "message": "Caché limpiado correctamente",
        "stats": llm_cache.get_stats()
    })

@app.route('/api/query', methods=['POST'])
def query():
    """Endpoint principal para procesar consultas"""
    global last_request_id, historial_consultas, historial_respuestas

    # Iniciar temporizador para medir tiempo de respuesta
    tiempo_inicio = time.time()

    # Verificar que hay datos cargados
    if record_count == 0:
        error_info = ErrorHandler.handle_error(
            DatosError("No hay datos cargados en la base de datos"),
            "DATOS"
        )
        log_error("API: No hay datos cargados", None)
        return jsonify({
            "error": error_info["mensaje"],
            "message": ErrorHandler.get_user_message(error_info)
        }), 500

    # Obtener datos de la solicitud
    data = request.json
    if not data or 'query' not in data:
        error_info = ErrorHandler.handle_error(
            ValueError("La solicitud debe incluir un campo 'query'"),
            "API"
        )
        log_error("API: Solicitud inválida", None, {"data": data})
        return jsonify({
            "error": error_info["mensaje"],
            "message": "La solicitud debe incluir un campo 'query'"
        }), 400

    query_text = data['query']

    # Registrar la consulta recibida
    log_consulta(query_text, {"ip": request.remote_addr, "user_agent": request.user_agent.string})
    logger.info(f"API: Consulta recibida: {query_text}")

    # Generar un ID único para esta solicitud
    request_id = f"{query_text}_{time.time()}"

    # Verificar si esta solicitud es un duplicado
    if request_id == last_request_id:
        logger.warning(f"API: Solicitud duplicada detectada: {query_text}")
        log_metrica("solicitud_duplicada", 1, {"consulta": query_text})
        return jsonify({
            "warning": "Solicitud duplicada detectada",
            "query": query_text,
            "response": "Por favor, espera un momento antes de enviar la misma consulta nuevamente."
        })

    # Actualizar el ID de la última solicitud
    last_request_id = request_id

    try:
        # Preparar contexto para la consulta
        contexto = None
        if historial_consultas and historial_respuestas:
            contexto = {
                "consulta_anterior": historial_consultas[-1],
                "respuesta_anterior": historial_respuestas[-1],
                "historial_consultas": historial_consultas,
                "historial_respuestas": historial_respuestas
            }
            log_metrica("consulta_con_contexto", 1, {"historial_length": len(historial_consultas)})

        # Usar la función centralizada para procesar la consulta
        logger.info(f"API: Procesando consulta: {query_text}")
        resultado_procesamiento = procesar_consulta_completa(query_text, contexto, DB_PATH, DEBUG)

        # Extraer la respuesta y otros datos del resultado
        respuesta = resultado_procesamiento["respuesta"]
        estrategia = resultado_procesamiento.get("estrategia", {})
        resultado_sql = resultado_procesamiento.get("resultado_sql", {"total": 0, "registros": []})

        # Actualizar historial
        historial_consultas.append(query_text)
        historial_respuestas.append(respuesta)

        # Limitar el historial a los últimos 10 elementos
        if len(historial_consultas) > 10:
            historial_consultas = historial_consultas[-10:]
            historial_respuestas = historial_respuestas[-10:]

        # Preparar resultado para la API
        result = {
            "query": query_text,
            "response": respuesta,
            "is_follow_up": contexto is not None,
            "parameters": estrategia,
            "search_result": {
                "total": resultado_sql.get("total", 0),
                "records": resultado_sql.get("registros", [])[:5] if resultado_sql.get("total", 0) > 5 else resultado_sql.get("registros", [])
            }
        }

        # Registrar tiempo de respuesta
        tiempo_respuesta = time.time() - tiempo_inicio
        log_metrica("tiempo_respuesta_api", tiempo_respuesta, {
            "tipo_consulta": estrategia.get("tipo_consulta", "general"),
            "resultados": resultado_sql.get("total", 0)
        })
        logger.info(f"API: Consulta procesada en {tiempo_respuesta:.2f} segundos")

        # Registrar la respuesta
        log_respuesta(query_text, respuesta, tiempo_respuesta, resultado_procesamiento.get("from_cache", False))

        # Devolver el resultado
        return jsonify(result)

    except Exception as e:
        # Manejar errores con el sistema centralizado
        error_info = ErrorHandler.handle_error(e, "API", mostrar_traceback=True)
        log_error("Error al procesar consulta en API", e, {"consulta": query_text})

        # Registrar tiempo de respuesta en caso de error
        tiempo_respuesta = time.time() - tiempo_inicio
        log_metrica("tiempo_respuesta_error", tiempo_respuesta, {"consulta": query_text})

        return jsonify({
            "error": error_info["mensaje"],
            "message": ErrorHandler.get_user_message(error_info),
            "query": query_text
        }), 500

@app.route('/api/reset', methods=['POST'])
def reset_context():
    """Endpoint para reiniciar el contexto de la sesión"""
    global historial_consultas, historial_respuestas

    # Registrar la acción
    logger.info("API: Reiniciando contexto de conversación")
    log_metrica("contexto_reiniciado", 1, {"historial_length": len(historial_consultas)})

    # Guardar historial anterior para el log
    historial_anterior = {
        "consultas": historial_consultas.copy(),
        "respuestas": historial_respuestas.copy()
    }

    # Reiniciar historial
    historial_consultas = []
    historial_respuestas = []

    return jsonify({
        "status": "success",
        "message": "Contexto de conversación reiniciado"
    })

@app.route('/api/context', methods=['GET'])
def get_context():
    """Endpoint para obtener el contexto actual (útil para depuración)"""
    # Registrar la acción
    logger.info("API: Solicitud de contexto actual")
    log_metrica("consulta_contexto", 1)

    if not historial_consultas:
        logger.info("API: No hay historial de conversación")
        return jsonify({
            "status": "empty",
            "message": "No hay historial de conversación"
        })

    return jsonify({
        "historial_consultas": historial_consultas,
        "historial_respuestas": historial_respuestas,
        "total_interacciones": len(historial_consultas)
    })

# Manejador de errores para rutas no encontradas
@app.errorhandler(404)
def not_found(error):
    """Manejador para rutas no encontradas"""
    log_error("API: Ruta no encontrada", None, {"path": request.path, "method": request.method})
    return jsonify({
        "error": "Ruta no encontrada",
        "message": f"La ruta {request.path} no existe en esta API"
    }), 404

# Manejador de errores para métodos no permitidos
@app.errorhandler(405)
def method_not_allowed(error):
    """Manejador para métodos no permitidos"""
    log_error("API: Método no permitido", None, {"path": request.path, "method": request.method})
    return jsonify({
        "error": "Método no permitido",
        "message": f"El método {request.method} no está permitido para la ruta {request.path}"
    }), 405

# Manejador de errores para errores internos
@app.errorhandler(500)
def internal_error(error):
    """Manejador para errores internos del servidor"""
    log_error("API: Error interno del servidor", error)
    return jsonify({
        "error": "Error interno del servidor",
        "message": "Ha ocurrido un error interno. Por favor, inténtalo de nuevo más tarde."
    }), 500

if __name__ == '__main__':
    # Iniciar el servidor
    logger.info(f"Iniciando servidor en http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
