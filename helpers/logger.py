#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo para el sistema de logging centralizado del asistente de agenda.
Proporciona funciones para registrar eventos, errores y métricas de manera consistente.
"""

import os
import json
import logging
import time
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Optional, Union, List
from colorama import Fore, Style
from helpers.logging_config.config import get_logging_config, update_logging_config, set_console_log_level

# Configuración de directorios
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# Niveles de log personalizados
CONSULTA = 25  # Entre INFO y WARNING
METRICA = 15   # Entre DEBUG e INFO

# Registrar niveles personalizados
logging.addLevelName(CONSULTA, "CONSULTA")
logging.addLevelName(METRICA, "METRICA")


class JsonFormatter(logging.Formatter):
    """
    Formateador personalizado que genera logs en formato JSON.
    """

    def format(self, record):
        """
        Formatea un registro de log como JSON.

        Args:
            record: Registro de log

        Returns:
            str: Registro formateado como JSON
        """
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Añadir excepción si existe
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Añadir datos extra si existen
        if hasattr(record, "detalles") and record.detalles:
            log_data["detalles"] = record.detalles

        return json.dumps(log_data, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    """
    Formateador que añade colores a los logs en consola.
    """

    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'CONSULTA': Fore.BLUE,
        'METRICA': Fore.MAGENTA,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT
    }

    def format(self, record):
        """
        Formatea un registro de log con colores.

        Args:
            record: Registro de log

        Returns:
            str: Registro formateado con colores
        """
        log_message = super().format(record)
        color = self.COLORS.get(record.levelname, Fore.WHITE)
        return f"{color}{log_message}{Style.RESET_ALL}"


class Logger:
    """
    Clase principal para el sistema de logging.
    Proporciona métodos para registrar diferentes tipos de eventos.
    """

    _instance = None
    _logger = None

    @classmethod
    def get_logger(cls):
        """
        Obtiene la instancia del logger (singleton).

        Returns:
            logging.Logger: Instancia del logger
        """
        if cls._logger is None:
            cls._setup_logger()
        return cls._logger

    @classmethod
    def _setup_logger(cls):
        """Configura el logger con los handlers y formateadores."""
        # Obtener configuración de logging
        config = get_logging_config()

        # Crear logger
        logger = logging.getLogger("asistente_agenda")
        logger.setLevel(logging.DEBUG)  # El nivel base siempre es DEBUG

        # Evitar duplicación de logs
        if logger.handlers:
            return

        # Añadir método para registrar consultas
        def consulta(self, message, *args, **kwargs):
            self.log(CONSULTA, message, *args, **kwargs)

        # Añadir método para registrar métricas
        def metrica(self, message, *args, **kwargs):
            self.log(METRICA, message, *args, **kwargs)

        # Añadir métodos personalizados al logger
        logging.Logger.consulta = consulta
        logging.Logger.metrica = metrica

        # Crear handler para archivo de log general
        file_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, "asistente.log"),
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(config["file_level"])
        file_handler.setFormatter(JsonFormatter())

        # Crear handler para archivo de errores
        error_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, "errores.log"),
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=3
        )
        error_handler.setLevel(config["error_level"])
        error_handler.setFormatter(JsonFormatter())

        # Crear handler para consultas
        consulta_handler = RotatingFileHandler(
            os.path.join(LOG_DIR, "consultas.log"),
            maxBytes=10*1024*1024,  # 10 MB
            backupCount=5
        )
        consulta_handler.setLevel(config["consulta_level"])
        consulta_handler.setFormatter(JsonFormatter())

        # Crear handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(config["console_level"])
        console_handler.setFormatter(ColoredConsoleFormatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            '%Y-%m-%d %H:%M:%S'
        ))

        # Añadir handlers al logger
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        logger.addHandler(consulta_handler)
        logger.addHandler(console_handler)

        # Guardar referencia al logger
        cls._logger = logger

        # Guardar referencia a los handlers para poder actualizarlos después
        cls._console_handler = console_handler
        cls._file_handler = file_handler
        cls._error_handler = error_handler
        cls._consulta_handler = consulta_handler

    @classmethod
    def log_consulta(cls, consulta: str, contexto: Optional[Dict[str, Any]] = None,
                    usuario: Optional[str] = None) -> None:
        """
        Registra una consulta del usuario.

        Args:
            consulta (str): Consulta del usuario
            contexto (dict, optional): Contexto de la consulta
            usuario (str, optional): Identificador del usuario
        """
        logger = cls.get_logger()
        detalles = {
            "consulta": consulta,
            "timestamp": time.time()
        }

        if contexto:
            detalles["contexto"] = contexto

        if usuario:
            detalles["usuario"] = usuario

        logger.consulta(f"Nueva consulta: {consulta}", extra={"detalles": detalles})

    @classmethod
    def log_respuesta(cls, consulta: str, respuesta: str,
                     tiempo_ejecucion: Optional[float] = None,
                     cache_hit: Optional[bool] = None) -> None:
        """
        Registra una respuesta del sistema.

        Args:
            consulta (str): Consulta original
            respuesta (str): Respuesta generada
            tiempo_ejecucion (float, optional): Tiempo de ejecución en segundos
            cache_hit (bool, optional): Si la respuesta vino del caché
        """
        logger = cls.get_logger()
        detalles = {
            "consulta": consulta,
            "respuesta": respuesta,
            "timestamp": time.time()
        }

        if tiempo_ejecucion is not None:
            detalles["tiempo_ejecucion"] = tiempo_ejecucion

        if cache_hit is not None:
            detalles["cache_hit"] = cache_hit

        logger.consulta(f"Respuesta generada para: {consulta}", extra={"detalles": detalles})

    @classmethod
    def log_metrica(cls, nombre: str, valor: Union[int, float, str],
                   contexto: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra una métrica del sistema.

        Args:
            nombre (str): Nombre de la métrica
            valor: Valor de la métrica
            contexto (dict, optional): Contexto adicional
        """
        logger = cls.get_logger()
        detalles = {
            "metrica": nombre,
            "valor": valor,
            "timestamp": time.time()
        }

        if contexto:
            detalles["contexto"] = contexto

        logger.metrica(f"Métrica {nombre}: {valor}", extra={"detalles": detalles})

    @classmethod
    def log_error(cls, mensaje: str, error: Optional[Exception] = None,
                 detalles: Optional[Dict[str, Any]] = None) -> None:
        """
        Registra un error del sistema.

        Args:
            mensaje (str): Mensaje descriptivo del error
            error (Exception, optional): Excepción original
            detalles (dict, optional): Detalles adicionales
        """
        logger = cls.get_logger()
        extra_detalles = detalles or {}

        if error:
            extra_detalles["error_type"] = type(error).__name__
            extra_detalles["error_message"] = str(error)

        logger.error(mensaje, exc_info=error is not None, extra={"detalles": extra_detalles})

    @classmethod
    def set_log_level(cls, level_name: str) -> None:
        """
        Establece el nivel de log para la consola.

        Args:
            level_name (str): Nombre del nivel (DEBUG, INFO, WARNING, ERROR)
        """
        # Obtener el nivel de log a partir del nombre
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL
        }
        level = level_map.get(level_name.upper(), logging.INFO)

        # Actualizar la configuración
        config = update_logging_config({"console_level": level})

        # Actualizar el nivel de log en el handler de consola
        if hasattr(cls, '_console_handler') and cls._console_handler:
            cls._console_handler.setLevel(level)

            # Registrar el cambio
            logger = cls.get_logger()
            logger.info(f"Nivel de log en consola cambiado a: {level_name.upper()}")

            return True

        return False


