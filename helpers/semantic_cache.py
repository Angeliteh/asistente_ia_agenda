#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Caché semántico para el asistente de agenda.
Este módulo implementa un sistema de caché basado en claves semánticas
generadas por el LLM para almacenar y recuperar resultados de consultas.
"""

import os
import time
from typing import Dict, Any, Optional
from helpers.base_cache import BaseCache
from helpers.llm_normalizer import normalizar_clave_con_llm
from config import SEMANTIC_CACHE_ENABLED, SEMANTIC_CACHE_MAX_SIZE, SEMANTIC_CACHE_FILE

# Ruta por defecto para el archivo de caché (usar la configuración si está disponible)
DEFAULT_CACHE_PATH = SEMANTIC_CACHE_FILE

class SemanticCache(BaseCache):
    """
    Implementa un sistema de caché basado en claves semánticas generadas por el LLM.
    Permite almacenar y recuperar resultados de consultas similares sin necesidad
    de volver a consultar la base de datos.
    """

    def __init__(self, cache_path: str = DEFAULT_CACHE_PATH, max_size: int = SEMANTIC_CACHE_MAX_SIZE, ttl: int = 86400):
        """
        Inicializa el caché semántico.

        Args:
            cache_path (str): Ruta al archivo de caché
            max_size (int): Tamaño máximo del caché (número de entradas)
            ttl (int): Tiempo de vida de las entradas en segundos (por defecto: 1 día)
        """
        super().__init__(max_size, cache_path, ttl)

        # Bandera para indicar si el caché está habilitado
        self.enabled = SEMANTIC_CACHE_ENABLED

        # Cargar caché existente si existe y está habilitado
        if self.enabled:
            self.load_from_disk()
            print(f"Caché semántico inicializado y habilitado. Tamaño máximo: {max_size} entradas.")
        else:
            print("Caché semántico inicializado pero DESHABILITADO. Las consultas no se almacenarán en caché.")

    def get(self, clave_semantica: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un resultado del caché usando la clave semántica.

        Args:
            clave_semantica (str): Clave semántica generada por el LLM

        Returns:
            dict: Resultado almacenado en caché, o None si no existe
        """
        # Si el caché está deshabilitado, siempre devolver None
        if not self.enabled:
            self.misses += 1
            return None

        # Normalizar clave
        clave = self._normalizar_clave(clave_semantica)

        # Verificar si existe en caché
        if clave in self.cache:
            # Verificar si ha expirado
            entry = self.cache[clave]
            if "timestamp" in entry and time.time() - entry["timestamp"] > self.ttl:
                # Entrada expirada, eliminarla
                del self.cache[clave]
                self.misses += 1
                return None

            # Actualizar estadísticas
            self.hits += 1

            # Actualizar timestamp para mantener la entrada "fresca"
            self.cache[clave]["timestamp"] = time.time()

            return self.cache[clave]["data"]

        # No encontrado en caché
        self.misses += 1
        return None

    def set(self, clave_semantica: str, data: Dict[str, Any]) -> None:
        """
        Guarda un resultado en el caché usando la clave semántica.

        Args:
            clave_semantica (str): Clave semántica generada por el LLM
            data (dict): Datos a almacenar en caché
        """
        # Si el caché está deshabilitado, no hacer nada
        if not self.enabled:
            return

        # Normalizar clave
        clave = self._normalizar_clave(clave_semantica)

        # Guardar en caché con timestamp
        self.cache[clave] = {
            "data": data,
            "timestamp": time.time()
        }

        # Verificar si es momento de guardar en disco
        self._check_save_to_disk()

    def _get_entry_timestamp(self, entry: Any) -> Optional[float]:
        """
        Obtiene el timestamp de una entrada del caché.

        Args:
            entry: Entrada del caché

        Returns:
            float: Timestamp de la entrada o None si no tiene
        """
        if isinstance(entry, dict) and "timestamp" in entry:
            return entry["timestamp"]
        return None

    def _prepare_data_for_save(self) -> Dict[str, Any]:
        """
        Prepara los datos del caché para guardar en disco.

        Returns:
            dict: Datos preparados para guardar
        """
        return {
            "metadata": {
                "version": "1.0",
                "timestamp": time.time(),
                "size": len(self.cache),
                "hits": self.hits,
                "misses": self.misses
            },
            "entries": self.cache
        }

    def _process_loaded_data(self, data: Dict[str, Any]) -> None:
        """
        Procesa los datos cargados desde disco.

        Args:
            data (dict): Datos cargados desde disco
        """
        try:
            # Verificar formato
            if isinstance(data, dict) and "entries" in data:
                # Formato estándar
                self.cache = data["entries"]

                # Cargar estadísticas si existen
                if "metadata" in data:
                    self.hits = data["metadata"].get("hits", 0)
                    self.misses = data["metadata"].get("misses", 0)

                print(f"DEBUG: Caché semántico cargado desde disco: {len(self.cache)} entradas")
            elif isinstance(data, dict) and any(isinstance(v, dict) for v in data.values()):
                # Formato alternativo (diccionario de entradas sin metadata)
                print("ADVERTENCIA: Formato de caché no estándar, intentando reparar")
                self.cache = data
                print(f"DEBUG: Caché semántico reparado: {len(self.cache)} entradas")
            else:
                # Formato desconocido
                print("ERROR: Formato de caché inválido, inicializando vacío")
                self.cache = {}

            # Limpiar entradas expiradas
            self._clean_expired_entries()
        except Exception as e:
            # En caso de cualquier error, inicializar vacío
            print(f"ERROR: Error al procesar datos del caché: {str(e)}")
            self.cache = {}

    def _normalizar_clave(self, clave: str) -> str:
        """
        Normaliza una clave semántica para comparaciones consistentes utilizando LLM.

        Args:
            clave (str): Clave semántica original

        Returns:
            str: Clave normalizada
        """
        # Usar el LLM para normalizar la clave
        return normalizar_clave_con_llm(clave)

    def save_to_disk(self) -> bool:
        """
        Guarda el caché en disco si está habilitado.

        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        if not self.enabled:
            print("DEBUG: Caché semántico deshabilitado, no se guardará en disco")
            return False

        return super().save_to_disk()

    def load_from_disk(self) -> bool:
        """
        Carga el caché desde disco si está habilitado.

        Returns:
            bool: True si se cargó correctamente, False en caso contrario
        """
        if not self.enabled:
            print("DEBUG: Caché semántico deshabilitado, no se cargará desde disco")
            return False

        return super().load_from_disk()

# Instancia global del caché
semantic_cache = SemanticCache()
