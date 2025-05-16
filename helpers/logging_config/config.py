#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Configuración del sistema de logging para el asistente de agenda.
Este archivo centraliza la configuración de niveles de log para diferentes componentes.
"""

import logging

# Niveles de log estándar:
# DEBUG = 10
# INFO = 20
# WARNING = 30
# ERROR = 40
# CRITICAL = 50

# Configuración por defecto
DEFAULT_CONFIG = {
    # Nivel de log para la consola
    "console_level": logging.INFO,
    
    # Nivel de log para archivos
    "file_level": logging.DEBUG,
    
    # Nivel de log para errores
    "error_level": logging.ERROR,
    
    # Nivel de log para consultas
    "consulta_level": 25,  # Nivel personalizado CONSULTA
    
    # Mostrar información de depuración en la consola
    "show_debug_in_console": False,
    
    # Mostrar información detallada de SQL en la consola
    "show_sql_in_console": False,
    
    # Mostrar información de caché en la consola
    "show_cache_in_console": False,
    
    # Mostrar tiempos de ejecución en la consola
    "show_timing_in_console": True,
}

# Función para obtener la configuración actual
def get_logging_config():
    """
    Obtiene la configuración actual de logging.
    
    Returns:
        dict: Configuración de logging
    """
    return DEFAULT_CONFIG.copy()

# Función para actualizar la configuración
def update_logging_config(new_config):
    """
    Actualiza la configuración de logging.
    
    Args:
        new_config (dict): Nueva configuración
        
    Returns:
        dict: Configuración actualizada
    """
    global DEFAULT_CONFIG
    DEFAULT_CONFIG.update(new_config)
    return DEFAULT_CONFIG.copy()

# Función para establecer el nivel de log de la consola
def set_console_log_level(level):
    """
    Establece el nivel de log para la consola.
    
    Args:
        level (int): Nivel de log (logging.DEBUG, logging.INFO, etc.)
        
    Returns:
        dict: Configuración actualizada
    """
    return update_logging_config({"console_level": level})

# Función para activar/desactivar la depuración en consola
def set_debug_mode(enabled):
    """
    Activa o desactiva el modo de depuración en consola.
    
    Args:
        enabled (bool): True para activar, False para desactivar
        
    Returns:
        dict: Configuración actualizada
    """
    new_config = {
        "show_debug_in_console": enabled,
        "console_level": logging.DEBUG if enabled else logging.INFO
    }
    return update_logging_config(new_config)

# Función para obtener el nivel de log a partir de un nombre
def get_log_level_from_name(level_name):
    """
    Obtiene el nivel de log a partir de su nombre.
    
    Args:
        level_name (str): Nombre del nivel (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        int: Nivel de log correspondiente
    """
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    return level_map.get(level_name.upper(), logging.INFO)
