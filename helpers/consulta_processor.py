#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Procesador de consultas para el asistente de agenda.
Este módulo proporciona funciones auxiliares para procesar consultas
y manejar errores de manera consistente.
"""

import os
import json
import time
from typing import Dict, Any, Optional, Tuple
from colorama import Fore, Style

from config import DB_PATH
from helpers.error_handler import ErrorHandler, SQLError, ConsultaError, DatosError
from helpers.logger import Logger, log_consulta, log_respuesta, log_metrica, log_error
from helpers.semantic_cache import semantic_cache
from helpers.llm_search import (
    analizar_consulta,
    generar_sql_desde_estrategia,
    ejecutar_consulta_llm,
    evaluar_resultados,
    generar_respuesta_desde_resultados
)

# Obtener instancia del logger
logger = Logger.get_logger()

def _verificar_base_datos(db_path: str, debug: bool = False) -> Optional[Dict[str, Any]]:
    """
    Verifica que la base de datos existe.

    Args:
        db_path (str): Ruta a la base de datos
        debug (bool): Activar modo de depuración

    Returns:
        dict: Información de error si la base de datos no existe, None si existe
    """
    if not os.path.exists(db_path):
        error_info = ErrorHandler.handle_error(
            DatosError(f"La base de datos no existe en {db_path}."),
            "DATOS",
            mostrar_traceback=debug
        )
        log_error("Base de datos no encontrada", None, {"db_path": db_path})
        return {
            "error": error_info["mensaje"],
            "respuesta": ErrorHandler.get_user_message(error_info)
        }
    return None

def _analizar_consulta_con_manejo_errores(consulta: str, contexto: Optional[Dict[str, Any]], db_path: str, debug: bool = False) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Analiza la consulta y maneja posibles errores.

    Args:
        consulta (str): Consulta del usuario
        contexto (dict): Contexto de la conversación
        db_path (str): Ruta a la base de datos
        debug (bool): Activar modo de depuración

    Returns:
        tuple: (estrategia, error_info)
            - estrategia: Estrategia de búsqueda generada
            - error_info: Información de error si ocurrió alguno, None si no hubo errores
    """
    try:
        # Registrar inicio del análisis
        logger.info(f"Analizando consulta: '{consulta}'")

        # Analizar consulta
        estrategia = analizar_consulta(consulta, contexto, db_path)

        # Registrar estrategia generada
        logger.info(f"Estrategia generada para '{consulta}'")
        logger.debug(f"Detalles de estrategia: {json.dumps(estrategia, ensure_ascii=False)}")

        # Registrar información adicional
        if "clave_semantica" in estrategia:
            logger.info(f"Clave semántica generada: {estrategia['clave_semantica']}")

        if "nombres_posibles" in estrategia and estrategia["nombres_posibles"]:
            nombres = ", ".join(estrategia["nombres_posibles"])
            logger.info(f"Nombres identificados: {nombres}")
        else:
            logger.warning(f"No se identificaron nombres en la consulta: '{consulta}'")

        if "tipo_consulta" in estrategia:
            logger.info(f"Tipo de consulta: {estrategia.get('tipo_consulta', 'desconocido')}")

        if "atributos_solicitados" in estrategia and estrategia["atributos_solicitados"]:
            atributos = ", ".join(estrategia["atributos_solicitados"])
            logger.info(f"Atributos solicitados: {atributos}")

        # Verificar si hubo un error en el análisis
        if "error" in estrategia:
            error_info = ErrorHandler.handle_error(
                ConsultaError(estrategia["error"]),
                "CONSULTA",
                mostrar_traceback=debug
            )
            return estrategia, error_info

        return estrategia, None

    except Exception as e:
        error_info = ErrorHandler.handle_error(e, "CONSULTA", mostrar_traceback=debug)
        log_error("Error al analizar consulta", e, {"consulta": consulta})
        return {}, error_info

