#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Servidor API para el Asistente de Agenda.
Expone la funcionalidad del asistente a través de endpoints REST.
"""

import os
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
from helpers.dynamic_loader import cargar_agenda_dinamica
from helpers.enhanced_query import process_query
from helpers.session_context import SessionContext
from config import GOOGLE_API_KEY

# Inicializar Flask
app = Flask(__name__)
CORS(app)  # Permitir solicitudes de diferentes orígenes

# Configuración
DEBUG = True
PORT = 5000
HOST = '0.0.0.0'  # Escuchar en todas las interfaces

# Cargar datos al iniciar
print("Cargando datos de la agenda...")
try:
    resultado = cargar_agenda_dinamica("datos/agenda.xlsx")
    registros = resultado["registros"]
    esquema = resultado["esquema"]
    mapeo_columnas = resultado["mapeo_columnas"]
    print(f"Datos cargados: {len(registros)} registros")
except Exception as e:
    print(f"Error al cargar datos: {e}")
    registros = []
    esquema = {}
    mapeo_columnas = {}

# Crear contexto de sesión global (para un solo usuario)
session_context = SessionContext(max_history=5)

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
            "/api/context"
        ]
    })

@app.route('/api/health')
def health_check():
    """Endpoint para verificar el estado del servidor"""
    return jsonify({
        "status": "healthy",
        "data_loaded": len(registros) > 0,
        "record_count": len(registros),
        "session_interactions": len(session_context.interactions)
    })

@app.route('/api/query', methods=['POST'])
def query():
    """Endpoint principal para procesar consultas"""
    # Verificar que hay datos cargados
    if not registros:
        return jsonify({
            "error": "No hay datos cargados en el servidor"
        }), 500
    
    # Obtener datos de la solicitud
    data = request.json
    if not data or 'query' not in data:
        return jsonify({
            "error": "La solicitud debe incluir un campo 'query'"
        }), 400
    
    query_text = data['query']
    
    try:
        # Procesar la consulta usando tu función existente
        result = process_query(
            query=query_text,
            records=registros,
            schema=esquema,
            column_mapping=mapeo_columnas,
            debug=DEBUG
        )
        
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
    global session_context
    session_context.reset_session()
    return jsonify({
        "status": "success",
        "message": "Contexto de sesión reiniciado"
    })

@app.route('/api/context', methods=['GET'])
def get_context():
    """Endpoint para obtener el contexto actual (útil para depuración)"""
    return jsonify(session_context.get_context_for_prompt())

if __name__ == '__main__':
    # Iniciar el servidor
    print(f"Iniciando servidor en http://{HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
