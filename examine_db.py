#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para examinar la estructura de la base de datos y los valores únicos
en campos relevantes para entender cómo están clasificados los docentes,
directores, subdirectores, etc.
"""

import sqlite3
import os
import pandas as pd
from colorama import Fore, Style, init

# Inicializar colorama
init()

# Ruta a la base de datos
DB_PATH = 'datos/agenda.db'

def print_header(text):
    """Imprime un encabezado formateado."""
    print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{text}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")

def print_subheader(text):
    """Imprime un subencabezado formateado."""
    print(f"\n{Fore.YELLOW}{'-' * 60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{text}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}{'-' * 60}{Style.RESET_ALL}")

def check_db_exists():
    """Verifica si la base de datos existe."""
    if not os.path.exists(DB_PATH):
        print(f"{Fore.RED}Error: La base de datos no existe en {DB_PATH}{Style.RESET_ALL}")
        return False
    return True

def get_db_columns():
    """Obtiene las columnas de la base de datos."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Obtener información sobre la tabla
    cursor.execute("PRAGMA table_info(contactos)")
    columns = cursor.fetchall()
    
    conn.close()
    return columns

def get_unique_values(column_name):
    """Obtiene los valores únicos de una columna específica."""
    conn = sqlite3.connect(DB_PATH)
    
    # Usar pandas para manejar mejor los caracteres especiales
    query = f'SELECT DISTINCT "{column_name}" FROM contactos'
    df = pd.read_sql_query(query, conn)
    
    conn.close()
    return df[column_name].tolist()

def count_values(column_name, value=None):
    """Cuenta las ocurrencias de un valor en una columna específica."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if value is None:
        # Contar todos los valores no nulos
        query = f'SELECT COUNT(*) FROM contactos WHERE "{column_name}" IS NOT NULL AND "{column_name}" != ""'
        cursor.execute(query)
    else:
        # Contar ocurrencias de un valor específico
        query = f'SELECT COUNT(*) FROM contactos WHERE "{column_name}" = ?'
        cursor.execute(query, (value,))
    
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_sample_records(column_name, value, limit=5):
    """Obtiene registros de muestra que coinciden con un valor específico."""
    conn = sqlite3.connect(DB_PATH)
    
    query = f'''
    SELECT id, nombre_completo, "{column_name}", j_jefe_de_sector_s_supervisor_d_director_sd_subdirector, zona
    FROM contactos 
    WHERE "{column_name}" = ?
    LIMIT {limit}
    '''
    
    df = pd.read_sql_query(query, conn, params=(value,))
    conn.close()
    return df

def get_role_distribution():
    """Obtiene la distribución de roles según el campo j_jefe_de_sector_s_supervisor_d_director_sd_subdirector."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
    SELECT j_jefe_de_sector_s_supervisor_d_director_sd_subdirector, COUNT(*) as count
    FROM contactos
    GROUP BY j_jefe_de_sector_s_supervisor_d_director_sd_subdirector
    ORDER BY count DESC
    '''
    
    cursor.execute(query)
    distribution = cursor.fetchall()
    
    conn.close()
    return distribution

def get_function_by_role():
    """Obtiene las funciones específicas por cada tipo de rol."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = '''
    SELECT j_jefe_de_sector_s_supervisor_d_director_sd_subdirector, "función_específica", COUNT(*) as count
    FROM contactos
    GROUP BY j_jefe_de_sector_s_supervisor_d_director_sd_subdirector, "función_específica"
    ORDER BY j_jefe_de_sector_s_supervisor_d_director_sd_subdirector, count DESC
    '''
    
    cursor.execute(query)
    functions = cursor.fetchall()
    
    conn.close()
    return functions

def main():
    """Función principal."""
    print_header("ANÁLISIS DE LA BASE DE DATOS DE AGENDA")
    
    # Verificar si la base de datos existe
    if not check_db_exists():
        return
    
    # Obtener columnas de la base de datos
    print_subheader("COLUMNAS EN LA BASE DE DATOS")
    columns = get_db_columns()
    for col in columns:
        print(f"{Fore.GREEN}{col[0]}: {col[1]} ({col[2]}){Style.RESET_ALL}")
    
    # Analizar valores únicos en función_específica
    print_subheader("VALORES ÚNICOS EN 'función_específica'")
    try:
        unique_functions = get_unique_values("función_específica")
        for func in unique_functions:
            count = count_values("función_específica", func)
            print(f"{Fore.GREEN}{func}: {count} registros{Style.RESET_ALL}")
            
            # Mostrar algunos ejemplos
            if count > 0:
                print(f"{Fore.WHITE}Ejemplos:{Style.RESET_ALL}")
                samples = get_sample_records("función_específica", func, 3)
                print(samples[["nombre_completo", "función_específica", "j_jefe_de_sector_s_supervisor_d_director_sd_subdirector", "zona"]].to_string(index=False))
                print()
    except Exception as e:
        print(f"{Fore.RED}Error al obtener valores únicos de función_específica: {str(e)}{Style.RESET_ALL}")
    
    # Analizar distribución de roles
    print_subheader("DISTRIBUCIÓN DE ROLES (j_jefe_de_sector_s_supervisor_d_director_sd_subdirector)")
    try:
        role_distribution = get_role_distribution()
        for role, count in role_distribution:
            role_desc = ""
            if role == "J":
                role_desc = "Jefe de Sector"
            elif role == "S":
                role_desc = "Supervisor"
            elif role == "D":
                role_desc = "Director"
            elif role == "SD":
                role_desc = "Subdirector"
            elif role == "DFG":
                role_desc = "Docente Frente a Grupo"
            
            print(f"{Fore.GREEN}{role} ({role_desc}): {count} registros{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error al obtener distribución de roles: {str(e)}{Style.RESET_ALL}")
    
    # Analizar funciones específicas por rol
    print_subheader("FUNCIONES ESPECÍFICAS POR ROL")
    try:
        functions_by_role = get_function_by_role()
        current_role = None
        for role, function, count in functions_by_role:
            if role != current_role:
                current_role = role
                role_desc = ""
                if role == "J":
                    role_desc = "Jefe de Sector"
                elif role == "S":
                    role_desc = "Supervisor"
                elif role == "D":
                    role_desc = "Director"
                elif role == "SD":
                    role_desc = "Subdirector"
                elif role == "DFG":
                    role_desc = "Docente Frente a Grupo"
                
                print(f"\n{Fore.CYAN}Rol: {role} ({role_desc}){Style.RESET_ALL}")
            
            print(f"{Fore.GREEN}  - {function}: {count} registros{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error al obtener funciones por rol: {str(e)}{Style.RESET_ALL}")
    
    # Analizar zonas
    print_subheader("ZONAS DISPONIBLES")
    try:
        unique_zones = get_unique_values("zona")
        for zone in unique_zones:
            count = count_values("zona", zone)
            print(f"{Fore.GREEN}Zona {zone}: {count} registros{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error al obtener zonas: {str(e)}{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