def _verificar_cache_semantico(estrategia: Dict[str, Any], consulta: str, tiempo_inicio: float, debug: bool = False) -> Optional[Dict[str, Any]]:
    """
    Verifica si hay un resultado en el caché semántico.

    Args:
        estrategia (dict): Estrategia de búsqueda
        consulta (str): Consulta original
        tiempo_inicio (float): Tiempo de inicio del procesamiento
        debug (bool): Activar modo de depuración

    Returns:
        dict: Resultado del caché si existe, None si no existe
    """
    # Verificar si hay clave semántica
    if "clave_semantica" not in estrategia:
        logger.warning("No se generó clave semántica para la consulta")
        return None

    # Verificar si hay un resultado en el caché semántico
    resultado_cache = semantic_cache.get(estrategia["clave_semantica"])
    if resultado_cache:
        if debug:
            print(f"DEBUG: ¡Resultado encontrado en caché semántico con clave: {estrategia['clave_semantica']}!")

        # Registrar hit de caché en métricas
        logger.info(f"¡Acierto en caché semántico! Consulta: '{consulta}'")
        log_metrica("semantic_cache_hit", 1, {"consulta": consulta, "clave_semantica": estrategia['clave_semantica']})

        # Registrar respuesta desde caché
        tiempo_ejecucion = time.time() - tiempo_inicio
        log_respuesta(consulta, resultado_cache["respuesta"], tiempo_ejecucion, True)

        # Añadir información de caché al resultado
        resultado_cache["from_semantic_cache"] = True

        return resultado_cache

    # Registrar miss de caché semántico
    logger.info(f"Fallo en caché semántico. Continuando procesamiento.")
    log_metrica("semantic_cache_miss", 1, {"consulta": consulta, "clave_semantica": estrategia['clave_semantica']})

    return None

# Función eliminada para simplificar el sistema de caché

def _generar_sql_con_manejo_errores(estrategia: Dict[str, Any], consulta: str, db_path: str, debug: bool = False) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Genera una consulta SQL a partir de la estrategia y maneja posibles errores.

    Args:
        estrategia (dict): Estrategia de búsqueda
        consulta (str): Consulta original
        db_path (str): Ruta a la base de datos
        debug (bool): Activar modo de depuración

    Returns:
        tuple: (consulta_sql, error_info)
            - consulta_sql: Consulta SQL generada
            - error_info: Información de error si ocurrió alguno, None si no hubo errores
    """
    try:
        # Registrar inicio de generación SQL
        logger.info(f"Generando SQL para consulta: '{consulta}'")

        # Generar SQL
        consulta_sql = generar_sql_desde_estrategia(estrategia, db_path)

        # Registrar SQL generado
        if "consulta" in consulta_sql:
            logger.info(f"SQL generado: {consulta_sql['consulta']}")
            if "parametros" in consulta_sql and consulta_sql["parametros"]:
                logger.info(f"Parámetros SQL: {json.dumps(consulta_sql['parametros'], ensure_ascii=False)}")
        else:
            logger.warning("No se generó consulta SQL")

        # Verificar si hubo un error en la generación de SQL
        if "error" in consulta_sql:
            error_info = ErrorHandler.handle_error(
                SQLError(consulta_sql["error"]),
                "SQL",
                mostrar_traceback=debug
            )
            return consulta_sql, error_info

        if debug:
            print("DEBUG: Consulta SQL generada:")
            print(consulta_sql.get("consulta", "Error: No se generó consulta SQL"))
            if consulta_sql.get("parametros"):
                print("DEBUG: Parámetros SQL:")
                print(consulta_sql["parametros"])

        return consulta_sql, None

    except Exception as e:
        error_info = ErrorHandler.handle_error(e, "SQL", mostrar_traceback=debug)
        log_error("Error al generar SQL", e, {"estrategia": estrategia})
        return {}, error_info

def _ejecutar_sql_con_manejo_errores(consulta_sql: Dict[str, Any], consulta: str, estrategia: Dict[str, Any], db_path: str, debug: bool = False) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Ejecuta una consulta SQL y maneja posibles errores.

    Args:
        consulta_sql (dict): Consulta SQL a ejecutar
        consulta (str): Consulta original
        estrategia (dict): Estrategia de búsqueda
        db_path (str): Ruta a la base de datos
        debug (bool): Activar modo de depuración

    Returns:
        tuple: (resultado_sql, error_info)
            - resultado_sql: Resultado de la ejecución SQL
            - error_info: Información de error si ocurrió alguno, None si no hubo errores
    """
    try:
        # Registrar inicio de ejecución SQL
        logger.info(f"Ejecutando SQL: {consulta_sql['consulta']}")

        # Ejecutar SQL
        resultado_sql = ejecutar_consulta_llm(consulta_sql["consulta"], consulta_sql["parametros"], db_path)

        # Registrar resultados obtenidos
        if "total" in resultado_sql:
            logger.info(f"Resultados encontrados: {resultado_sql['total']}")
            if resultado_sql["total"] > 0:
                # Registrar primer resultado como muestra
                if "registros" in resultado_sql and resultado_sql["registros"]:
                    primer_registro = resultado_sql["registros"][0]
                    logger.info(f"Muestra de resultado: {json.dumps(primer_registro, ensure_ascii=False)}")
            else:
                logger.warning(f"No se encontraron resultados para la consulta: '{consulta}'")

        # Verificar si hubo un error en la ejecución
        if resultado_sql.get("error"):
            error_info = ErrorHandler.handle_error(
                SQLError(resultado_sql["error"]),
                "SQL",
                mostrar_traceback=debug
            )
            return resultado_sql, error_info

        if debug:
            print("DEBUG: Resultados SQL:")
            print(f"Total: {resultado_sql['total']} registros")
            if resultado_sql["total"] > 0 and resultado_sql["total"] <= 3:
                print(json.dumps(resultado_sql["registros"], indent=2, ensure_ascii=False))
            elif resultado_sql["total"] > 3:
                print(json.dumps(resultado_sql["registros"][:3], indent=2, ensure_ascii=False))
                print(f"... y {resultado_sql['total'] - 3} más")

        # Registrar métrica de resultados encontrados
        log_metrica("resultados_encontrados", resultado_sql["total"], {
            "tipo_consulta": estrategia.get("tipo_consulta", "general")
        })

        return resultado_sql, None

    except Exception as e:
        error_info = ErrorHandler.handle_error(e, "SQL", mostrar_traceback=debug)
        log_error("Error al ejecutar SQL", e, {
            "consulta_sql": consulta_sql["consulta"],
            "parametros": consulta_sql["parametros"]
        })
        return {}, error_info

