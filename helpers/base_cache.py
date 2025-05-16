#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Clase base para sistemas de caché del asistente de agenda.
Este módulo proporciona una clase base con funcionalidad común para
diferentes implementaciones de caché, reduciendo la duplicación de código.
"""

import json
import os
import time
from typing import Dict, Any, Optional, List, Union

class BaseCache:
    """
    Clase base para sistemas de caché con funcionalidad común.
    Implementa métodos para estadísticas, persistencia y limpieza.
    """
    
    def __init__(self, max_size: int = 100, cache_file: str = None, ttl: Optional[int] = None):
        """
        Inicializa el caché base.
        
        Args:
            max_size (int): Tamaño máximo del caché (número de entradas)
            cache_file (str): Ruta al archivo para persistir el caché
            ttl (int, optional): Tiempo de vida de las entradas en segundos
        """
        self.cache = {}
        self.max_size = max_size
        self.cache_file = cache_file
        self.ttl = ttl
        self.hits = 0
        self.misses = 0
        self.last_save_time = time.time()
        self.save_interval = 300  # 5 minutos (intervalo de guardado por defecto)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.
        
        Returns:
            dict: Estadísticas del caché (tamaño, hits, misses, etc.)
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total) * 100 if total > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": f"{hit_rate:.2f}%"
        }
    
    def save_to_disk(self) -> bool:
        """
        Guarda el caché en disco.
        
        Returns:
            bool: True si se guardó correctamente, False en caso contrario
        """
        if not self.cache_file:
            print("DEBUG: No se especificó archivo de caché")
            return False
        
        try:
            # Asegurarse de que el directorio existe
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
            
            # Preparar datos para guardar
            cache_data = self._prepare_data_for_save()
            
            # Guardar en archivo
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            self.last_save_time = time.time()
            
            print(f"DEBUG: Caché guardado en disco: {self.cache_file}")
            return True
        except Exception as e:
            print(f"ERROR: No se pudo guardar el caché en disco: {str(e)}")
            return False
    
    def load_from_disk(self) -> bool:
        """
        Carga el caché desde disco.
        
        Returns:
            bool: True si se cargó correctamente, False en caso contrario
        """
        if not self.cache_file or not os.path.exists(self.cache_file):
            print(f"DEBUG: No existe archivo de caché en {self.cache_file}")
            return False
        
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Procesar datos cargados
            self._process_loaded_data(data)
            
            print(f"DEBUG: Caché cargado desde disco: {self.cache_file}")
            return True
        except Exception as e:
            print(f"ERROR: No se pudo cargar el caché desde disco: {str(e)}")
            return False
    
    def clear(self) -> None:
        """Limpia el caché."""
        self.cache = {}
        self.hits = 0
        self.misses = 0
        if self.cache_file and os.path.exists(self.cache_file):
            try:
                os.remove(self.cache_file)
                print(f"DEBUG: Archivo de caché eliminado: {self.cache_file}")
            except Exception as e:
                print(f"ERROR: No se pudo eliminar el archivo de caché: {str(e)}")
    
    def _clean_expired_entries(self) -> None:
        """
        Limpia entradas expiradas del caché.
        Solo aplicable si se ha configurado un TTL.
        """
        if not self.ttl:
            return
        
        now = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            timestamp = self._get_entry_timestamp(entry)
            if timestamp and now - timestamp > self.ttl:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            print(f"DEBUG: Se eliminaron {len(expired_keys)} entradas expiradas del caché")
    
    def _prepare_data_for_save(self) -> Dict[str, Any]:
        """
        Prepara los datos del caché para guardar en disco.
        Este método debe ser sobrescrito por las clases derivadas.
        
        Returns:
            dict: Datos preparados para guardar
        """
        return {
            "metadata": {
                "version": "1.0",
                "timestamp": time.time(),
                "hits": self.hits,
                "misses": self.misses,
                "size": len(self.cache),
                "max_size": self.max_size,
                "ttl": self.ttl
            },
            "entries": self.cache
        }
    
    def _process_loaded_data(self, data: Dict[str, Any]) -> None:
        """
        Procesa los datos cargados desde disco.
        Este método debe ser sobrescrito por las clases derivadas.
        
        Args:
            data (dict): Datos cargados desde disco
        """
        # Verificar formato
        if isinstance(data, dict) and "entries" in data:
            self.cache = data["entries"]
            
            # Cargar metadatos si existen
            if "metadata" in data:
                metadata = data["metadata"]
                if "hits" in metadata:
                    self.hits = metadata["hits"]
                if "misses" in metadata:
                    self.misses = metadata["misses"]
            
            # Limpiar entradas expiradas
            self._clean_expired_entries()
        else:
            # Formato antiguo (solo el caché)
            self.cache = data
    
    def _get_entry_timestamp(self, entry: Any) -> Optional[float]:
        """
        Obtiene el timestamp de una entrada del caché.
        Este método debe ser sobrescrito por las clases derivadas.
        
        Args:
            entry: Entrada del caché
            
        Returns:
            float: Timestamp de la entrada o None si no tiene
        """
        # Implementación por defecto para entradas con formato
        # {"timestamp": 123456789, "data": {...}}
        if isinstance(entry, dict) and "timestamp" in entry:
            return entry["timestamp"]
        return None
    
    def _should_save_to_disk(self) -> bool:
        """
        Determina si se debe guardar el caché en disco.
        
        Returns:
            bool: True si se debe guardar, False en caso contrario
        """
        return (
            self.cache_file is not None and 
            time.time() - self.last_save_time > self.save_interval
        )
    
    def _check_save_to_disk(self) -> None:
        """
        Verifica si es momento de guardar el caché en disco y lo hace si es necesario.
        """
        if self._should_save_to_disk():
            self.save_to_disk()
            self.last_save_time = time.time()
