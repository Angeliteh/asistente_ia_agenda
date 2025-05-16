#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Módulo para el manejo centralizado de errores del asistente de agenda.
Define tipos de errores específicos y proporciona funciones para manejarlos de manera consistente.
"""

import traceback
import json
from typing import Dict, Any, Optional, Union, List
from colorama import Fore, Style

# Definición de tipos de errores específicos
class AsistenteError(Exception):
    """Clase base para todos los errores del asistente."""
    
    def __init__(self, mensaje: str, detalles: Optional[Dict[str, Any]] = None):
        """
        Inicializa un error del asistente.
        
        Args:
            mensaje (str): Mensaje descriptivo del error
            detalles (dict, optional): Detalles adicionales del error
        """
        self.mensaje = mensaje
        self.detalles = detalles or {}
        super().__init__(self.mensaje)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convierte el error a un diccionario.
        
        Returns:
            dict: Representación del error como diccionario
        """
        return {
            "tipo": self.__class__.__name__,
            "mensaje": self.mensaje,
            "detalles": self.detalles
        }
    
    def __str__(self) -> str:
        """
        Representación en string del error.
        
        Returns:
            str: Mensaje de error formateado
        """
        if self.detalles:
            return f"{self.mensaje} - Detalles: {json.dumps(self.detalles, ensure_ascii=False)}"
        return self.mensaje


class ConsultaError(AsistenteError):
    """Error relacionado con el análisis o procesamiento de una consulta."""
    pass


class SQLError(AsistenteError):
    """Error relacionado con la generación o ejecución de SQL."""
    pass


class LLMError(AsistenteError):
    """Error relacionado con la comunicación con el modelo LLM."""
    pass


class DatosError(AsistenteError):
    """Error relacionado con la base de datos o los datos."""
    pass


class ConfigError(AsistenteError):
    """Error relacionado con la configuración del sistema."""
    pass