def _evaluar_resultados_con_manejo_errores(consulta: str, resultado_sql: Dict[str, Any], estrategia: Dict[str, Any], db_path: str, debug: bool = False) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Evalúa los resultados de una consulta SQL y maneja posibles errores.

    Args:
        consulta (str): Consulta original
        resultado_sql (dict): Resultado de la ejecución SQL
        estrategia (dict): Estrategia de búsqueda
        db_path (str): Ruta a la base de datos
        debug (bool): Activar modo de depuración

    Returns:
        tuple: (evaluacion, error_info)
            - evaluacion: Evaluación de los resultados
            - error_info: Información de error si ocurrió alguno, None si no hubo errores
    """
    try:
        # Registrar inicio de evaluación
        logger.info(f"Evaluando resultados para consulta: '{consulta}'")

        # Evaluar resultados
        evaluacion = evaluar_resultados(consulta, resultado_sql, estrategia, db_path)

        # Registrar resultado de la evaluación
        if "satisfactorio" in evaluacion:
            logger.info(f"Evaluación: {'Satisfactoria' if evaluacion['satisfactorio'] else 'No satisfactoria'}")
            if "evaluacion" in evaluacion:
                logger.info(f"Detalle de evaluación: {evaluacion['evaluacion']}")
        else:
            logger.warning("Evaluación incompleta")

        if debug:
            print("DEBUG: Evaluación de resultados:")
            print(json.dumps(evaluacion, indent=2, ensure_ascii=False))

        return evaluacion, None

    except Exception as e:
        # Manejar el error pero continuar con una evaluación básica
        ErrorHandler.handle_error(e, "EVALUACION", mostrar_traceback=debug)
        log_error("Error al evaluar resultados", e, {"resultado_sql": resultado_sql})

        # En caso de error en la evaluación, continuamos con una evaluación básica
        evaluacion = {
            "satisfactorio": resultado_sql["total"] > 0,
            "evaluacion": "No se pudo evaluar completamente los resultados."
        }
        logger.warning("Se utilizó evaluación básica debido a un error")

        return evaluacion, None  # No devolvemos error_info para continuar con la evaluación básica

def _intentar_refinamiento_automatico(consulta: str, contexto: Optional[Dict[str, Any]], estrategia: Dict[str, Any], evaluacion: Dict[str, Any], resultado_sql: Dict[str, Any], db_path: str, debug: bool = False, max_refinamientos: int = 1) -> Optional[Dict[str, Any]]:
    """
    Intenta un refinamiento automático de la consulta si los resultados no son satisfactorios.

    Args:
        consulta (str): Consulta original
        contexto (dict): Contexto de la conversación
        estrategia (dict): Estrategia de búsqueda original
        evaluacion (dict): Evaluación de los resultados
        resultado_sql (dict): Resultado de la ejecución SQL
        db_path (str): Ruta a la base de datos
        debug (bool): Activar modo de depuración
        max_refinamientos (int): Número máximo de refinamientos a intentar

    Returns:
        dict: Resultado refinado si el refinamiento tuvo éxito, None si no
    """
    # Verificar si hay una nueva estrategia sugerida y si debemos intentar un refinamiento
    if (not evaluacion.get("satisfactorio", False) and
        "refinamiento" in evaluacion and
        "nueva_estrategia" in evaluacion["refinamiento"] and
        max_refinamientos > 0 and
        resultado_sql["total"] == 0):

        nueva_estrategia = evaluacion["refinamiento"]["nueva_estrategia"]

        if nueva_estrategia:
            logger.info(f"Intentando refinamiento automático (quedan {max_refinamientos} intentos)")
            if debug:
                print(f"\n{Fore.YELLOW}DEBUG: Intentando refinamiento automático (quedan {max_refinamientos} intentos){Style.RESET_ALL}")
                print(f"DEBUG: Nueva estrategia: {json.dumps(nueva_estrategia, indent=2, ensure_ascii=False)}")

            # Llamar recursivamente a la función actual con la nueva estrategia y un intento menos
            resultado_refinado = procesar_consulta(
                consulta,
                contexto,
                db_path,
                debug,
                max_refinamientos - 1
            )

            # Si el refinamiento tuvo éxito (encontró resultados), usarlo
            if resultado_refinado.get("resultado_sql", {}).get("total", 0) > 0:
                logger.info(f"Refinamiento automático exitoso: {resultado_refinado['resultado_sql']['total']} resultados encontrados")
                if debug:
                    print(f"\n{Fore.GREEN}DEBUG: Refinamiento automático exitoso: {resultado_refinado['resultado_sql']['total']} resultados encontrados{Style.RESET_ALL}")

                # Añadir información sobre el refinamiento
                resultado_refinado["refinamiento_automatico"] = True
                resultado_refinado["estrategia_original"] = estrategia
                resultado_refinado["evaluacion_original"] = evaluacion

                # Registrar métrica de refinamiento exitoso
                log_metrica("refinamiento_exitoso", 1, {
                    "consulta": consulta,
                    "resultados_originales": resultado_sql["total"],
                    "resultados_refinados": resultado_refinado["resultado_sql"]["total"]
                })

                return resultado_refinado
            else:
                logger.warning("Refinamiento automático no encontró resultados")
                if debug:
                    print(f"\n{Fore.YELLOW}DEBUG: Refinamiento automático no encontró resultados{Style.RESET_ALL}")

                # Registrar métrica de refinamiento fallido
                log_metrica("refinamiento_fallido", 1, {
                    "consulta": consulta
                })

    return None

def _generar_respuesta_con_manejo_errores(consulta: str, resultado_sql: Dict[str, Any], estrategia: Dict[str, Any], evaluacion: Dict[str, Any], db_path: str, debug: bool = False) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Genera una respuesta natural a partir de los resultados y maneja posibles errores.

    Args:
        consulta (str): Consulta original
        resultado_sql (dict): Resultado de la ejecución SQL
        estrategia (dict): Estrategia de búsqueda
        evaluacion (dict): Evaluación de los resultados
        db_path (str): Ruta a la base de datos
        debug (bool): Activar modo de depuración

    Returns:
        tuple: (respuesta, error_info)
            - respuesta: Respuesta generada
            - error_info: Información de error si ocurrió alguno, None si no hubo errores
    """
    try:
        # Registrar inicio de generación de respuesta
        logger.info(f"Generando respuesta para consulta: '{consulta}'")

        # Generar respuesta
        respuesta = generar_respuesta_desde_resultados(consulta, resultado_sql, estrategia, evaluacion, db_path)

        # Registrar respuesta generada (versión resumida para el log)
        respuesta_resumida = respuesta[:100] + "..." if len(respuesta) > 100 else respuesta
        logger.info(f"Respuesta generada: {respuesta_resumida}")

        # Registrar longitud de la respuesta como métrica
        log_metrica("longitud_respuesta", len(respuesta), {
            "tipo_consulta": estrategia.get("tipo_consulta", "general"),
            "resultados": resultado_sql["total"]
        })

        return respuesta, None

    except Exception as e:
        error_info = ErrorHandler.handle_error(e, "RESPUESTA", mostrar_traceback=debug)
        log_error("Error al generar respuesta", e, {"evaluacion": evaluacion})

        # En caso de error, generamos una respuesta más informativa basada en los resultados SQL
        if resultado_sql["total"] > 0:
            # Intentar generar una respuesta básica pero informativa basada en los datos
            try:
                # Obtener el primer resultado
                primer_resultado = resultado_sql["registros"][0]

                # Determinar qué tipo de información se solicitó
                if "tipo_consulta" in estrategia and estrategia["tipo_consulta"] == "informacion":
                    # Obtener los atributos solicitados
                    atributos = estrategia.get("atributos_solicitados", [])

                    # Construir una respuesta básica con la información disponible
                    if atributos and all(attr in primer_resultado for attr in atributos):
                        # Obtener el nombre de la persona
                        nombre = primer_resultado.get("nombre_completo", "")
                        if nombre:
                            # Convertir de "APELLIDO APELLIDO NOMBRE" a "Nombre Apellido Apellido"
                            partes = nombre.split()
                            if len(partes) >= 3:
                                nombre_formateado = f"{partes[-1]} {' '.join(partes[:-1])}"
                                nombre_formateado = nombre_formateado.title()
                            else:
                                nombre_formateado = nombre.title()

                            # Construir respuesta con los valores de los atributos
                            valores = []
                            for attr in atributos:
                                if attr in primer_resultado and primer_resultado[attr]:
                                    valores.append(f"{attr.replace('_', ' ').title()}: {primer_resultado[attr]}")

                            if valores:
                                respuesta = f"Encontré la siguiente información para {nombre_formateado}: {', '.join(valores)}."
                            else:
                                respuesta = f"Encontré información para {nombre_formateado}, pero no puedo mostrar los detalles específicos que solicitaste."
                        else:
                            respuesta = f"Encontré {resultado_sql['total']} resultados para tu consulta, pero tuve problemas al generar una respuesta detallada."
                    else:
                        respuesta = f"Encontré {resultado_sql['total']} resultados para tu consulta, pero tuve problemas al generar una respuesta detallada."
                else:
                    respuesta = f"Encontré {resultado_sql['total']} resultados para tu consulta, pero tuve problemas al generar una respuesta detallada."
            except Exception as inner_e:
                # Si hay algún error al generar la respuesta básica, usar el mensaje genérico
                logger.error(f"Error al generar respuesta básica: {str(inner_e)}")
                respuesta = f"Encontré {resultado_sql['total']} resultados para tu consulta, pero tuve problemas al generar una respuesta detallada."
        else:
            respuesta = "No encontré resultados para tu consulta. ¿Podrías intentar con otra búsqueda?"

        logger.warning(f"Se generó respuesta básica debido a un error: {respuesta}")

        return respuesta, error_info

