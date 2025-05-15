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

# Inicializar Flask
app = Flask(__name__)
CORS(app)  # Permitir solicitudes de diferentes orígenes

# Importar configuración centralizada
from config import DB_PATH

# Configuración
DEBUG = True
PORT = 5000
HOST = '0.0.0.0'  # Escuchar en todas las interfaces

# Verificar conexión a la base de datos
print("Verificando conexión a la base de datos SQLite...")
try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM contactos")
    record_count = cursor.fetchone()[0]
    conn.close()
    print(f"Conexión exitosa: {record_count} registros en la base de datos")

    # Obtener vista previa de la base de datos
    vista_previa = obtener_vista_previa_db(DB_PATH)
    print("Muestra de nombres únicos:")
    print(json.dumps(vista_previa.get('nombres_unicos', [])[:5], indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error al conectar con la base de datos: {e}")
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

    # Verificar que hay datos cargados
    if record_count == 0:
        return jsonify({
            "error": "No hay datos cargados en la base de datos"
        }), 500

    # Obtener datos de la solicitud
    data = request.json
    if not data or 'query' not in data:
        return jsonify({
            "error": "La solicitud debe incluir un campo 'query'"
        }), 400

    query_text = data['query']

    # Generar un ID único para esta solicitud
    request_id = f"{query_text}_{time.time()}"

    # Verificar si esta solicitud es un duplicado
    if request_id == last_request_id:
        print(f"Solicitud duplicada detectada: {query_text}")
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

        # Usar la función centralizada para procesar la consulta
        print(f"Procesando consulta: {query_text}")
        resultado_procesamiento = procesar_consulta_completa(query_text, contexto, DB_PATH, DEBUG)

        # Extraer la respuesta y otros datos del resultado
        respuesta = resultado_procesamiento["respuesta"]
        estrategia = resultado_procesamiento["estrategia"]
        resultado_sql = resultado_procesamiento["resultado_sql"]

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
                "total": resultado_sql["total"],
                "records": resultado_sql["registros"][:5] if resultado_sql["total"] > 5 else resultado_sql["registros"]
            }
        }

        # Devolver el resultado
        return jsonify(result)

    except Exception as e:
        # Manejar errores
        print(f"Error al procesar consulta: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": f"Error al procesar la consulta: {str(e)}",
            "query": query_text
        }), 500

@app.route('/api/reset', methods=['POST'])
def reset_context():
    """Endpoint para reiniciar el contexto de la sesión"""
    global historial_consultas, historial_respuestas
    historial_consultas = []
    historial_respuestas = []
    return jsonify({
        "status": "success",
        "message": "Contexto de conversación reiniciado"
    })

@app.route('/api/context', methods=['GET'])
def get_context():
    """Endpoint para obtener el contexto actual (útil para depuración)"""
    if not historial_consultas:
        return jsonify({
            "status": "empty",
            "message": "No hay historial de conversación"
        })

    return jsonify({
        "historial_consultas": historial_consultas,
        "historial_respuestas": historial_respuestas,
        "total_interacciones": len(historial_consultas)
    })

if __name__ == '__main__':
    # Iniciar el servidor
    print(f"Iniciando servidor en http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