# Clase principal para el manejo de errores
class ErrorHandler:
    """
    Manejador centralizado de errores para el asistente.
    Proporciona métodos para manejar diferentes tipos de errores de manera consistente.
    """
    
    @staticmethod
    def handle_error(error: Exception, tipo_error: str = "general", 
                    mostrar_traceback: bool = False, 
                    log_error: bool = True) -> Dict[str, Any]:
        """
        Maneja un error y devuelve un diccionario con la información del error.
        
        Args:
            error (Exception): El error a manejar
            tipo_error (str): Tipo de error (para categorización)
            mostrar_traceback (bool): Si se debe mostrar el traceback completo
            log_error (bool): Si se debe registrar el error en el log
            
        Returns:
            dict: Diccionario con información del error
        """
        # Convertir a AsistenteError si no lo es ya
        if not isinstance(error, AsistenteError):
            if "LLM" in tipo_error.upper():
                error = LLMError(str(error), {"original_error": str(error)})
            elif "SQL" in tipo_error.upper():
                error = SQLError(str(error), {"original_error": str(error)})
            elif "CONSULTA" in tipo_error.upper():
                error = ConsultaError(str(error), {"original_error": str(error)})
            elif "DATOS" in tipo_error.upper():
                error = DatosError(str(error), {"original_error": str(error)})
            elif "CONFIG" in tipo_error.upper():
                error = ConfigError(str(error), {"original_error": str(error)})
            else:
                error = AsistenteError(str(error), {"original_error": str(error)})
        
        # Obtener información del error
        error_info = error.to_dict()
        
        # Añadir traceback si se solicita
        if mostrar_traceback:
            error_info["traceback"] = traceback.format_exc()
        
        # Mostrar mensaje de error en consola
        print(f"{Fore.RED}❌ Error ({error_info['tipo']}): {error_info['mensaje']}{Style.RESET_ALL}")
        
        # Registrar error en el log si se solicita
        if log_error:
            from helpers.logger import Logger
            logger = Logger.get_logger()
            logger.error(f"Error ({error_info['tipo']}): {error_info['mensaje']}", 
                        extra={"detalles": error_info['detalles']})
        
        return error_info
    
    @staticmethod
    def format_error_response(error_info: Dict[str, Any], 
                             user_friendly: bool = True) -> Dict[str, Any]:
        """
        Formatea un error para devolverlo como respuesta al usuario.
        
        Args:
            error_info (dict): Información del error
            user_friendly (bool): Si se debe formatear de manera amigable para el usuario
            
        Returns:
            dict: Respuesta formateada para el usuario
        """
        if user_friendly:
            # Mensajes amigables según el tipo de error
            mensajes_amigables = {
                "LLMError": "Hubo un problema al procesar tu consulta. Por favor, intenta de nuevo o reformula tu pregunta.",
                "SQLError": "Hubo un problema al buscar la información solicitada. Por favor, intenta con una consulta más específica.",
                "ConsultaError": "No pude entender completamente tu consulta. ¿Podrías reformularla de otra manera?",
                "DatosError": "Hubo un problema al acceder a los datos. Por favor, verifica que la información que buscas existe.",
                "ConfigError": "Hay un problema con la configuración del sistema. Por favor, contacta al administrador.",
                "AsistenteError": "Ocurrió un error inesperado. Por favor, intenta de nuevo más tarde."
            }
            
            tipo = error_info.get("tipo", "AsistenteError")
            mensaje = mensajes_amigables.get(tipo, mensajes_amigables["AsistenteError"])
            
            return {
                "error": True,
                "mensaje": mensaje,
                "tipo": tipo
            }
        else:
            # Respuesta técnica con todos los detalles
            return {
                "error": True,
                "mensaje": error_info.get("mensaje", "Error desconocido"),
                "tipo": error_info.get("tipo", "AsistenteError"),
                "detalles": error_info.get("detalles", {}),
                "traceback": error_info.get("traceback", None)
            }
    
    @staticmethod
    def get_user_message(error_info: Dict[str, Any]) -> str:
        """
        Obtiene un mensaje amigable para el usuario basado en la información del error.
        
        Args:
            error_info (dict): Información del error
            
        Returns:
            str: Mensaje amigable para el usuario
        """
        tipo = error_info.get("tipo", "AsistenteError")
        
        # Mensajes específicos según el tipo de error
        if tipo == "LLMError":
            return "Lo siento, estoy teniendo problemas para procesar tu consulta en este momento. ¿Podrías intentar de nuevo o reformular tu pregunta?"
        elif tipo == "SQLError":
            return "Lo siento, estoy teniendo problemas para buscar la información que solicitaste. ¿Podrías ser más específico en tu consulta?"
        elif tipo == "ConsultaError":
            return "No estoy seguro de entender lo que estás preguntando. ¿Podrías reformular tu consulta de otra manera?"
        elif tipo == "DatosError":
            return "No pude encontrar la información que buscas. ¿Estás seguro de que los datos existen en la agenda?"
        elif tipo == "ConfigError":
            return "Hay un problema con mi configuración interna. Por favor, contacta al administrador del sistema."
        else:
            return "Lo siento, ocurrió un error inesperado. Por favor, intenta de nuevo más tarde."


# Funciones de utilidad para manejar errores comunes
def handle_llm_error(error: Exception, detalles: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Maneja un error relacionado con el modelo LLM.
    
    Args:
        error (Exception): El error original
        detalles (dict, optional): Detalles adicionales del error
        
    Returns:
        dict: Información del error
    """
    llm_error = LLMError(str(error), detalles or {})
    return ErrorHandler.handle_error(llm_error, "LLM")


def handle_sql_error(error: Exception, detalles: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Maneja un error relacionado con SQL.
    
    Args:
        error (Exception): El error original
        detalles (dict, optional): Detalles adicionales del error
        
    Returns:
        dict: Información del error
    """
    sql_error = SQLError(str(error), detalles or {})
    return ErrorHandler.handle_error(sql_error, "SQL")


def handle_consulta_error(error: Exception, detalles: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Maneja un error relacionado con el análisis de consultas.
    
    Args:
        error (Exception): El error original
        detalles (dict, optional): Detalles adicionales del error
        
    Returns:
        dict: Información del error
    """
    consulta_error = ConsultaError(str(error), detalles or {})
    return ErrorHandler.handle_error(consulta_error, "CONSULTA")