def _guardar_en_cache(estrategia: Dict[str, Any], resultado: Dict[str, Any], debug: bool = False) -> None:
    """
    Guarda el resultado en el caché semántico.

    Args:
        estrategia (dict): Estrategia de búsqueda
        resultado (dict): Resultado completo del procesamiento
        debug (bool): Activar modo de depuración
    """
    # Guardar en caché semántico si hay clave semántica
    if "clave_semantica" in estrategia:
        logger.info(f"Guardando resultado en caché semántico con clave: {estrategia['clave_semantica']}")
        semantic_cache.set(estrategia["clave_semantica"], resultado)

        # Verificar que se guardó correctamente
        semantic_cache_stats = semantic_cache.get_stats()
        logger.info(f"Estadísticas del caché semántico después de guardar: {json.dumps(semantic_cache_stats, ensure_ascii=False)}")

        if debug:
            print(f"DEBUG: Resultado guardado en caché semántico. Estadísticas: {semantic_cache.get_stats()}")
    else:
        logger.warning("No se pudo guardar en caché: no hay clave semántica en la estrategia")

def procesar_consulta(consulta: str, contexto: Optional[Dict[str, Any]] = None, db_path: str = DB_PATH, debug: bool = False, max_refinamientos: int = 1) -> Dict[str, Any]:
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
    # Iniciar temporizador para medir tiempo de ejecución
    tiempo_inicio = time.time()

    # Registrar la consulta en el log
    log_consulta(consulta, contexto)

    try:
        # Paso 0: Verificar que la base de datos existe
        error_db = _verificar_base_datos(db_path, debug)
        if error_db:
            error_db["consulta"] = consulta
            return error_db

        # Paso 1: Analizar la consulta y generar una estrategia de búsqueda
        estrategia, error_analisis = _analizar_consulta_con_manejo_errores(consulta, contexto, db_path, debug)
        if error_analisis:
            return {
                "error": error_analisis["mensaje"],
                "respuesta": ErrorHandler.get_user_message(error_analisis),
                "consulta": consulta
            }

        if debug:
            print("DEBUG: Estrategia de búsqueda:")
            print(json.dumps(estrategia, indent=2, ensure_ascii=False))

        # Paso 2: Verificar caché semántico
        resultado_cache_semantico = _verificar_cache_semantico(estrategia, consulta, tiempo_inicio, debug)
        if resultado_cache_semantico:
            return resultado_cache_semantico

        # Paso 4: Generar consulta SQL
        consulta_sql, error_sql = _generar_sql_con_manejo_errores(estrategia, consulta, db_path, debug)
        if error_sql:
            return {
                "error": error_sql["mensaje"],
                "respuesta": ErrorHandler.get_user_message(error_sql),
                "consulta": consulta,
                "estrategia": estrategia
            }

        # Paso 5: Ejecutar consulta SQL
        resultado_sql, error_ejecucion = _ejecutar_sql_con_manejo_errores(consulta_sql, consulta, estrategia, db_path, debug)
        if error_ejecucion:
            return {
                "error": error_ejecucion["mensaje"],
                "respuesta": ErrorHandler.get_user_message(error_ejecucion),
                "consulta": consulta,
                "estrategia": estrategia,
                "consulta_sql": consulta_sql
            }

        # Paso 6: Evaluar resultados
        evaluacion, _ = _evaluar_resultados_con_manejo_errores(consulta, resultado_sql, estrategia, db_path, debug)

        # Paso 7: Intentar refinamiento automático si es necesario
        resultado_refinado = _intentar_refinamiento_automatico(
            consulta, contexto, estrategia, evaluacion, resultado_sql,
            db_path, debug, max_refinamientos
        )
        if resultado_refinado:
            return resultado_refinado

        # Paso 8: Generar respuesta natural
        respuesta, error_respuesta = _generar_respuesta_con_manejo_errores(
            consulta, resultado_sql, estrategia, evaluacion, db_path, debug
        )
        if error_respuesta:
            return {
                "error": error_respuesta["mensaje"],
                "respuesta": respuesta,  # Usamos la respuesta básica generada
                "consulta": consulta,
                "estrategia": estrategia,
                "consulta_sql": consulta_sql,
                "resultado_sql": resultado_sql,
                "evaluacion": evaluacion
            }

        # Construir el resultado completo
        resultado = {
            "consulta": consulta,
            "estrategia": estrategia,
            "consulta_sql": consulta_sql,
            "resultado_sql": resultado_sql,
            "evaluacion": evaluacion,
            "respuesta": respuesta,
            "error": None
        }

        # Paso 9: Guardar en caché
        _guardar_en_cache(estrategia, resultado, debug)

        # Registrar respuesta final
        tiempo_ejecucion = time.time() - tiempo_inicio
        log_respuesta(consulta, respuesta, tiempo_ejecucion, False)

        return resultado

    except Exception as e:
        # Manejar cualquier error no capturado
        error_info = ErrorHandler.handle_error(e, "GENERAL", mostrar_traceback=debug)
        log_error("Error general al procesar consulta", e, {"consulta": consulta})

        return {
            "error": error_info["mensaje"],
            "respuesta": ErrorHandler.get_user_message(error_info),
            "consulta": consulta
        }
