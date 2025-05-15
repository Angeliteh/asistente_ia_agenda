#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Utilidades para interactuar con modelos LLM.
Este módulo proporciona funciones comunes para llamar a los modelos LLM
y procesar sus respuestas, incluyendo manejo de fallback entre modelos.
"""

import json
from colorama import Fore, Style
import google.generativeai as genai
from config import (
    LLM_PRIMARY_MODEL,
    LLM_FALLBACK_MODEL,
    LLM_TEMPERATURE,
    LLM_TOP_P,
    LLM_TOP_K,
    LLM_MAX_TOKENS,
    LLM_FALLBACK_MAX_TOKENS,
    LLM_SAFETY_SETTINGS
)

def llamar_llm(prompt, max_output_tokens=None, safety_settings=None):
    """
    Función común para llamar al LLM con fallback automático.

    Args:
        prompt (str): El prompt a enviar al modelo
        max_output_tokens (int, optional): Límite de tokens de salida
        safety_settings (list, optional): Configuración de seguridad

    Returns:
        object: Respuesta del modelo
    """
    # Usar configuración de seguridad predeterminada si no se proporciona
    if safety_settings is None:
        safety_settings = LLM_SAFETY_SETTINGS

    # Establecer límite de tokens predeterminado si no se proporciona
    if max_output_tokens is None:
        max_output_tokens = LLM_MAX_TOKENS

    try:
        modelo = genai.GenerativeModel(model_name=LLM_PRIMARY_MODEL)

        # Configurar el modelo para evitar repeticiones y respuestas más coherentes
        generation_config = {
            "temperature": LLM_TEMPERATURE,
            "top_p": LLM_TOP_P,
            "top_k": LLM_TOP_K,
            "max_output_tokens": max_output_tokens
        }

        respuesta = modelo.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        print(f"{Fore.GREEN}✓ Usando modelo: {LLM_PRIMARY_MODEL}{Style.RESET_ALL}")
        return respuesta
    except Exception as e:
        print(f"{Fore.YELLOW}⚠ Error con {LLM_PRIMARY_MODEL}: {str(e)}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⚠ Intentando con modelo alternativo: {LLM_FALLBACK_MODEL}{Style.RESET_ALL}")

        modelo = genai.GenerativeModel(model_name=LLM_FALLBACK_MODEL)
        generation_config = {
            "temperature": LLM_TEMPERATURE,
            "top_p": LLM_TOP_P,
            "top_k": LLM_TOP_K,
            "max_output_tokens": min(max_output_tokens, LLM_FALLBACK_MAX_TOKENS)
        }

        respuesta = modelo.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        print(f"{Fore.GREEN}✓ Usando modelo: {LLM_FALLBACK_MODEL}{Style.RESET_ALL}")
        return respuesta

def parsear_respuesta_json(respuesta):
    """
    Función común para parsear respuestas JSON del LLM.

    Args:
        respuesta (object): Respuesta del modelo

    Returns:
        dict: Objeto JSON parseado o diccionario con error
    """
    try:
        texto_respuesta = respuesta.text.strip()
        if "```json" in texto_respuesta:
            texto_respuesta = texto_respuesta.split("```json")[1].split("```")[0].strip()
        elif "```" in texto_respuesta:
            texto_respuesta = texto_respuesta.split("```")[1].strip()

        return json.loads(texto_respuesta)
    except Exception as e:
        print(f"Error al parsear respuesta JSON: {e}")
        print(f"Respuesta recibida: {respuesta.text}")
        return {
            "error": str(e),
            "respuesta_original": respuesta.text
        }

def generar_respuesta_texto(prompt, max_output_tokens=None, safety_settings=None):
    """
    Genera una respuesta de texto utilizando el LLM.

    Args:
        prompt (str): El prompt a enviar al modelo
        max_output_tokens (int, optional): Límite de tokens de salida
        safety_settings (list, optional): Configuración de seguridad

    Returns:
        str: Texto de la respuesta generada
    """
    # Usar valores predeterminados de la configuración si no se proporcionan
    if max_output_tokens is None:
        max_output_tokens = LLM_MAX_TOKENS

    if safety_settings is None:
        safety_settings = LLM_SAFETY_SETTINGS

    respuesta = llamar_llm(prompt, max_output_tokens, safety_settings)
    return respuesta.text.strip()