# Funciones de utilidad para uso directo
def log_consulta(consulta: str, contexto: Optional[Dict[str, Any]] = None,
                usuario: Optional[str] = None) -> None:
    """
    Registra una consulta del usuario.

    Args:
        consulta (str): Consulta del usuario
        contexto (dict, optional): Contexto de la consulta
        usuario (str, optional): Identificador del usuario
    """
    Logger.log_consulta(consulta, contexto, usuario)


def log_respuesta(consulta: str, respuesta: str,
                 tiempo_ejecucion: Optional[float] = None,
                 cache_hit: Optional[bool] = None) -> None:
    """
    Registra una respuesta del sistema.

    Args:
        consulta (str): Consulta original
        respuesta (str): Respuesta generada
        tiempo_ejecucion (float, optional): Tiempo de ejecución en segundos
        cache_hit (bool, optional): Si la respuesta vino del caché
    """
    Logger.log_respuesta(consulta, respuesta, tiempo_ejecucion, cache_hit)


def log_metrica(nombre: str, valor: Union[int, float, str],
               contexto: Optional[Dict[str, Any]] = None) -> None:
    """
    Registra una métrica del sistema.

    Args:
        nombre (str): Nombre de la métrica
        valor: Valor de la métrica
        contexto (dict, optional): Contexto adicional
    """
    Logger.log_metrica(nombre, valor, contexto)


def log_error(mensaje: str, error: Optional[Exception] = None,
             detalles: Optional[Dict[str, Any]] = None) -> None:
    """
    Registra un error del sistema.

    Args:
        mensaje (str): Mensaje descriptivo del error
        error (Exception, optional): Excepción original
        detalles (dict, optional): Detalles adicionales
    """
    Logger.log_error(mensaje, error, detalles)


def set_log_level(level_name: str) -> bool:
    """
    Establece el nivel de log para la consola.

    Args:
        level_name (str): Nombre del nivel (DEBUG, INFO, WARNING, ERROR)

    Returns:
        bool: True si se cambió el nivel, False en caso contrario
    """
    return Logger.set_log_level(level_name)
