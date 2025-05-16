#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestor de caché inteligente para el asistente de agenda.
Este módulo proporciona una clase para almacenar y recuperar resultados
de consultas basándose en la estrategia generada por el LLM.
"""

import time
from typing import Dict, Any, Optional
from helpers.base_cache import BaseCache

class SmartLLMCache(BaseCache):
    """
    Caché inteligente que utiliza la estrategia generada por el LLM
    para identificar consultas similares y reutilizar resultados.
    """

    def __init__(self, max_size: int = 100, cache_file: str = "datos/cache.json"):
        """
        Inicializa el caché.

        Args:
            max_size (int): Tamaño máximo del caché
            cache_file (str): Ruta al archivo para persistir el caché
        """
        super().__init__(max_size, cache_file)

    def get_cache_key_from_strategy(self, estrategia: Dict[str, Any]) -> str:
        """
        Genera una clave de caché basada en la estrategia generada por el LLM.

        Args:
            estrategia (dict): Estrategia generada por el LLM

        Returns:
            str: Clave única para el caché
        """
        # Importar logger si está disponible
        try:
            from helpers.logger import Logger
            logger = Logger.get_logger()
            log_available = True
        except (ImportError, AttributeError):
            log_available = False

        # Extraer tipo de consulta y normalizarlo
        tipo_consulta_original = estrategia.get("tipo_consulta", "general")
        tipo_consulta = tipo_consulta_original.lower().strip()

        if log_available:
            logger.debug(f"Generando clave de caché. Tipo de consulta original: '{tipo_consulta_original}'")

        # Normalizar tipos de consulta similares
        tipo_consulta_normalizado = tipo_consulta
        if tipo_consulta in ["informacion", "información", "info"]:
            tipo_consulta_normalizado = "informacion"
        elif tipo_consulta in ["listado", "lista", "listar"]:
            tipo_consulta_normalizado = "listado"
        elif tipo_consulta in ["filtrado", "filtrar", "buscar"]:
            tipo_consulta_normalizado = "filtrado"
        elif tipo_consulta in ["conteo", "contar", "cuantos", "cuántos"]:
            tipo_consulta_normalizado = "conteo"

        if log_available and tipo_consulta != tipo_consulta_normalizado:
            logger.debug(f"Tipo de consulta normalizado: '{tipo_consulta}' -> '{tipo_consulta_normalizado}'")

        tipo_consulta = tipo_consulta_normalizado

        # Extraer nombres mencionados y normalizarlos
        nombres = []
        if "nombres_posibles" in estrategia and estrategia["nombres_posibles"]:
            if log_available:
                logger.debug(f"Nombres originales: {estrategia['nombres_posibles']}")

            # Normalizar nombres (quitar acentos, convertir a mayúsculas, eliminar espacios extra)
            nombres_normalizados = []
            for nombre in estrategia["nombres_posibles"]:
                if nombre:
                    # Normalizar nombre
                    nombre_norm = nombre.upper().strip()
                    nombre_original = nombre_norm  # Guardar para logging

                    # Quitar caracteres especiales y acentos comunes en español
                    for original, reemplazo in [
                        ('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U'),
                        ('Ñ', 'N'), ('.', ''), (',', ''), (';', ''), (':', '')
                    ]:
                        nombre_norm = nombre_norm.replace(original, reemplazo)

                    nombres_normalizados.append(nombre_norm)

                    if log_available and nombre_original != nombre_norm:
                        logger.debug(f"Nombre normalizado: '{nombre_original}' -> '{nombre_norm}'")

            nombres = sorted(nombres_normalizados)

            if log_available:
                logger.debug(f"Nombres normalizados y ordenados: {nombres}")
        else:
            if log_available:
                logger.debug("No se encontraron nombres en la estrategia")

        nombres_str = "|".join(nombres)

        if log_available:
            logger.debug(f"String de nombres para clave: '{nombres_str}'")

        # Extraer atributos solicitados y normalizarlos
        atributos = []
        if "atributos_solicitados" in estrategia and estrategia["atributos_solicitados"]:
            # Si se solicitan muchos atributos o incluye "todos", consideramos que es "información completa"
            atributos_lista = estrategia["atributos_solicitados"]
            if len(atributos_lista) > 5 or "todos" in [a.lower() for a in atributos_lista if a]:
                atributos = ["completo"]
            else:
                # Normalizar atributos
                atributos_normalizados = []
                for atributo in atributos_lista:
                    if atributo:
                        # Normalizar atributo
                        atributo_norm = atributo.lower().strip()
                        # Mapear atributos similares a un valor canónico
                        if atributo_norm in ["telefono", "teléfono", "celular", "móvil", "movil", "numero", "número"]:
                            atributo_norm = "telefono"
                        elif atributo_norm in ["correo", "email", "e-mail", "mail"]:
                            atributo_norm = "correo"
                        elif atributo_norm in ["direccion", "dirección", "domicilio", "ubicación", "ubicacion"]:
                            atributo_norm = "direccion"
                        elif atributo_norm in ["funcion", "función", "puesto", "cargo", "rol", "trabajo"]:
                            atributo_norm = "funcion"
                        atributos_normalizados.append(atributo_norm)

                atributos = sorted(set(atributos_normalizados))  # Eliminar duplicados

        atributos_str = "|".join(atributos)

        # Para consultas de información sobre una persona específica,
        # ignoramos las condiciones y usamos solo el tipo, nombres y atributos
        if tipo_consulta == "informacion" and nombres_str:
            if log_available:
                logger.debug("Generando clave para consulta de información personal")

            # Construir la clave simplificada para consultas de información
            key_parts = [tipo_consulta]
            key_parts.append(f"nombres={nombres_str}")
            if atributos_str:
                key_parts.append(f"atributos={atributos_str}")

            final_key = ":".join(key_parts)

            if log_available:
                logger.debug(f"Clave de caché generada: '{final_key}'")

            return final_key

        # Para otros tipos de consultas, incluimos las condiciones
        condiciones = []
        if "condiciones" in estrategia and estrategia["condiciones"]:
            if log_available:
                logger.debug(f"Condiciones originales: {estrategia['condiciones']}")

            for cond in estrategia["condiciones"]:
                if isinstance(cond, dict):
                    campo_original = cond.get("campo", "")
                    campo = campo_original.lower().strip() if campo_original else ""

                    valor_original = cond.get("valor", "")
                    valor = str(valor_original).lower().strip() if valor_original else ""

                    if log_available:
                        logger.debug(f"Procesando condición: campo='{campo}', valor='{valor}'")

                    # Normalizar campos
                    campo_normalizado = campo
                    if campo in ["zona", "área", "area", "sector"]:
                        campo_normalizado = "zona"
                    elif campo in ["funcion", "función", "puesto", "cargo", "rol"]:
                        campo_normalizado = "funcion"
                    elif campo in ["estado_civil", "estado civil", "civil"]:
                        campo_normalizado = "estado_civil"

                    if log_available and campo != campo_normalizado:
                        logger.debug(f"Campo normalizado: '{campo}' -> '{campo_normalizado}'")

                    campo = campo_normalizado

                    # Normalizar valores
                    valor_normalizado = valor
                    if campo == "estado_civil" and valor in ["casado", "casada", "matrimonio"]:
                        valor_normalizado = "casado"
                    elif campo == "estado_civil" and valor in ["soltero", "soltera"]:
                        valor_normalizado = "soltero"

                    if log_available and valor != valor_normalizado:
                        logger.debug(f"Valor normalizado: '{valor}' -> '{valor_normalizado}'")

                    valor = valor_normalizado

                    if campo and valor:
                        condicion_str = f"{campo}:{valor}"
                        condiciones.append(condicion_str)

                        if log_available:
                            logger.debug(f"Condición añadida: '{condicion_str}'")

        condiciones_str = "|".join(sorted(condiciones))

        if log_available:
            logger.debug(f"String de condiciones para clave: '{condiciones_str}'")

        # Construir la clave
        key_parts = [tipo_consulta]
        if nombres_str:
            key_parts.append(f"nombres={nombres_str}")
        if atributos_str:
            key_parts.append(f"atributos={atributos_str}")
        if condiciones_str:
            key_parts.append(f"condiciones={condiciones_str}")

        final_key = ":".join(key_parts)

        if log_available:
            logger.debug(f"Clave de caché generada: '{final_key}'")

        return final_key

    def get(self, estrategia: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Busca en el caché basado en la estrategia generada por el LLM.

        Args:
            estrategia (dict): Estrategia generada por el LLM

        Returns:
            dict: Resultado almacenado en caché o None si no se encuentra
        """
        cache_key = self.get_cache_key_from_strategy(estrategia)
        print(f"DEBUG: Buscando clave en caché: {cache_key}")
        print(f"DEBUG: Claves disponibles: {list(self.cache.keys())}")

        result = self.cache.get(cache_key)

        if result:
            print(f"DEBUG: ¡Encontrado en caché!")
            self.hits += 1
        else:
            print(f"DEBUG: No encontrado en caché")
            self.misses += 1

        return result

    def set(self, estrategia: Dict[str, Any], resultado: Dict[str, Any]) -> None:
        """
        Guarda un resultado en el caché.

        Args:
            estrategia (dict): Estrategia generada por el LLM
            resultado (dict): Resultado completo del procesamiento
        """
        cache_key = self.get_cache_key_from_strategy(estrategia)
        print(f"DEBUG: Guardando en caché con clave: {cache_key}")

        # Limitar el tamaño del caché si es necesario
        if len(self.cache) >= self.max_size:
            # Eliminar la entrada más antigua
            oldest_key = next(iter(self.cache))
            print(f"DEBUG: Eliminando entrada antigua: {oldest_key}")
            del self.cache[oldest_key]

        # Guardar el resultado
        self.cache[cache_key] = resultado

        # Guardar periódicamente en disco
        current_time = time.time()
        if current_time - self.last_save_time > 300:  # Cada 5 minutos
            self.save_to_disk()
            self.last_save_time = current_time

        print(f"DEBUG: Caché actualizado. Claves: {list(self.cache.keys())}")

    def _prepare_data_for_save(self) -> Dict[str, Any]:
        """
        Prepara los datos del caché para guardar en disco.

        Returns:
            dict: Datos preparados para guardar
        """
        # Solo guardar las respuestas finales para ahorrar espacio
        simplified_cache = {}
        for key, value in self.cache.items():
            simplified_cache[key] = {
                "respuesta": value["respuesta"],
                "resultado_sql": {
                    "total": value["resultado_sql"]["total"],
                    "registros": value["resultado_sql"]["registros"]
                }
            }

        # Guardar también metadatos del caché
        return {
            "metadata": {
                "version": "1.0",
                "timestamp": time.time(),
                "hits": self.hits,
                "misses": self.misses,
                "size": len(self.cache),
                "max_size": self.max_size
            },
            "cache": simplified_cache
        }

    def _get_entry_timestamp(self, entry: Dict[str, Any]) -> Optional[float]:
        """
        Obtiene el timestamp de una entrada del caché.

        Args:
            entry: Entrada del caché

        Returns:
            float: Timestamp de la entrada o None si no tiene
        """
        # Las entradas no tienen timestamp en este caché
        return None

    def _process_loaded_data(self, data: Dict[str, Any]) -> None:
        """
        Procesa los datos cargados desde disco.

        Args:
            data (dict): Datos cargados desde disco
        """
        # Verificar si es el nuevo formato con metadatos
        if isinstance(data, dict) and "cache" in data and "metadata" in data:
            self.cache = data["cache"]
            # Restaurar metadatos si están disponibles
            if "hits" in data["metadata"]:
                self.hits = data["metadata"]["hits"]
            if "misses" in data["metadata"]:
                self.misses = data["metadata"]["misses"]
        else:
            # Formato antiguo (solo el caché)
            self.cache = data

        print(f"DEBUG: Claves cargadas: {list(self.cache.keys())}")
