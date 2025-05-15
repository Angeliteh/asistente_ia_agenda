#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gestor de caché inteligente para el asistente de agenda.
Este módulo proporciona una clase para almacenar y recuperar resultados
de consultas basándose en la estrategia generada por el LLM.
"""

import json
import os
import time
from typing import Dict, Any, Optional

class SmartLLMCache:
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
        self.cache = {}
        self.max_size = max_size
        self.cache_file = cache_file
        self.hits = 0
        self.misses = 0
        self.last_save_time = time.time()

    def get_cache_key_from_strategy(self, estrategia: Dict[str, Any]) -> str:
        """
        Genera una clave de caché basada en la estrategia generada por el LLM.

        Args:
            estrategia (dict): Estrategia generada por el LLM

        Returns:
            str: Clave única para el caché
        """
        # Extraer tipo de consulta y normalizarlo
        tipo_consulta = estrategia.get("tipo_consulta", "general").lower().strip()

        # Normalizar tipos de consulta similares
        if tipo_consulta in ["informacion", "información", "info"]:
            tipo_consulta = "informacion"
        elif tipo_consulta in ["listado", "lista", "listar"]:
            tipo_consulta = "listado"
        elif tipo_consulta in ["filtrado", "filtrar", "buscar"]:
            tipo_consulta = "filtrado"
        elif tipo_consulta in ["conteo", "contar", "cuantos", "cuántos"]:
            tipo_consulta = "conteo"

        # Extraer nombres mencionados y normalizarlos
        nombres = []
        if "nombres_posibles" in estrategia and estrategia["nombres_posibles"]:
            # Normalizar nombres (quitar acentos, convertir a mayúsculas, eliminar espacios extra)
            nombres_normalizados = []
            for nombre in estrategia["nombres_posibles"]:
                if nombre:
                    # Normalizar nombre
                    nombre_norm = nombre.upper().strip()
                    # Quitar caracteres especiales y acentos comunes en español
                    for original, reemplazo in [
                        ('Á', 'A'), ('É', 'E'), ('Í', 'I'), ('Ó', 'O'), ('Ú', 'U'),
                        ('Ñ', 'N'), ('.', ''), (',', ''), (';', ''), (':', '')
                    ]:
                        nombre_norm = nombre_norm.replace(original, reemplazo)
                    nombres_normalizados.append(nombre_norm)

            nombres = sorted(nombres_normalizados)

        nombres_str = "|".join(nombres)

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
            # Construir la clave simplificada para consultas de información
            key_parts = [tipo_consulta]
            key_parts.append(f"nombres={nombres_str}")
            if atributos_str:
                key_parts.append(f"atributos={atributos_str}")
            return ":".join(key_parts)

        # Para otros tipos de consultas, incluimos las condiciones
        condiciones = []
        if "condiciones" in estrategia and estrategia["condiciones"]:
            for cond in estrategia["condiciones"]:
                if isinstance(cond, dict):
                    campo = cond.get("campo", "").lower().strip()
                    valor = str(cond.get("valor", "")).lower().strip()

                    # Normalizar campos
                    if campo in ["zona", "área", "area", "sector"]:
                        campo = "zona"
                    elif campo in ["funcion", "función", "puesto", "cargo", "rol"]:
                        campo = "funcion"
                    elif campo in ["estado_civil", "estado civil", "civil"]:
                        campo = "estado_civil"

                    # Normalizar valores
                    if campo == "estado_civil" and valor in ["casado", "casada", "matrimonio"]:
                        valor = "casado"
                    elif campo == "estado_civil" and valor in ["soltero", "soltera"]:
                        valor = "soltero"

                    if campo and valor:
                        condiciones.append(f"{campo}:{valor}")

        condiciones_str = "|".join(sorted(condiciones))

        # Construir la clave
        key_parts = [tipo_consulta]
        if nombres_str:
            key_parts.append(f"nombres={nombres_str}")
        if atributos_str:
            key_parts.append(f"atributos={atributos_str}")
        if condiciones_str:
            key_parts.append(f"condiciones={condiciones_str}")

        return ":".join(key_parts)

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

    def get_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas del caché.

        Returns:
            dict: Estadísticas del caché
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
        try:
            # Asegurarse de que el directorio existe
            os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)

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
            cache_data = {
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

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)

            print(f"DEBUG: Caché guardado en disco: {self.cache_file}")
            print(f"DEBUG: Claves guardadas: {list(simplified_cache.keys())}")

            return True
        except Exception as e:
            print(f"Error al guardar el caché: {str(e)}")
            return False

    def load_from_disk(self) -> bool:
        """
        Carga el caché desde disco.

        Returns:
            bool: True si se cargó correctamente, False en caso contrario
        """
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

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

                print(f"DEBUG: Caché cargado desde disco: {self.cache_file}")
                print(f"DEBUG: Claves cargadas: {list(self.cache.keys())}")
                return True

            print(f"DEBUG: Archivo de caché no encontrado: {self.cache_file}")
            return False
        except Exception as e:
            print(f"Error al cargar el caché: {str(e)}")
            return False
